import sqlite3
from pathlib import Path

base = Path("c:/Users/ahl-sushant/Desktop/Share via QR")
path = base / "database.db"
conn = sqlite3.connect(path)
print(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transfer_sessions'").fetchone())
conn.close()
