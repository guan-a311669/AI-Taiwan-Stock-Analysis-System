import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATA_DIR = PROJECT_ROOT / "股市資料庫" / "data"
DATA_DB_PATH = DATA_DIR / "data.db"


TABLE_SCHEMAS = {
    "stockList": {
        "columns": [
            "stock_id",
            "股票名稱",
            "上市日",
            "市場別",
            "產業別",
        ],
        "primary_key": ["stock_id"],
    },

    "price": {
        "columns": [
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
            "最後揭示買價",
            "最後揭示買量",
            "最後揭示賣價",
            "最後揭示賣量",
            "本益比",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "corporate": {
        "columns": [
            "stock_id",
            "date",
            "證券名稱",
            "外陸資買進股數(不含外資自營商)",
            "外陸資賣出股數(不含外資自營商)",
            "外陸資買賣超股數(不含外資自營商)",
            "外資自營商買進股數",
            "外資自營商賣出股數",
            "外資自營商買賣超股數",
            "投信買進股數",
            "投信賣出股數",
            "投信買賣超股數",
            "自營商買賣超股數",
            "自營商買進股數(自行買賣)",
            "自營商賣出股數(自行買賣)",
            "自營商買賣超股數(自行買賣)",
            "自營商買進股數(避險)",
            "自營商賣出股數(避險)",
            "自營商買賣超股數(避險)",
            "三大法人買賣超股數",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "corporate_holding": {
        "columns": [
            "stock_id",
            "date",
            "發行股數",
            "外資及陸資尚可投資股數",
            "全體外資及陸資持有股數",
            "外資及陸資尚可投資比率",
            "全體外資及陸資持股比率",
            "外資及陸資共用法令投資上限比率",
            "陸資法令投資上限比率",
            "最近一次申報外資及陸資持股異動日期",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "credit": {
        "columns": [
            "stock_id",
            "date",
            "融資買進",
            "融資賣出",
            "融資現金償還",
            "融資前日餘額",
            "融資今日餘額",
            "融資次一營業日限額",
            "融券買進",
            "融券賣出",
            "融券現券償還",
            "融券前日餘額",
            "融券今日餘額",
            "融券次一營業日限額",
            "資券互抵",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "mainforce": {
        "columns": [
            "stock_id",
            "date",
            "排名",
            "買進",
            "賣出",
            "買賣超",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "monthly_revenue": {
        "columns": [
            "stock_id",
            "date",
            "上月比較增減(%)",
            "上月營收",
            "前期比較增減(%)",
            "去年同月增減(%)",
            "去年當月營收",
            "去年累計營收",
            "當月營收",
            "當月累計營收",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "seasonprofit": {
        "columns": [
            "stock_id",
            "date",
            "EPS增減(元)",
        ],
        "primary_key": ["stock_id", "date"],
    },

    "twii": {
        "columns": [
            "date",
            "收盤指數",
        ],
        "primary_key": ["date"],
    },
}


def quote_name(name):
    return '"' + str(name).replace('"', '""') + '"'


def create_table_sql(table_name, schema):
    columns = schema["columns"]
    primary_key = schema["primary_key"]

    column_sql = []
    for col in columns:
        column_sql.append(f"{quote_name(col)} TEXT")

    pk_sql = ", ".join(quote_name(col) for col in primary_key)

    sql = f"""
    CREATE TABLE IF NOT EXISTS {quote_name(table_name)} (
        {", ".join(column_sql)},
        PRIMARY KEY ({pk_sql})
    );
    """

    return sql


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("準備建立 data.db")
    print(f"資料庫位置：{DATA_DB_PATH}")

    with sqlite3.connect(DATA_DB_PATH) as conn:
        for table_name, schema in TABLE_SCHEMAS.items():
            sql = create_table_sql(table_name, schema)
            conn.execute(sql)
            print(f"已建立 / 確認資料表：{table_name}")

        conn.commit()

    print("完成：data.db 資料庫骨架已建立")


if __name__ == "__main__":
    main()