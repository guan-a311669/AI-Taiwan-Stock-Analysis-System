import sys
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 子專案 1：計算多空指標
# 目的：
# 從 data.db 讀取台股資料，計算技術面 + 籌碼面多空分數
# ============================================================


def quote_identifier(name: str) -> str:
    """SQLite 欄位/資料表名稱安全加雙引號，避免中文欄位或特殊符號出錯。"""
    return '"' + name.replace('"', '""') + '"'


def find_database_path() -> Path:
    """
    自動尋找 data.db。
    支援：
    1. python main.py 指定路徑
    2. 從目前子專案位置往上找 ../股市資料庫/data/data.db
    """
    if len(sys.argv) >= 2:
        user_path = Path(sys.argv[1]).expanduser()
        if user_path.exists():
            return user_path.resolve()

    base_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()

    candidates = [
        base_dir.parent.parent / "股市資料庫" / "data" / "data.db",
        base_dir.parent / "股市資料庫" / "data" / "data.db",
        cwd.parent / "股市資料庫" / "data" / "data.db",
        cwd / "股市資料庫" / "data" / "data.db",
        cwd / "data" / "data.db",
        cwd.parent / "data" / "data.db",
    ]

    for path in candidates:
        if path.exists():
            return path.resolve()

    raise FileNotFoundError(
        "找不到 data.db。\n"
        "請確認資料庫位置是否為：../股市資料庫/data/data.db\n"
        "或改用指定路徑執行：\n"
        'python subproject_1_market_indicators/main.py "../股市資料庫/data/data.db"'
    )


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = ?
    """
    result = conn.execute(sql, (table_name,)).fetchone()
    return result is not None


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row[1] for row in rows]


def read_table(
    conn: sqlite3.Connection,
    table_name: str,
    wanted_columns: list[str] | None = None,
) -> pd.DataFrame:
    """讀取指定資料表，若欄位不存在則自動略過。"""
    if not table_exists(conn, table_name):
        print(f"⚠️ 找不到資料表：{table_name}，已略過")
        return pd.DataFrame()

    table_columns = get_table_columns(conn, table_name)

    if wanted_columns is None:
        selected_columns = table_columns
    else:
        selected_columns = [col for col in wanted_columns if col in table_columns]

    if not selected_columns:
        print(f"⚠️ 資料表 {table_name} 沒有可讀取欄位，已略過")
        return pd.DataFrame()

    sql = (
        "SELECT "
        + ", ".join(quote_identifier(col) for col in selected_columns)
        + f" FROM {quote_identifier(table_name)}"
    )

    return pd.read_sql_query(sql, conn)


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """把含逗號、空字串、-- 的欄位轉成數值。"""
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("--", "", regex=False)
        .str.replace("－", "-", regex=False)
        .str.strip()
        .replace({"": np.nan, "nan": np.nan, "None": np.nan}),
        errors="coerce",
    )


def clean_basic_columns(df: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    df = df.copy()

    if "stock_id" in df.columns:
        df["stock_id"] = df["stock_id"].astype(str).str.strip()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in numeric_columns:
        if col in df.columns:
            df[col] = clean_numeric_series(df[col])

    return df


def safe_merge(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    merge_name: str,
) -> pd.DataFrame:
    """依 stock_id + date 合併資料，避免缺表造成中斷。"""
    if right_df.empty:
        print(f"⚠️ {merge_name} 無資料，略過合併")
        return left_df

    if not {"stock_id", "date"}.issubset(right_df.columns):
        print(f"⚠️ {merge_name} 缺少 stock_id 或 date，略過合併")
        return left_df

    right_df = right_df.dropna(subset=["stock_id", "date"])
    right_df = right_df.drop_duplicates(subset=["stock_id", "date"], keep="last")

    merged = left_df.merge(right_df, on=["stock_id", "date"], how="left")
    print(f"✅ 已合併 {merge_name}")
    return merged


def load_price_data(conn: sqlite3.Connection) -> pd.DataFrame:
    price_columns = [
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

    df = read_table(conn, "price", price_columns)

    if df.empty:
        raise ValueError("price 表沒有資料，無法計算多空指標")

    required_columns = {"stock_id", "date", "收盤價"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"price 表缺少必要欄位：{missing}")

    numeric_columns = [
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

    df = clean_basic_columns(df, numeric_columns)
    df = df.dropna(subset=["stock_id", "date", "收盤價"])
    df = df.drop_duplicates(subset=["stock_id", "date"], keep="last")
    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    print(f"✅ price 讀取完成：{len(df):,} 筆")
    return df


def load_stock_list(conn: sqlite3.Connection) -> pd.DataFrame:
    stock_columns = [
        "stock_id",
        "股票名稱",
        "市場別",
        "產業別",
    ]

    df = read_table(conn, "stockList", stock_columns)

    if df.empty:
        return pd.DataFrame()

    if "stock_id" in df.columns:
        df["stock_id"] = df["stock_id"].astype(str).str.strip()

    df = df.drop_duplicates(subset=["stock_id"], keep="last")
    return df


def load_corporate_data(conn: sqlite3.Connection) -> pd.DataFrame:
    corporate_columns = [
        "stock_id",
        "date",
        "外陸資買賣超股數(不含外資自營商)",
        "投信買賣超股數",
        "自營商買賣超股數",
        "三大法人買賣超股數",
    ]

    df = read_table(conn, "corporate", corporate_columns)

    if df.empty:
        return pd.DataFrame()

    numeric_columns = [
        "外陸資買賣超股數(不含外資自營商)",
        "投信買賣超股數",
        "自營商買賣超股數",
        "三大法人買賣超股數",
    ]

    df = clean_basic_columns(df, numeric_columns)

    if "三大法人買賣超股數" not in df.columns:
        available_parts = [
            col
            for col in [
                "外陸資買賣超股數(不含外資自營商)",
                "投信買賣超股數",
                "自營商買賣超股數",
            ]
            if col in df.columns
        ]

        if available_parts:
            df["三大法人買賣超股數"] = df[available_parts].sum(axis=1, skipna=True)

    keep_columns = [
        col
        for col in [
            "stock_id",
            "date",
            "三大法人買賣超股數",
            "外陸資買賣超股數(不含外資自營商)",
            "投信買賣超股數",
            "自營商買賣超股數",
        ]
        if col in df.columns
    ]

    return df[keep_columns]


def load_mainforce_data(conn: sqlite3.Connection) -> pd.DataFrame:
    mainforce_columns = [
        "stock_id",
        "date",
        "買進",
        "賣出",
        "買賣超",
    ]

    df = read_table(conn, "mainforce", mainforce_columns)

    if df.empty:
        return pd.DataFrame()

    numeric_columns = ["買進", "賣出", "買賣超"]
    df = clean_basic_columns(df, numeric_columns)

    if "買賣超" in df.columns:
        df = df.rename(columns={"買賣超": "主力買賣超"})

    keep_columns = [
        col
        for col in [
            "stock_id",
            "date",
            "買進",
            "賣出",
            "主力買賣超",
        ]
        if col in df.columns
    ]

    return df[keep_columns]


def load_credit_data(conn: sqlite3.Connection) -> pd.DataFrame:
    credit_columns = [
        "stock_id",
        "date",
        "融資今日餘額",
        "融券今日餘額",
        "資券互抵",
    ]

    df = read_table(conn, "credit", credit_columns)

    if df.empty:
        return pd.DataFrame()

    numeric_columns = [
        "融資今日餘額",
        "融券今日餘額",
        "資券互抵",
    ]

    df = clean_basic_columns(df, numeric_columns)

    keep_columns = [
        col
        for col in [
            "stock_id",
            "date",
            "融資今日餘額",
            "融券今日餘額",
            "資券互抵",
        ]
        if col in df.columns
    ]

    return df[keep_columns]


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    close_col = "收盤價"
    volume_col = "成交股數"

    group = df.groupby("stock_id", group_keys=False)

    df["daily_return"] = group[close_col].transform(lambda s: s.pct_change())

    df["ma5"] = group[close_col].transform(
        lambda s: s.rolling(window=5, min_periods=5).mean()
    )
    df["ma20"] = group[close_col].transform(
        lambda s: s.rolling(window=20, min_periods=20).mean()
    )
    df["ma60"] = group[close_col].transform(
        lambda s: s.rolling(window=60, min_periods=60).mean()
    )

    if volume_col in df.columns:
        df["volume_ma20"] = group[volume_col].transform(
            lambda s: s.rolling(window=20, min_periods=20).mean()
        )
        df["volume_ratio"] = df[volume_col] / df["volume_ma20"]
    else:
        print("⚠️ price 表缺少 成交股數，volume_ratio 將為空值")
        df["volume_ma20"] = np.nan
        df["volume_ratio"] = np.nan

    df["price_position"] = np.where(
        df["ma60"].isna(),
        0,
        np.where(df[close_col] > df["ma60"], 1, -1),
    )

    df["ma_trend_signal"] = np.select(
        [
            (df["ma5"] > df["ma20"]) & (df["ma20"] > df["ma60"]),
            (df["ma5"] < df["ma20"]) & (df["ma20"] < df["ma60"]),
        ],
        [1, -1],
        default=0,
    )

    df["momentum_20d"] = group[close_col].transform(lambda s: s / s.shift(20) - 1)

    high_source_col = "最高價" if "最高價" in df.columns else close_col
    df["high_20d_prev"] = group[high_source_col].transform(
        lambda s: s.shift(1).rolling(window=20, min_periods=20).max()
    )

    df["breakout_20d"] = (
        (df[close_col] > df["high_20d_prev"])
        & df["high_20d_prev"].notna()
    ).astype(int)

    print("✅ 技術面指標計算完成")
    return df


def calculate_bull_bear_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    score = pd.Series(0, index=df.index, dtype="int64")

    def add_score(condition, points: int):
        nonlocal score
        condition = pd.Series(condition, index=df.index).fillna(False)
        score.loc[condition] += points

    # 技術面
    add_score(df["收盤價"] > df["ma20"], 1)
    add_score(df["收盤價"] < df["ma20"], -1)

    add_score(df["ma_trend_signal"] == 1, 2)
    add_score(df["ma_trend_signal"] == -1, -2)

    add_score(df["momentum_20d"] > 0.05, 1)
    add_score(df["momentum_20d"] < -0.05, -1)

    add_score((df["volume_ratio"] > 1.5) & (df["daily_return"] > 0), 1)
    add_score((df["volume_ratio"] > 1.5) & (df["daily_return"] < 0), -1)

    add_score(df["breakout_20d"] == 1, 1)

    # 籌碼面：三大法人
    if "三大法人買賣超股數" in df.columns:
        add_score(df["三大法人買賣超股數"] > 0, 1)
        add_score(df["三大法人買賣超股數"] < 0, -1)

    # 籌碼面：主力買賣超
    if "主力買賣超" in df.columns:
        add_score(df["主力買賣超"] > 0, 1)
        add_score(df["主力買賣超"] < 0, -1)

    # 籌碼面：融資融券變化
    group = df.groupby("stock_id", group_keys=False)

    if "融資今日餘額" in df.columns:
        df["融資餘額變化"] = group["融資今日餘額"].transform(lambda s: s.diff())
        add_score((df["融資餘額變化"] > 0) & (df["daily_return"] < 0), -1)
    else:
        df["融資餘額變化"] = np.nan

    if "融券今日餘額" in df.columns:
        df["融券餘額變化"] = group["融券今日餘額"].transform(lambda s: s.diff())
        add_score((df["融券餘額變化"] > 0) & (df["daily_return"] > 0), 1)
    else:
        df["融券餘額變化"] = np.nan

    df["bull_bear_score"] = score

    df["signal"] = np.select(
        [
            df["bull_bear_score"] >= 4,
            df["bull_bear_score"].between(1, 3),
            df["bull_bear_score"].between(-1, 0),
            df["bull_bear_score"].between(-3, -2),
            df["bull_bear_score"] <= -4,
        ],
        [
            "偏多",
            "弱多",
            "中性",
            "弱空",
            "偏空",
        ],
        default="中性",
    )

    print("✅ 多空分數 bull_bear_score 與 signal 計算完成")
    return df


def merge_stock_info(df: pd.DataFrame, stock_df: pd.DataFrame) -> pd.DataFrame:
    if stock_df.empty:
        print("⚠️ stockList 無資料，略過股票名稱/產業別合併")
        return df

    merged = df.merge(stock_df, on="stock_id", how="left")
    print("✅ 已合併 stockList 股票基本資料")
    return merged


def save_csv(df: pd.DataFrame, output_path: Path):
    output_df = df.copy()

    if "date" in output_df.columns:
        output_df["date"] = pd.to_datetime(output_df["date"], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )

    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ 已輸出：{output_path}")


def export_outputs(df: pd.DataFrame):
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    latest_df = (
        df.dropna(subset=["date"])
        .groupby("stock_id", as_index=False, group_keys=False)
        .tail(1)
        .sort_values(["bull_bear_score", "stock_id"], ascending=[False, True])
        .reset_index(drop=True)
    )

    signal_order = ["偏多", "弱多", "中性", "弱空", "偏空"]

    summary_df = (
        latest_df["signal"]
        .value_counts()
        .reindex(signal_order, fill_value=0)
        .reset_index()
    )
    summary_df.columns = ["signal", "stock_count"]

    total_count = summary_df["stock_count"].sum()
    if total_count > 0:
        summary_df["percentage"] = summary_df["stock_count"] / total_count
    else:
        summary_df["percentage"] = 0

    preferred_columns = [
        "stock_id",
        "股票名稱",
        "市場別",
        "產業別",
        "date",
        "開盤價",
        "最高價",
        "最低價",
        "收盤價",
        "成交股數",
        "daily_return",
        "ma5",
        "ma20",
        "ma60",
        "volume_ma20",
        "volume_ratio",
        "price_position",
        "ma_trend_signal",
        "momentum_20d",
        "high_20d_prev",
        "breakout_20d",
        "三大法人買賣超股數",
        "主力買賣超",
        "融資今日餘額",
        "融券今日餘額",
        "融資餘額變化",
        "融券餘額變化",
        "bull_bear_score",
        "signal",
    ]

    export_columns = [col for col in preferred_columns if col in df.columns]
    latest_export_columns = [col for col in preferred_columns if col in latest_df.columns]

    save_csv(df[export_columns], output_dir / "market_indicators.csv")
    save_csv(latest_df[latest_export_columns], output_dir / "latest_market_indicators.csv")
    save_csv(summary_df, output_dir / "bull_bear_summary.csv")

    top_bullish_df = latest_df.sort_values(
        ["bull_bear_score", "stock_id"],
        ascending=[False, True],
    ).head(30)

    top_bearish_df = latest_df.sort_values(
        ["bull_bear_score", "stock_id"],
        ascending=[True, True],
    ).head(30)

    save_csv(top_bullish_df[latest_export_columns], output_dir / "top_bullish_stocks.csv")
    save_csv(top_bearish_df[latest_export_columns], output_dir / "top_bearish_stocks.csv")

    print("\n==============================")
    print("子專案 1 輸出完成")
    print("==============================")
    print(f"全部股票每日多空指標：{output_dir / 'market_indicators.csv'}")
    print(f"每檔股票最新一日指標：{output_dir / 'latest_market_indicators.csv'}")
    print(f"多空分類統計：{output_dir / 'bull_bear_summary.csv'}")
    print(f"偏多前 30 名：{output_dir / 'top_bullish_stocks.csv'}")
    print(f"偏空前 30 名：{output_dir / 'top_bearish_stocks.csv'}")

    print("\n最新多空分類統計：")
    print(summary_df.to_string(index=False))


def main():
    print("🚀 開始執行：子專案 1 - 計算多空指標")

    db_path = find_database_path()
    print(f"📌 使用資料庫：{db_path}")

    conn = sqlite3.connect(db_path)

    try:
        price_df = load_price_data(conn)

        stock_df = load_stock_list(conn)
        corporate_df = load_corporate_data(conn)
        mainforce_df = load_mainforce_data(conn)
        credit_df = load_credit_data(conn)

    finally:
        conn.close()

    df = price_df

    df = safe_merge(df, corporate_df, "corporate 三大法人資料")
    df = safe_merge(df, mainforce_df, "mainforce 主力資料")
    df = safe_merge(df, credit_df, "credit 融資融券資料")

    df = calculate_technical_indicators(df)
    df = calculate_bull_bear_score(df)
    df = merge_stock_info(df, stock_df)

    export_outputs(df)

    print("\n✅ 子專案 1 完成，請先檢查輸出結果，再進行子專案 2。")


if __name__ == "__main__":
    main()