from pathlib import Path

from config import OUTPUT_DB_PATH
from db_utils import init_output_db, connect_db, table_exists


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def main():
    print("開始測試建立 indicator.db...")

    init_output_db(
        output_db_path=OUTPUT_DB_PATH,
        schema_path=SCHEMA_PATH
    )

    conn = connect_db(OUTPUT_DB_PATH)

    if table_exists(conn, "indicators"):
        print("成功：indicators 資料表已建立")
    else:
        print("失敗：找不到 indicators 資料表")

    conn.close()


if __name__ == "__main__":
    main()