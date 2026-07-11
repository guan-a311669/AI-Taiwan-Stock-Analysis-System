import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import pandas as pd


# =========================
# 路徑設定
# =========================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATA_DB_PATH = PROJECT_ROOT / "股市資料庫" / "data" / "data.db"


# =========================
# 測試股票
# =========================
# 先只抓 2330 台積電
# Yahoo Finance 台股上市通常是 .TW
# 上櫃常見是 .TWO，之後再擴充
TARGET_STOCKS = [
    {
        "stock_id": "2330",
        "symbol": "2330.TW",
        "name": "台積電",
    }
]


def fetch_yahoo_price(symbol, range_text="3mo", interval="1d"):
    """
    從 Yahoo Finance chart API 取得股價資料。

    range_text 範例：
    - 1mo
    - 3mo
    - 6mo
    - 1y
    - 5y

    interval 範例：
    - 1d
    - 1wk
    - 1mo
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    params = {
        "range": range_text,
        "interval": interval,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()
    data = response.json()

    chart = data.get("chart", {})
    error = chart.get("error")

    if error:
        raise RuntimeError(f"Yahoo 回傳錯誤：{error}")

    results = chart.get("result", [])

    if not results:
        return pd.DataFrame()

    result = results[0]

    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]

    if not timestamps or not quote:
        return pd.DataFrame()

    rows = []

    taipei_tz = ZoneInfo("Asia/Taipei")

    for i, ts in enumerate(timestamps):
        date_text = datetime.fromtimestamp(ts, taipei_tz).strftime("%Y-%m-%d")

        row = {
            "date": date_text,
            "開盤價": get_list_value(quote.get("open"), i),
            "最高價": get_list_value(quote.get("high"), i),
            "最低價": get_list_value(quote.get("low"), i),
            "收盤價": get_list_value(quote.get("close"), i),
            "成交股數": get_list_value(quote.get("volume"), i),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # 收盤價沒有的資料不要存
    df = df.dropna(subset=["收盤價"])

    return df


def get_list_value(values, index):
    """
    安全取得 list 裡的值。
    """
    if values is None:
        return None

    if index >= len(values):
        return None

    return values[index]


def upsert_price(conn, stock_id, price_df):
    """
    寫入 price 表。

    若同一個 stock_id + date 已存在，就更新。
    """
    if price_df.empty:
        print(f"{stock_id} 沒有資料可寫入")
        return 0

    sql = """
    INSERT INTO price (
        stock_id,
        date,
        成交股數,
        開盤價,
        最高價,
        最低價,
        收盤價
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(stock_id, date)
    DO UPDATE SET
        成交股數 = excluded.成交股數,
        開盤價 = excluded.開盤價,
        最高價 = excluded.最高價,
        最低價 = excluded.最低價,
        收盤價 = excluded.收盤價;
    """

    rows = []

    for _, row in price_df.iterrows():
        rows.append((
            stock_id,
            row["date"],
            row["成交股數"],
            row["開盤價"],
            row["最高價"],
            row["最低價"],
            row["收盤價"],
        ))

    conn.executemany(sql, rows)
    conn.commit()

    return len(rows)


def main():
    print("開始匯入 Yahoo 股價資料")
    print(f"資料庫位置：{DATA_DB_PATH}")

    if not DATA_DB_PATH.exists():
        raise FileNotFoundError(f"找不到 data.db：{DATA_DB_PATH}")

    with sqlite3.connect(DATA_DB_PATH) as conn:
        total_rows = 0

        for item in TARGET_STOCKS:
            stock_id = item["stock_id"]
            symbol = item["symbol"]
            name = item["name"]

            print(f"\n正在抓取：{stock_id} {name} / {symbol}")

            df = fetch_yahoo_price(
                symbol=symbol,
                range_text="3mo",
                interval="1d"
            )

            print(f"抓到資料筆數：{len(df)}")

            written_rows = upsert_price(conn, stock_id, df)

            print(f"寫入 price 筆數：{written_rows}")

            total_rows += written_rows

            # 禮貌等待，避免太頻繁請求
            time.sleep(1)

    print("\n完成 Yahoo 股價匯入")
    print(f"本次總寫入筆數：{total_rows}")


if __name__ == "__main__":
    main()