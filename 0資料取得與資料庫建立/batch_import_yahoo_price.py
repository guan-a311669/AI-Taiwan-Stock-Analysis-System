import sqlite3
import time
from datetime import datetime, date, timedelta
from pathlib import Path

import requests


DB_PATH = Path(__file__).resolve().parent.parent / "股市資料庫" / "data" / "data.db"

START_DATE = "2024-01-01"
END_DATE = date.today().strftime("%Y-%m-%d")


TARGET_STOCKS = [
    {"stock_id": "2330", "股票名稱": "台積電", "市場別": "上市", "產業別": "半導體"},
    {"stock_id": "2317", "股票名稱": "鴻海", "市場別": "上市", "產業別": "電子"},
    {"stock_id": "2454", "股票名稱": "聯發科", "市場別": "上市", "產業別": "半導體"},
    {"stock_id": "2308", "股票名稱": "台達電", "市場別": "上市", "產業別": "電子零組件"},
    {"stock_id": "2382", "股票名稱": "廣達", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "2303", "股票名稱": "聯電", "市場別": "上市", "產業別": "半導體"},
    {"stock_id": "3711", "股票名稱": "日月光投控", "市場別": "上市", "產業別": "半導體"},
    {"stock_id": "3008", "股票名稱": "大立光", "市場別": "上市", "產業別": "光電"},
    {"stock_id": "2357", "股票名稱": "華碩", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "2353", "股票名稱": "宏碁", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "2376", "股票名稱": "技嘉", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "3231", "股票名稱": "緯創", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "4938", "股票名稱": "和碩", "市場別": "上市", "產業別": "電子"},
    {"stock_id": "3037", "股票名稱": "欣興", "市場別": "上市", "產業別": "電子零組件"},
    {"stock_id": "2412", "股票名稱": "中華電", "市場別": "上市", "產業別": "通信網路"},
    {"stock_id": "1216", "股票名稱": "統一", "市場別": "上市", "產業別": "食品"},
    {"stock_id": "1301", "股票名稱": "台塑", "市場別": "上市", "產業別": "塑膠"},
    {"stock_id": "1303", "股票名稱": "南亞", "市場別": "上市", "產業別": "塑膠"},
    {"stock_id": "2002", "股票名稱": "中鋼", "市場別": "上市", "產業別": "鋼鐵"},
    {"stock_id": "1101", "股票名稱": "台泥", "市場別": "上市", "產業別": "水泥"},
    {"stock_id": "2881", "股票名稱": "富邦金", "市場別": "上市", "產業別": "金融"},
    {"stock_id": "2882", "股票名稱": "國泰金", "市場別": "上市", "產業別": "金融"},
    {"stock_id": "2884", "股票名稱": "玉山金", "市場別": "上市", "產業別": "金融"},
    {"stock_id": "2886", "股票名稱": "兆豐金", "市場別": "上市", "產業別": "金融"},
    {"stock_id": "2891", "股票名稱": "中信金", "市場別": "上市", "產業別": "金融"},
    {"stock_id": "2603", "股票名稱": "長榮", "市場別": "上市", "產業別": "航運"},
    {"stock_id": "2609", "股票名稱": "陽明", "市場別": "上市", "產業別": "航運"},
    {"stock_id": "2615", "股票名稱": "萬海", "市場別": "上市", "產業別": "航運"},
    {"stock_id": "2610", "股票名稱": "華航", "市場別": "上市", "產業別": "航運"},
    {"stock_id": "2618", "股票名稱": "長榮航", "市場別": "上市", "產業別": "航運"},
    {"stock_id": "0050", "股票名稱": "元大台灣50", "市場別": "上市", "產業別": "ETF"},
    {"stock_id": "0056", "股票名稱": "元大高股息", "市場別": "上市", "產業別": "ETF"},
    {"stock_id": "00878", "股票名稱": "國泰永續高股息", "市場別": "上市", "產業別": "ETF"},
    {"stock_id": "00919", "股票名稱": "群益台灣精選高息", "市場別": "上市", "產業別": "ETF"},
    {"stock_id": "006208", "股票名稱": "富邦台50", "市場別": "上市", "產業別": "ETF"},
    {"stock_id": "2395", "股票名稱": "研華", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "2324", "股票名稱": "仁寶", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "6669", "股票名稱": "緯穎", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "3017", "股票名稱": "奇鋐", "市場別": "上市", "產業別": "電腦週邊"},
    {"stock_id": "2408", "股票名稱": "南亞科", "市場別": "上市", "產業別": "半導體"},
]


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(conn, table_name: str) -> bool:
    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = ?
    """
    return conn.execute(sql, (table_name,)).fetchone() is not None


def get_columns(conn, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row[1] for row in rows]


def fetch_yahoo_price(stock_id: str, start_date: str, end_date: str):
    symbol = f"{stock_id}.TW"

    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_ts = int((datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "events": "history",
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()

    data = response.json()

    result = data.get("chart", {}).get("result")
    if not result:
        return []

    result = result[0]
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    records = []
    previous_close = None

    for i, ts in enumerate(timestamps):
        open_price = opens[i] if i < len(opens) else None
        high_price = highs[i] if i < len(highs) else None
        low_price = lows[i] if i < len(lows) else None
        close_price = closes[i] if i < len(closes) else None
        volume = volumes[i] if i < len(volumes) else None

        if close_price is None:
            continue

        trade_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

        change = None
        if previous_close is not None:
            change = close_price - previous_close

        previous_close = close_price

        amount = None
        if volume is not None and close_price is not None:
            amount = volume * close_price

        records.append({
            "stock_id": stock_id,
            "date": trade_date,
            "成交股數": volume,
            "成交筆數": None,
            "成交金額": amount,
            "開盤價": open_price,
            "最高價": high_price,
            "最低價": low_price,
            "收盤價": close_price,
            "漲跌價差": change,
            "本益比": None,
        })

    return records


def insert_stock_list(conn, stocks):
    if not table_exists(conn, "stockList"):
        print("⚠️ 找不到 stockList 表，略過股票清單寫入")
        return

    columns = get_columns(conn, "stockList")

    usable_columns = [
        col for col in ["stock_id", "股票名稱", "市場別", "產業別"]
        if col in columns
    ]

    if not usable_columns:
        print("⚠️ stockList 沒有可用欄位，略過")
        return

    for stock in stocks:
        if "stock_id" in columns:
            conn.execute(
                f"DELETE FROM {quote_identifier('stockList')} WHERE {quote_identifier('stock_id')} = ?",
                (stock["stock_id"],)
            )

        row = {col: stock.get(col) for col in usable_columns}

        sql = (
            f"INSERT INTO {quote_identifier('stockList')} "
            f"({', '.join(quote_identifier(col) for col in usable_columns)}) "
            f"VALUES ({', '.join(['?'] * len(usable_columns))})"
        )

        conn.execute(sql, [row[col] for col in usable_columns])

    conn.commit()
    print(f"✅ stockList 已寫入 {len(stocks)} 檔股票")


def insert_price_records(conn, records):
    if not records:
        return 0

    if not table_exists(conn, "price"):
        raise RuntimeError("找不到 price 表，無法寫入股價資料")

    columns = get_columns(conn, "price")

    usable_columns = [
        col for col in [
            "stock_id",
            "date",
            "成交股數",
            "成交筆數",
            "成交金額",
            "開盤價",
            "最高價",
            "最低價",
            "收盤價",
            "漲跌價差",
            "本益比",
        ]
        if col in columns
    ]

    inserted_count = 0

    for record in records:
        conn.execute(
            f"""
            DELETE FROM {quote_identifier('price')}
            WHERE {quote_identifier('stock_id')} = ?
              AND {quote_identifier('date')} = ?
            """,
            (record["stock_id"], record["date"])
        )

        sql = (
            f"INSERT INTO {quote_identifier('price')} "
            f"({', '.join(quote_identifier(col) for col in usable_columns)}) "
            f"VALUES ({', '.join(['?'] * len(usable_columns))})"
        )

        conn.execute(sql, [record.get(col) for col in usable_columns])
        inserted_count += 1

    conn.commit()
    return inserted_count


def print_price_status(conn):
    if not table_exists(conn, "price"):
        print("⚠️ 找不到 price 表")
        return

    row = conn.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT stock_id) AS stock_count,
            MIN(date) AS min_date,
            MAX(date) AS max_date
        FROM price
    """).fetchone()

    print("\n目前 price 表狀態：")
    print(f"總筆數：{row[0]}")
    print(f"股票檔數：{row[1]}")
    print(f"最早日期：{row[2]}")
    print(f"最新日期：{row[3]}")


def main():
    print("🚀 開始批次補 Yahoo 股價資料")
    print(f"📌 使用資料庫：{DB_PATH}")
    print(f"📌 抓取日期：{START_DATE} ~ {END_DATE}")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"找不到資料庫：{DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        insert_stock_list(conn, TARGET_STOCKS)

        total_inserted = 0

        for index, stock in enumerate(TARGET_STOCKS, start=1):
            stock_id = stock["stock_id"]
            stock_name = stock["股票名稱"]

            print(f"\n[{index}/{len(TARGET_STOCKS)}] 抓取 {stock_id} {stock_name}")

            try:
                records = fetch_yahoo_price(stock_id, START_DATE, END_DATE)
                inserted_count = insert_price_records(conn, records)

                total_inserted += inserted_count

                print(f"✅ 寫入 {inserted_count} 筆")

            except Exception as e:
                print(f"❌ {stock_id} 抓取失敗：{e}")

            time.sleep(0.8)

        print(f"\n✅ 批次補資料完成，本次寫入 {total_inserted} 筆")
        print_price_status(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
    