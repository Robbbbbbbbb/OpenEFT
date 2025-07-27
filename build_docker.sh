# This is untested!
#!/usr/bin/bash

mkdir build
mkdir -p browser/linux

echo "Updating Submodules"
git submodule update

echo "Setting Up NBIS"
# Remove any old copies of NBIS
sudo rm -rf ./nbis 
git clone https://github.com/Robbbbbbbbb/nbis ./nbis
cd nbis

./setup.sh ${PWD}/../build --64

echo "Configuring NBIS"
make config

echo "Making NBIS"
make it

echo "Installing NBIS"
sudo make install LIBNBIS=no

echo "Checking NBIS binaries paths"
case :$PATH:
  in *:$HOME/OpenEFT/nbis/nfseg/bin:*) ;; # do nothing, it's there
     *) echo 'export PATH="$HOME/OpenEFT/nbis/nfseg/bin:$PATH"' >> ~/.bashrc #it's missing, add to PATH
esac

case :$PATH:
  in *:$HOME/OpenEFT/nbis/nfiq/bin:*) ;; # do nothing, it's there
     *) echo 'export PATH="$HOME/OpenEFT/nbis/nfiq/bin:$PATH"' >> ~/.bashrc #it's missing, add to PATH
esac

# Install the necessary tools
echo "Installing LibOpenJP2-Tools"
sudo apt-get install libopenjp2-tools -y
sudo apt-get install libgl1-mesa-glx -y

# Move to browser directory and set up chromium
cd ../browser/linux
wget "https://github.com/clickot/ungoogled-chromium-binaries/releases/download/111.0.5563.65-1/ungoogled-chromium_111.0.5563.65-1.1.AppImage"
mv ungoogled-chromium_111.0.5563.65-1.1.AppImage chrome.AppImage

cd ../../

# Install Python dependencies
echo "Installing Pip Requirements"
pip3 install -r requirements.txt

# Migrate Django (similar to Windows build)
echo "Running Django Migrations"
python3 manage.py migrate

echo "OpenEFT build complete. Update your PATH by typing 'source ~/.bashrc' and run the app by typing 'python3 openeft.py'"
cd ~/OpenEFT
. ~/.bashrc
