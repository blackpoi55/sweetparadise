:: 1) แตกโฟลเดอร์ที่มี sweet_paradise.py + requirements.txt
:: 2) เปิด cmd ในโฟลเดอร์นั้น แล้วรัน:
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

คำสั่งทำ exe
python -m PyInstaller `
  --noconfirm --clean `
  --name SweetParadise `
  --windowed --onefile `
  --collect-all PySide6 `
  --collect-submodules TikTokLive `
  sweet_paradise.py
