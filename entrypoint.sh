#!/bin/bash
echo "[INFO] Starting OpenEFT..."
python3 openeft.py || tail -f /dev/null
