#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  echo 'Mac上で実行してください。'; exit 1
fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir --name SiteCapture --osx-bundle-identifier com.studiomk.sitecapture --collect-all playwright main.py
mkdir -p release
arch_name="$(uname -m)"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent dist/SiteCapture.app "release/SiteCapture-Mac-Lite-${arch_name}.zip"
echo 'Macアプリの生成が完了しました。releaseフォルダをご覧ください。'
