
:: 1) แตกโฟลเดอร์ที่มี sweet_paradise.py + requirements.txt
:: 2) เปิด cmd ในโฟลเดอร์นั้น แล้วรัน:
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

----ติดตั้งไลบรารี + PyInstaller
python -m pip install pyinstaller


คำสั่งทำ exe
py -m pip install --upgrade pip
py -m pip install pyinstaller

py -3.13 -m PyInstaller --noconfirm --clean `
  --name "SweetParadise" `
  --onefile `
  --collect-all PySide6 `
  --collect-all TikTokLive `
  --collect-all fastapi `
  --collect-all starlette `
  --collect-all anyio `
  --collect-all h11 `
  --hidden-import websockets.legacy.client `
  --hidden-import websockets.legacy.server `
  sweet_paradise.py
