from pathlib import Path
from datetime import datetime, timedelta
import shutil
import sqlite3
import pandas as pd

ROOT = Path.cwd()

SOURCE_DB = ROOT / "股市資料庫" / "data" / "data.db"
DEMO_DIR = ROOT / "demo"
DEMO_DB = DEMO_DIR / "demo_data.db"
APP_PATH = ROOT / "4生成戰略儀表板" / "app_integrated_final.py"
GITIGNORE_PATH = ROOT / ".gitignore"
REQUIREMENTS_PATH = ROOT / "requirements.txt"

DEMO_STOCK_LIMIT = 50
HISTORY_DAYS = 1095  # 約 3 年

PRIORITY_STOCK_IDS = [
    # ETF
    "0050", "0056", "006208", "00878", "00919", "00929", "00940",
    # 電子與大型權值
    "2330", "2317", "2454", "2308", "2412", "2303", "2382", "3231",
    "2357", "2356", "2379", "3008", "2327", "2408", "3034", "3711",
    # 金融
    "2881", "2882", "2886", "2891", "2892", "5880", "2884", "2885",
    "2880", "2883", "2887", "2890", "2897", "5871",
    # 傳產與航運
    "1301", "1303", "2002", "2207", "1216", "6505", "2603", "2609",
    "2615", "2618", "2801", "3045", "4904", "9910",
]


def normalize_stock_id(value):
    text = str(value).strip().replace(".0", "")
    if text.isdigit() and len(text) <= 4:
        return text.zfill(4)
    return text


def require_files():
    required = [SOURCE_DB, APP_PATH, GITIGNORE_PATH]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("❌ 找不到必要檔案：")
        for path in missing:
            print(f" - {path}")
        raise SystemExit(1)


def build_demo_database():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(SOURCE_DB) as conn:
        stock_list = pd.read_sql("SELECT * FROM stockList", conn)

        price_summary = pd.read_sql(
            """
            SELECT
                CAST(stock_id AS TEXT) AS raw_stock_id,
                COUNT(*) AS row_count,
                MAX(date) AS max_date
            FROM price
            GROUP BY CAST(stock_id AS TEXT)
            """,
            conn,
        )

        stock_list["_normalized_id"] = stock_list["stock_id"].map(normalize_stock_id)
        price_summary["_normalized_id"] = price_summary["raw_stock_id"].map(normalize_stock_id)

        available = (
            price_summary
            .sort_values(["row_count", "max_date"], ascending=[False, False])
            .drop_duplicates("_normalized_id")
        )

        available_ids = set(available["_normalized_id"].astype(str))

        selected_ids = [
            sid for sid in PRIORITY_STOCK_IDS
            if sid in available_ids
        ]

        for sid in available["_normalized_id"].astype(str):
            if sid not in selected_ids:
                selected_ids.append(sid)
            if len(selected_ids) >= DEMO_STOCK_LIMIT:
                break

        selected_ids = selected_ids[:DEMO_STOCK_LIMIT]

        if len(selected_ids) < 5:
            print("❌ 可用股票太少，請確認原始資料庫內容。")
            raise SystemExit(1)

        selected_summary = available[
            available["_normalized_id"].isin(selected_ids)
        ].copy()

        raw_ids = selected_summary["raw_stock_id"].astype(str).tolist()
        placeholders = ",".join("?" for _ in raw_ids)

        max_date = pd.to_datetime(
            selected_summary["max_date"],
            errors="coerce"
        ).max()

        cutoff = (
            "1900-01-01"
            if pd.isna(max_date)
            else (max_date - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
        )

        price = pd.read_sql(
            f"""
            SELECT *
            FROM price
            WHERE CAST(stock_id AS TEXT) IN ({placeholders})
              AND date >= ?
            ORDER BY stock_id, date
            """,
            conn,
            params=raw_ids + [cutoff],
        )

    stock_list = stock_list[
        stock_list["_normalized_id"].isin(selected_ids)
    ].copy()
    stock_list["stock_id"] = stock_list["_normalized_id"]
    stock_list = stock_list.drop(columns=["_normalized_id"])

    price["stock_id"] = price["stock_id"].map(normalize_stock_id)

    if stock_list.empty or price.empty:
        print("❌ Demo 資料建立失敗，沒有可用資料。")
        raise SystemExit(1)

    if DEMO_DB.exists():
        DEMO_DB.unlink()

    with sqlite3.connect(DEMO_DB) as demo_conn:
        stock_list.to_sql(
            "stockList",
            demo_conn,
            index=False,
            if_exists="replace",
        )
        price.to_sql(
            "price",
            demo_conn,
            index=False,
            if_exists="replace",
        )
        demo_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_price_stock_date "
            "ON price(stock_id, date)"
        )
        demo_conn.commit()

    size_mb = DEMO_DB.stat().st_size / (1024 * 1024)

    display_cols = [
        col for col in ["stock_id", "股票名稱", "市場別", "產業別"]
        if col in stock_list.columns
    ]

    print("✅ 已建立公開 Demo 資料庫")
    print(f"   股票數：{stock_list['stock_id'].nunique()} 檔")
    print(f"   股價筆數：{len(price):,} 筆")
    print(f"   歷史區間：約 3 年")
    print(f"   檔案大小：{size_mb:.2f} MB")
    print()
    print("公開 Demo 股票：")
    print(stock_list[display_cols].sort_values("stock_id").to_string(index=False))


