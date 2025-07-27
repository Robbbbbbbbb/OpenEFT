#!/bin/bash
echo "[INFO] Setting an2k path"
export PATH="/root/OpenEFT/nbis/an2k/bin:$PATH"
echo "[INFO] Starting OpenEFT..."
python3 openeft.py || tail -f /dev/null
