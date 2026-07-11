from pathlib import Path
import os

# =========================
# 專案路徑設定
# =========================
# 目前檔案位置：
# AI奇摩股價預測專案 / 1計算多空指標 / config.py
BASE_DIR = Path(__file__).resolve().parent

# 專案根目錄：
# AI奇摩股價預測專案
PROJECT_ROOT = BASE_DIR.parent

# =========================
# 來源資料庫
# =========================
# 優先順序：
# 1. 如果有設定環境變數 STOCK_DB_PATH，就使用環境變數
# 2. 否則使用專案內的 股市資料庫/data/data.db
SOURCE_DB_PATH = Path(
    os.getenv(
        "STOCK_DB_PATH",
        PROJECT_ROOT / "股市資料庫" / "data" / "data.db"
    )
)

# =========================
# 輸出資料庫
# =========================
# indicator.db 一律建立在 1計算多空指標 資料夾內
OUTPUT_DB_PATH = BASE_DIR / "indicator.db"

# =========================
# 日期設定
# =========================
# 若都設為 None，代表只計算 indicators 裡尚未存在的資料
START_DATE = None
END_DATE = None

# 範例：
# START_DATE = "2024-01-01"
# END_DATE = "2024-12-31"