def update_app_for_cloud():
    text = APP_PATH.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = APP_PATH.with_name(
        f"app_integrated_final_部署前備份_{timestamp}.py"
    )

    if "IS_DEMO_MODE =" not in text:
        shutil.copy2(APP_PATH, backup_path)

        old_db_line = (
            'DATA_DB_PATH = PROJECT_ROOT / "股市資料庫" / "data" / "data.db"'
        )
        new_db_block = (
            'LOCAL_DB_PATH = PROJECT_ROOT / "股市資料庫" / "data" / "data.db"\n'
            'DEMO_DB_PATH = PROJECT_ROOT / "demo" / "demo_data.db"\n'
            'DATA_DB_PATH = LOCAL_DB_PATH if LOCAL_DB_PATH.exists() else DEMO_DB_PATH\n'
            'IS_DEMO_MODE = DATA_DB_PATH == DEMO_DB_PATH'
        )

        if old_db_line not in text:
            print("❌ 找不到 app 的資料庫路徑設定。")
            raise SystemExit(1)

        text = text.replace(old_db_line, new_db_block, 1)

        catalog_line = (
            "catalog_df = build_stock_catalog("
            "stock_list_df, screener_df, market_df)"
        )
        catalog_block = (
            "catalog_df = build_stock_catalog("
            "stock_list_df, screener_df, market_df)\n"
            'if IS_DEMO_MODE and not stock_list_df.empty '
            'and "stock_id" in stock_list_df.columns:\n'
            '    demo_stock_ids = set('
            'stock_list_df["stock_id"].astype(str))\n'
            '    catalog_df = catalog_df['
            'catalog_df["stock_id"].astype(str).isin(demo_stock_ids)'
            '].reset_index(drop=True)'
        )

        if catalog_line in text:
            text = text.replace(catalog_line, catalog_block, 1)

        flow_info = (
            '    st.info("可一鍵依序執行子專案 1、2、3，'
            '也保留原本的單獨執行按鈕。")'
        )
        flow_demo_block = (
            '    st.info("可一鍵依序執行子專案 1、2、3，'
            '也保留原本的單獨執行按鈕。")\n'
            '    if IS_DEMO_MODE:\n'
            '        st.warning("目前為公開 Demo 模式，'
            '為避免雲端重新訓練與覆寫資料，'
            '流程執行功能已停用。其他分析與圖表功能可正常操作。")\n'
            '        st.stop()'
        )

        if flow_info in text:
            text = text.replace(flow_info, flow_demo_block, 1)

        APP_PATH.write_text(text, encoding="utf-8")
        print(f"✅ 已修改儀表板以支援雲端 Demo")
        print(f"✅ 備份位置：{backup_path.relative_to(ROOT)}")
    else:
        print("✅ 儀表板已具備雲端 Demo 模式，不重複修改")


def update_requirements_and_gitignore():
    REQUIREMENTS_PATH.write_text(
        "streamlit\n"
        "pandas\n"
        "numpy\n"
        "plotly\n"
        "scikit-learn\n"
        "matplotlib\n",
        encoding="utf-8",
    )
    print("✅ 已建立 requirements.txt")

    gitignore_text = GITIGNORE_PATH.read_text(encoding="utf-8")

    rules = (
        "\n# Public Streamlit demo database\n"
        "!demo/\n"
        "!demo/demo_data.db\n"
    )

    if "!demo/demo_data.db" not in gitignore_text:
        GITIGNORE_PATH.write_text(
            gitignore_text.rstrip() + "\n" + rules,
            encoding="utf-8",
        )
        print("✅ 已更新 .gitignore")
    else:
        print("✅ .gitignore 已允許 Demo 資料庫")


def main():
    require_files()
    build_demo_database()
    update_app_for_cloud()
    update_requirements_and_gitignore()

    print()
    print("=== 完成 ===")
    print("這次不是 2 檔，而是最多 50 檔股票、約 3 年資料。")
    print("完整本機 data.db 不會被刪除或縮小。")
    print()
    print("接著執行：")
    print(
        'python -m py_compile '
        '"4生成戰略儀表板/app_integrated_final.py"'
    )
    print(
        'streamlit run '
        '"4生成戰略儀表板/app_integrated_final.py"'
    )


if __name__ == "__main__":
    main()
