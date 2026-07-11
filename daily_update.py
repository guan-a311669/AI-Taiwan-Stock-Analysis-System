import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime

import pandas as pd


# ==============================
# 路徑設定
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 嘗試自動尋找 data.db
DATA_DB_CANDIDATES = [
    os.path.abspath(os.path.join(PROJECT_ROOT, "..", "股市資料庫", "data", "data.db")),
    os.path.abspath(os.path.join(PROJECT_ROOT, "data", "data.db")),
    os.path.abspath(os.path.join(PROJECT_ROOT, "..", "股市資料庫", "data.db")),
]

SCRIPT_1 = os.path.join(PROJECT_ROOT, "1計算多空指標", "calculate_price_indicators.py")
SCRIPT_2 = os.path.join(PROJECT_ROOT, "2股價預測", "train_price_prediction.py")
SCRIPT_3 = os.path.join(PROJECT_ROOT, "3多空指標股票篩選器", "simple_stock_screener.py")

MARKET_INDICATORS_CSV = os.path.join(
    PROJECT_ROOT,
    "1計算多空指標",
    "subproject_1_market_indicators",
    "output",
    "market_indicators.csv"
)

LATEST_PREDICTIONS_CSV = os.path.join(
    PROJECT_ROOT,
    "2股價預測",
    "output",
    "latest_price_predictions.csv"
)

SCREENER_CSV = os.path.join(
    PROJECT_ROOT,
    "3多空指標股票篩選器",
    "output",
    "simple_stock_screener_results.csv"
)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "update_log.txt")
STATUS_FILE = os.path.join(LOG_DIR, "update_status.json")


# ==============================
# 日誌工具
# ==============================
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{now}] {message}"
    print(text)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def save_status(status, message, extra=None):
    data = {
        "status": status,
        "message": message,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "extra": extra or {}
    }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==============================
# 尋找 data.db
# ==============================
def find_data_db():
    for path in DATA_DB_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ==============================
# 取得 CSV 最新日期
# ==============================
def get_latest_date_from_csv(csv_path):
    if not os.path.exists(csv_path):
        return None

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        if "date" not in df.columns:
            return None

        dates = pd.to_datetime(df["date"], errors="coerce").dropna()

        if dates.empty:
            return None

        return dates.max().date()

    except Exception as e:
        log(f"讀取 CSV 最新日期失敗：{csv_path}，錯誤：{e}")
        return None


# ==============================
# 取得 SQLite data.db 最新日期
# ==============================
def get_latest_date_from_db(db_path):
    date_columns = ["date", "trade_date", "日期", "交易日期"]

    latest_date = None
    latest_source = None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = [row[1] for row in cursor.fetchall()]

            for col in date_columns:
                if col in columns:
                    try:
                        query = f'SELECT MAX("{col}") FROM "{table}"'
                        cursor.execute(query)
                        result = cursor.fetchone()[0]

                        if result is None:
                            continue

                        parsed_date = pd.to_datetime(result, errors="coerce")

                        if pd.isna(parsed_date):
                            continue

                        parsed_date = parsed_date.date()

                        if latest_date is None or parsed_date > latest_date:
                            latest_date = parsed_date
                            latest_source = f"{table}.{col}"

                    except Exception:
                        continue

        conn.close()

        return latest_date, latest_source

    except Exception as e:
        log(f"讀取 data.db 最新日期失敗：{e}")
        return None, None


# ==============================
# 執行子專案程式
# ==============================
def run_script(script_path, script_name):
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"找不到 {script_name} 程式：{script_path}")

    log(f"開始執行 {script_name}")
    log(f"程式路徑：{script_path}")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.stdout:
        log(f"{script_name} 輸出：")
        log(result.stdout)

    if result.returncode != 0:
        if result.stderr:
            log(f"{script_name} 錯誤：")
            log(result.stderr)

        raise RuntimeError(f"{script_name} 執行失敗")

    log(f"{script_name} 執行成功")


# ==============================
# 判斷是否需要更新
# ==============================
def should_update(force=False):
    if force:
        return True, "使用 force 模式，強制更新"

    db_path = find_data_db()

    if db_path is None:
        return False, "找不到 data.db，無法判斷是否需要更新"

    db_latest_date, db_source = get_latest_date_from_db(db_path)
    csv_latest_date = get_latest_date_from_csv(MARKET_INDICATORS_CSV)

    log(f"data.db 路徑：{db_path}")
    log(f"data.db 最新日期：{db_latest_date}，來源：{db_source}")
    log(f"目前多空指標 CSV 最新日期：{csv_latest_date}")

    if db_latest_date is None:
        return False, "data.db 找不到可判斷的日期欄位"

    if csv_latest_date is None:
        return True, "尚未產生 market_indicators.csv，需要更新"

    if db_latest_date > csv_latest_date:
        return True, f"data.db 有新資料：{db_latest_date} > {csv_latest_date}"

    return False, f"目前已是最新資料：{csv_latest_date}"


# ==============================
# 主更新流程
# ==============================
def run_daily_update(force=False):
    log("=" * 60)
    log("開始每日更新檢查")

    try:
        need_update, reason = should_update(force=force)

        log(f"是否需要更新：{need_update}")
        log(f"原因：{reason}")

        if not need_update:
            save_status(
                status="skipped",
                message=reason,
                extra={
                    "market_indicators_csv": MARKET_INDICATORS_CSV,
                    "latest_predictions_csv": LATEST_PREDICTIONS_CSV,
                    "screener_csv": SCREENER_CSV
                }
            )
            log("今日無需更新，流程結束")
            return

        run_script(SCRIPT_1, "子專案 1：計算多空指標")
        run_script(SCRIPT_2, "子專案 2：股價預測")
        run_script(SCRIPT_3, "子專案 3：股票篩選器")

        latest_indicator_date = get_latest_date_from_csv(MARKET_INDICATORS_CSV)
        latest_prediction_date = get_latest_date_from_csv(LATEST_PREDICTIONS_CSV)
        latest_screener_date = get_latest_date_from_csv(SCREENER_CSV)

        save_status(
            status="success",
            message="每日更新完成",
            extra={
                "latest_indicator_date": str(latest_indicator_date),
                "latest_prediction_date": str(latest_prediction_date),
                "latest_screener_date": str(latest_screener_date),
                "market_indicators_csv": MARKET_INDICATORS_CSV,
                "latest_predictions_csv": LATEST_PREDICTIONS_CSV,
                "screener_csv": SCREENER_CSV
            }
        )

        log("每日更新完成")

    except Exception as e:
        error_message = str(e)
        save_status(
            status="failed",
            message=error_message
        )
        log(f"每日更新失敗：{error_message}")
        raise


# ==============================
# 執行入口
# ==============================
if __name__ == "__main__":
    force_mode = "--force" in sys.argv
    run_daily_update(force=force_mode)