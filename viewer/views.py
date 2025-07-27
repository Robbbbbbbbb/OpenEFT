import os
import uuid
import subprocess
import shutil
import re
from datetime import datetime, timedelta
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, HttpResponseBadRequest

# Enable debug logging to console
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define where to store temporary fingerprint images and EFTs
TMP_FP_DIR = os.path.join(settings.BASE_DIR, "static", "tmp_fps")
TMP_EFT_DIR = os.path.join(settings.BASE_DIR, "static", "tmp_efts")

# Location of the an2ktool binary; can be set via environment variable
AN2KTOOL = os.environ.get("AN2KTOOL", "/root/OpenEFT/nbis/an2k/bin/an2ktool")

def cleanup_old_sessions(base_path, max_age_minutes=60):
    """Remove old session folders to avoid clutter and space issues."""
    now = datetime.now()
    for folder in os.listdir(base_path):
        fpath = os.path.join(base_path, folder)
        if os.path.isdir(fpath):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if now - mtime > timedelta(minutes=max_age_minutes):
                shutil.rmtree(fpath, ignore_errors=True)

# Clean up both FP and EFT session directories older than 60 minutes
cleanup_old_sessions(TMP_FP_DIR)
cleanup_old_sessions(TMP_EFT_DIR)

##########################################################
'''  Function to display EFT files begins here         '''
##########################################################

