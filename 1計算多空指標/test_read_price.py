import sqlite3
from config import SOURCE_DB_PATH

print("來源資料庫：", SOURCE_DB_PATH)
print("來源資料庫存在嗎？", SOURCE_DB_PATH.exists())

with sqlite3.connect(SOURCE_DB_PATH) as conn:
    count = conn.execute("""
        SELECT COUNT(*)
        FROM price
        WHERE stock_id = '2330'
    """).fetchone()[0]

    print("2330 price 筆數：", count)

    rows = conn.execute("""
        SELECT stock_id, date, "收盤價", "成交股數"
        FROM price
        WHERE stock_id = '2330'
        ORDER BY date DESC
        LIMIT 3
    """).fetchall()

    print("最新 3 筆：")
    for row in rows:
        print(row)
