import sqlite3
from pathlib import Path
from datetime import datetime
import math


def connect_db(db_path):
    return sqlite3.connect(str(db_path))


def init_output_db(output_db_path, schema_path):
    output_db_path = Path(output_db_path)
    schema_path = Path(schema_path)

    if not schema_path.exists():
        raise FileNotFoundError(f"找不到 schema.sql：{schema_path}")

    sql = schema_path.read_text(encoding="utf-8")

    with connect_db(output_db_path) as conn:
        conn.executescript(sql)
        conn.commit()

    print(f"已初始化輸出資料庫：{output_db_path}")


def clean_value(value):
    if value is None:
        return None

    try:
        if math.isnan(value):
            return None
    except TypeError:
        pass

    return value


def upsert_indicators(conn, df):
    if df is None or df.empty:
        print("沒有資料需要寫入 indicators。")
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = df.copy()

    if "created_at" not in df.columns:
        df["created_at"] = now

    df["updated_at"] = now

    columns = [
        "stock_id",
        "date",
        "ret_1d",
        "ret_5d",
        "ret_20d",
        "ma5",
        "ma10",
        "ma20",
        "ma5_bias",
        "ma20_bias",
        "volume_ratio_5d",
        "volatility_20d",
        "intraday_range_pct",
        "rsi_14",
        "k_value",
        "d_value",
        "macd",
        "macd_signal",
        "macd_hist",
        "bollinger_upper",
        "bollinger_middle",
        "bollinger_lower",
        "foreign_net_ratio",
        "trust_net_ratio",
        "dealer_net_ratio",
        "institutional_net_ratio",
        "foreign_holding_change_5d",
        "margin_balance_change_5d",
        "short_balance_change_5d",
        "mainforce_net_ratio",
        "revenue_yoy_ratio",
        "revenue_mom_ratio",
        "eps_change_value",
        "twii_return_20d",
        "bullish_signal_count",
        "bearish_signal_count",
        "long_short_signal_score",
        "long_short_signal_ratio",
        "created_at",
        "updated_at",
    ]

    for col in columns:
        if col not in df.columns:
            df[col] = None

    df = df[columns]

    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)

    update_columns = [
        col for col in columns
        if col not in ["stock_id", "date", "created_at"]
    ]

    update_sql = ",\n        ".join([
        f"{col} = excluded.{col}"
        for col in update_columns
    ])

    sql = f"""
    INSERT INTO indicators (
        {column_names}
    )
    VALUES (
        {placeholders}
    )
    ON CONFLICT(stock_id, date)
    DO UPDATE SET
        {update_sql};
    """

    rows = []
    for _, row in df.iterrows():
        rows.append(tuple(clean_value(row[col]) for col in columns))

    conn.executemany(sql, rows)
    conn.commit()

    print(f"已寫入 / 更新 indicators：{len(rows)} 筆")
    return len(rows)
    