@csrf_exempt
def viewer(request):
    """Handles EFT file upload and displays parsed content."""
    if request.method == "POST":
        eft_file = request.FILES.get("eftfile")
        if not eft_file:
            return render(request, "viewer/index.html", {"error": "No EFT file uploaded."})

        # Get the selected mode from the form (default to VIEW_ONLY)
        mode = request.POST.get("mode", "VIEW_ONLY")
        if mode not in ["VIEW_ONLY", "ADVANCE"]:
            mode = "VIEW_ONLY"  # Default

        # Create a unique session directory for this upload
        # Each session gets its own isolated directory to prevent fingerprint cross-contamination
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TMP_EFT_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        # Save the uploaded EFT file to the session directory, rename it to "uploaded.eft"
        input_path = os.path.join(session_dir, "uploaded.eft")
        with open(input_path, "wb") as dest:
            for chunk in eft_file.chunks():
                dest.write(chunk)

        # Parse the EFT file using an2ktool to extract raw data
        # This will also extract fingerprint images as fld*.tmp files
        try:
            result = subprocess.run(
                [AN2KTOOL, "-print", "all", input_path],
                cwd=session_dir,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            return render(request, "viewer/index.html", {
                "error": f"an2ktool failed during parse: {e.stderr or str(e)}"
            })

        # Extract raw fields from the output
        # Parse the an2ktool output to find field values in format [2.xxx]=value
        # These are the EFT fields we want to display to the user, as they are
        # specific to the user's fingerprint data
        raw_fields = {}
        for line in result.stdout.splitlines():
            match = re.match(r".*\[(2\.\d{3})\]=(.*)", line)
            if match:
                raw_fields[match.group(1).strip()] = match.group(2).strip()

        # Map field numbers to human-readable names for display
        # Alias is not displayed, as it is not needed by the ATF for eForms
        DISPLAY_FIELD_MAP = {
            "2.018": "Full Name",
            "2.022": "Date of Birth",
            "2.041": "Address",
            "2.020": "Place of Birth",
            "2.021": "Citizenship",
            "2.016": "SSN",
            "2.025": "Race",
            "2.031": "Eye Color",
            "2.032": "Hair Color",
            "2.027": "Height",
            "2.029": "Weight",
            "2.024": "Sex"
        }

        # Extract Type-4 fingerprint images from the EFT file
        # an2ktool automatically extracts images as fld*.tmp files when using -print all
        # This is run again with output to a temp file to trigger image extraction
        temp_output_path = os.path.join(session_dir, "temp_extract.txt")
        subprocess.run(
            [AN2KTOOL, "-print", "all", input_path, temp_output_path],
            cwd=session_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Map specific images to known labels for display
        # Look for fld_*_17.tmp files (which are JPEG images) created by an2ktool
        labeled_images = {}

        # Get all fld_*_17.tmp files and parse their names for proper mapping
        fld_files = [f for f in os.listdir(session_dir) if f.startswith('fld_') and f.endswith('.tmp')]

        # Parse the field numbers from filenames and map to correct labels
        # fld_3_17.tmp = RSLAP (Right Simultaneous Plain)
        # fld_4_17.tmp = LSLAP (Left Simultaneous Plain) 
        # fld_5_17.tmp = THUMBS (Thumbs)
        for fld_file in fld_files:
            file_path = os.path.join("static", "tmp_efts", session_id, fld_file)
            
            # Parse field number from filename (eg: fld_4_17.tmp -> field 4)
            match = re.match(r'fld_(\d+)_\d+\.tmp', fld_file)
            if match:
                field_num = int(match.group(1))
                
                # Map field numbers to fingerprint types based on EBTS specs
                if field_num == 3:
                    labeled_images["RSLAP"] = file_path
                elif field_num == 4:
                    labeled_images["LSLAP"] = file_path
                elif field_num == 5:
                    labeled_images["THUMBS"] = file_path
                else:
                    # For any other field numbers, use generic label
                    labeled_images[f"Field_{field_num}"] = file_path

        # Debug logging to verify the mapping (shows in console ONLY)
        logger.debug(f"Found fld files: {fld_files}")
        logger.debug(f"Mapped images: {labeled_images}")
        logger.debug(f"Selected mode: {mode}")

        # Prepare context data for template rendering
        # This includes the raw fields, labeled images, and the edit mode selected by the user
        context = {
            "fname": eft_file.name,
            "display_fields": DISPLAY_FIELD_MAP,
            "raw_fields": raw_fields,
            "original_path": input_path,
            "output": result.stdout,
            "images": labeled_images,  # labeled dict like {'RSLAP': 'static/tmp_efts/uuid/3_17.tmp', ...}
            "mode": mode,  # Pass the selected mode to the template
            "is_view_only": mode == "VIEW_ONLY",  # Helper for template conditionals - Default view mode
            "is_advance": mode == "ADVANCE"  # Helper for template conditionals
        }

        return render(request, "viewer/index.html", context)

    # GET request - show the upload form
    return render(request, "viewer/index.html")

###############################################################
'''  Function to handle saving edited EFT files begins here '''  
###############################################################

@csrf_exempt
def save_edited_eft(request):
    """
    Handles saving changes back into an EFT file using txt2an2k.
    
    SECURITY: This function is only accessible in ADVANCE mode.
    
    SECURITY CRITICAL: This function creates a completely new session directory
    and re-extracts all fingerprint images to ensure complete isolation between
    different EFT processing operations. This prevents any possibility of 
    fingerprint cross-contamination between different users or files.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    # INTEGRITY: Verify this is being called from ADVANCE mode only
    # This prevents direct access to editing functionality when in VIEW_ONLY mode
    mode = request.POST.get("mode")
    if mode != "ADVANCE":
        return HttpResponseBadRequest("Editing is only available in ADVANCE mode.")

    # Get the path to the original EFT file from the form
    original_path = request.POST.get("original_path")
    if not original_path or not os.path.isfile(original_path):
        return HttpResponseBadRequest("Original EFT file missing.")

    # SECURITY: Create a completely NEW session directory for this edit operation
    # This ensures complete isolation from any other processing sessions
    # and prevents any possibility of fingerprint cross-contamination
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(TMP_EFT_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # DEBUG: Log session creation - show ONLY in console
    logger.debug(f"=== EDIT SESSION START ===")
    logger.debug(f"Created new edit session: {session_id}")
    logger.debug(f"Session directory: {session_dir}")
    logger.debug(f"Original file path: {original_path}")
    logger.debug(f"Mode: {mode}")

    # Copy EFT to new isolated session directory
    original_copy_path = os.path.join(session_dir, "original.eft")
    shutil.copyfile(original_path, original_copy_path)
    logger.debug(f"Copied original EFT to: {original_copy_path}")
    
    # DEBUG: Show initial directory contents - show ONLY in console
    logger.debug(f"Initial session directory contents: {os.listdir(session_dir)}")

    # SECURITY: Re-extract ALL fingerprint images to the new session
    # an2ktool automatically extracts images as fld*.tmp files when using -print all
    # We need to run it with an output file to trigger the image extraction
    try:
        temp_extract_path = os.path.join(session_dir, "temp_extract.txt")
        logger.debug(f"Running an2ktool -print all to extract images...")
        logger.debug(f"Command: {AN2KTOOL} -print all {original_copy_path} {temp_extract_path}")
        logger.debug(f"Working directory: {session_dir}")
        
        result = subprocess.run(
            [AN2KTOOL, "-print", "all", original_copy_path, temp_extract_path],
            cwd=session_dir,
            capture_output=True,
            check=True
        )
        
        logger.debug(f"an2ktool stdout: {result.stdout.decode() if result.stdout else 'None'}")
        logger.debug(f"an2ktool stderr: {result.stderr.decode() if result.stderr else 'None'}")
        
        # DEBUG: Show directory contents after extraction - show ONLY in console
        post_extract_files = os.listdir(session_dir)
        logger.debug(f"Directory contents after image extraction: {post_extract_files}")
        
        # Verify that fld_*_17.tmp files were created (these contain the fingerprint images)
        fld_files = [f for f in post_extract_files if f.startswith('fld_') and f.endswith('.tmp')]
        logger.debug(f"Found fld_*.tmp files: {fld_files}")
        
        if not fld_files:
            logger.error("No fld_*.tmp files found after extraction!")
            return render(request, "viewer/index.html", {
                "error": "No fingerprint images were extracted from the EFT file. The file may not contain Type-4 records.",
            })
        else:
            logger.debug(f"Successfully extracted {len(fld_files)} fingerprint image files")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"an2ktool failed: {e}")
        logger.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        logger.error(f"stdout: {e.stdout.decode() if e.stdout else 'None'}")
        return render(request, "viewer/index.html", {
            "error": f"Failed to re-extract fingerprint images for editing: {e.stderr.decode().strip() if e.stderr else str(e)}",
        })

    # Define paths for the text dump and final edited EFT
    fmttext_path = os.path.join(session_dir, "dump.txt")
    edited_eft_path = os.path.join(session_dir, "edited.eft")
    
    logger.debug(f"Text dump path: {fmttext_path}")
    logger.debug(f"Edited EFT output path: {edited_eft_path}")

    # NOTE: We DO NOT clean up fld_*_17.tmp files here
    # These .tmp files contain the fingerprint image data (they're actually JPEG files)
    # and are required by txt2an2k to properly rebuild the EFT file with embedded images
    # They will be cleaned up when the session directory is removed by cleanup_old_sessions()

    # DEBUG: Check if any fld_*_17.tmp files might cause conflicts
    existing_fld_files = [f for f in os.listdir(session_dir) if f.startswith('fld_') and f.endswith('.tmp')]
    logger.debug(f"Existing fld_*.tmp files before an2k2txt: {existing_fld_files}")
    for fld_file in existing_fld_files:
        fld_path = os.path.join(session_dir, fld_file)
        fld_stat = os.stat(fld_path)
        logger.debug(f"  {fld_file}: size={fld_stat.st_size}, mtime={datetime.fromtimestamp(fld_stat.st_mtime)}")

    # CRITICAL FIX: Remove existing fld_*_17.tmp files before an2k2txt
    # an2k2txt will recreate these files as part of its conversion process
    # but it fails if they already exist from the previous an2ktool -print all command
    logger.debug("Removing existing fld_*.tmp files to prevent an2k2txt conflicts...")
    for fld_file in existing_fld_files:
        fld_path = os.path.join(session_dir, fld_file)
        os.remove(fld_path)
        logger.debug(f"Removed: {fld_file}")
    
    # Verify tmp files were removed
    remaining_fld_files = [f for f in os.listdir(session_dir) if f.startswith('fld_') and f.endswith('.tmp')]
    logger.debug(f"Remaining fld_*.tmp files after cleanup: {remaining_fld_files}")

    # Convert the EFT to editable text format using an2k2txt
    try:
        an2k2txt_cmd = AN2KTOOL.replace("an2ktool", "an2k2txt")
        logger.debug(f"Running an2k2txt to convert EFT to text...")
        logger.debug(f"Command: {an2k2txt_cmd} {original_copy_path} {fmttext_path}")
        logger.debug(f"Working directory: {session_dir}")
        
        result = subprocess.run(
            [an2k2txt_cmd, original_copy_path, fmttext_path],
            check=True,
            capture_output=True,
            cwd=session_dir  # Ensure we're working in the session directory with fld_*_17.tmp images
        )
        
        logger.debug(f"an2k2txt stdout: {result.stdout.decode() if result.stdout else 'None'}")
        logger.debug(f"an2k2txt stderr: {result.stderr.decode() if result.stderr else 'None'}")
        
        # DEBUG: Show directory contents after an2k2txt - show ONLY in console
        post_an2k2txt_files = os.listdir(session_dir)
        logger.debug(f"Directory contents after an2k2txt: {post_an2k2txt_files}")
        
        # DEBUG: Check if dump.txt was created and show its size - show ONLY in console
        if os.path.exists(fmttext_path):
            dump_stat = os.stat(fmttext_path)
            logger.debug(f"dump.txt created successfully: size={dump_stat.st_size} bytes")
        else:
            logger.error("dump.txt was not created!")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"an2k2txt failed: {e}")
        logger.error(f"Command was: {an2k2txt_cmd} {original_copy_path} {fmttext_path}")
        logger.error(f"Working directory: {session_dir}")
        logger.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        logger.error(f"stdout: {e.stdout.decode() if e.stdout else 'None'}")
        logger.error(f"Directory contents when error occurred: {os.listdir(session_dir)}")
        return render(request, "viewer/index.html", {
            "error": f"an2k2txt failed to convert EFT to text format: {e.stderr.decode().strip() if e.stderr else str(e)}",
        })

    # Extract user edits from the form data
    # Only process Type 2 fields that have content
    edited_fields = {k: v.strip() for k, v in request.POST.items() if k.startswith("2.") and v.strip()}
    if not edited_fields:
        logger.debug("No edited fields found in form data")
        return HttpResponseBadRequest("No fields to update.")
    
    logger.debug(f"User edited fields: {edited_fields}")

    # Read the dumped fmttext file for editing
    try:
        with open(fmttext_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        logger.debug(f"Read {len(lines)} lines from dump.txt")
    except (IOError, UnicodeDecodeError) as e:
        logger.error(f"Failed to read dump.txt: {e}")
        return render(request, "viewer/index.html", {
            "error": f"Failed to read text dump file: {str(e)}",
        })

    # Process each line and replace matching editable fields
    # Only modify lines that match expected field format to avoid breaking the EFT structure
    updated_lines = []
    changes_made = 0
    for i, line in enumerate(lines):
        # Look for lines in format: "1.2.3.4 [2.xxx]=value"
        match = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+\[(2\.\d{3})\]=(.*)", line)
        if match:
            full_key, short_key, current_value = match.groups()
            # If this field was edited by the user, update it
            if short_key in edited_fields:
                # Clean the new value (remove bullet points in the UI)
                new_value = edited_fields[short_key].replace("•", "").strip()
                # Reconstruct the line with the new value, preserving the \x1F separator
                old_line = line.strip()
                line = f"{full_key} [{short_key}]={new_value}\x1F"
                logger.debug(f"Line {i}: Changed [{short_key}] from '{current_value}' to '{new_value}'")
                logger.debug(f"  Old line: {repr(old_line)}")
                logger.debug(f"  New line: {repr(line)}")
                changes_made += 1
        updated_lines.append(line)
    
    logger.debug(f"Made {changes_made} field changes total")

    # Write the modified lines back to the text file
    # We preserve the exact format including \x1F separators and EOF markers
    # that are required by txt2an2k
    try:
        with open(fmttext_path, "w", encoding="utf-8") as f:
            for line in updated_lines:
                f.write(line + "\n")
        
        # DEBUG: Verify the updated file - show ONLY in console
        updated_stat = os.stat(fmttext_path)
        logger.debug(f"Updated dump.txt: size={updated_stat.st_size} bytes")
        
    except IOError as e:
        logger.error(f"Failed to write updated dump.txt: {e}")
        return render(request, "viewer/index.html", {
            "error": f"Failed to write updated text file: {str(e)}",
        })

    # DEBUG: Show directory state before txt2an2k - show ONLY in console
    pre_txt2an2k_files = os.listdir(session_dir)
    logger.debug(f"Directory contents before txt2an2k: {pre_txt2an2k_files}")
    
    # Check for any potential conflicts with fld_*_17.tmp files
    fld_files_before = [f for f in pre_txt2an2k_files if f.startswith('fld_') and f.endswith('.tmp')]
    logger.debug(f"fld_*.tmp files before txt2an2k: {fld_files_before}")

    # Convert the modified text back to EFT format using txt2an2k
    # This step rebuilds the binary EFT file with changes
    try:
        txt2an2k_cmd = AN2KTOOL.replace("an2ktool", "txt2an2k")
        logger.debug(f"Running txt2an2k to convert text back to EFT...")
        logger.debug(f"Command: {txt2an2k_cmd} {fmttext_path} {edited_eft_path}")
        logger.debug(f"Working directory: {session_dir}")
        
        result = subprocess.run(
            [txt2an2k_cmd, fmttext_path, edited_eft_path],
            check=True,
            capture_output=True,
            cwd=session_dir  # Ensure txt2an2k can find the fingerprint image files
        )
        
        logger.debug(f"txt2an2k stdout: {result.stdout.decode() if result.stdout else 'None'}")
        logger.debug(f"txt2an2k stderr: {result.stderr.decode() if result.stderr else 'None'}")
        
        # DEBUG: Show final directory contents - show ONLY in console
        final_files = os.listdir(session_dir)
        logger.debug(f"Final directory contents: {final_files}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"txt2an2k failed: {e}")
        logger.error(f"Command was: {txt2an2k_cmd} {fmttext_path} {edited_eft_path}")
        logger.error(f"Working directory: {session_dir}")
        logger.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        logger.error(f"stdout: {e.stdout.decode() if e.stdout else 'None'}")
        logger.error(f"Directory contents when txt2an2k failed: {os.listdir(session_dir)}")
        return render(request, "viewer/index.html", {
            "error": f"txt2an2k failed to create edited EFT file: {e.stderr.decode().strip() if e.stderr else str(e)}",
        })

    # Verify edited EFT was created successfully
    if not os.path.exists(edited_eft_path):
        logger.error(f"Edited EFT file was not created at: {edited_eft_path}")
        return render(request, "viewer/index.html", {
            "error": "Edited EFT file was not created successfully.",
        })
    
    # DEBUG: Show final file info - show ONLY in console
    edited_stat = os.stat(edited_eft_path)
    logger.debug(f"Successfully created edited EFT: {edited_eft_path}")
    logger.debug(f"Edited EFT size: {edited_stat.st_size} bytes")
    logger.debug(f"=== EDIT SESSION END ===")

    # Return the edited EFT file as a download
    # The session directory (including all fingerprint images) will be cleaned up
    # by the cleanup_old_sessions function when it's older than 60 minutes
    try:
        return FileResponse(
            open(edited_eft_path, "rb"), 
            as_attachment=True, 
            filename="edited.eft"
        )
    except IOError as e:
        logger.error(f"Failed to serve edited EFT file: {e}")
        return render(request, "viewer/index.html", {
            "error": f"Failed to serve edited EFT file: {str(e)}",
        })