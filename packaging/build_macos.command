#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt pyinstaller pywebview
pyinstaller packaging/bitd_gm_ai.spec --noconfirm
echo "Built app bundle at ./dist/BitD_GM_AI/BitD GM AI"
