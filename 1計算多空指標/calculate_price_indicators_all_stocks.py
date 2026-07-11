import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from config import SOURCE_DB_PATH, OUTPUT_DB_PATH
from db_utils import init_output_db, connect_db, upsert_indicators


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def to_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )


def read_price(stock_id="2330"):
    sql = """
    SELECT
        stock_id,
        date,
        "開盤價",
        "最高價",
        "最低價",
        "收盤價",
        "成交股數"
    FROM price
    WHERE stock_id = ?
    ORDER BY date
    """

    with sqlite3.connect(SOURCE_DB_PATH) as conn:
        df = pd.read_sql_query(sql, conn, params=(stock_id,))

    return df


def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_kd(df, period=9):
    low_min = df["最低價"].rolling(period, min_periods=period).min()
    high_max = df["最高價"].rolling(period, min_periods=period).max()

    denominator = (high_max - low_min).replace(0, np.nan)
    rsv = (df["收盤價"] - low_min) / denominator * 100

    k_value = rsv.ewm(com=2, adjust=False).mean()
    d_value = k_value.ewm(com=2, adjust=False).mean()

    return k_value, d_value


def calculate_indicators(df):
    df = df.copy()

    for col in ["開盤價", "最高價", "最低價", "收盤價", "成交股數"]:
        df[col] = to_num(df[col])

    df = df.dropna(subset=["收盤價"]).copy()
    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    group = df.groupby("stock_id", group_keys=False)

    df["ret_1d"] = group["收盤價"].pct_change(1)
    df["ret_5d"] = group["收盤價"].pct_change(5)
    df["ret_20d"] = group["收盤價"].pct_change(20)

    df["ma5"] = group["收盤價"].transform(
        lambda s: s.rolling(5, min_periods=5).mean()
    )
    df["ma10"] = group["收盤價"].transform(
        lambda s: s.rolling(10, min_periods=10).mean()
    )
    df["ma20"] = group["收盤價"].transform(
        lambda s: s.rolling(20, min_periods=20).mean()
    )

    df["ma5_bias"] = df["收盤價"] / df["ma5"] - 1
    df["ma20_bias"] = df["收盤價"] / df["ma20"] - 1

    volume_ma5 = group["成交股數"].transform(
        lambda s: s.rolling(5, min_periods=5).mean()
    )
    df["volume_ratio_5d"] = df["成交股數"] / volume_ma5.replace(0, np.nan)

    df["volatility_20d"] = group["ret_1d"].transform(
        lambda s: s.rolling(20, min_periods=20).std()
    )

    df["intraday_range_pct"] = (
        df["最高價"] - df["最低價"]
    ) / df["收盤價"].replace(0, np.nan)

    df["rsi_14"] = group["收盤價"].transform(
        lambda s: calculate_rsi(s, 14)
    )

    df["k_value"] = np.nan
    df["d_value"] = np.nan

    for stock_id, sub_df in df.groupby("stock_id"):
        k_value, d_value = calculate_kd(sub_df, period=9)
        df.loc[sub_df.index, "k_value"] = k_value.values
        df.loc[sub_df.index, "d_value"] = d_value.values

    ema12 = group["收盤價"].transform(
        lambda s: s.ewm(span=12, adjust=False).mean()
    )
    ema26 = group["收盤價"].transform(
        lambda s: s.ewm(span=26, adjust=False).mean()
    )

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df.groupby("stock_id")["macd"].transform(
        lambda s: s.ewm(span=9, adjust=False).mean()
    )
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    df["bollinger_middle"] = df["ma20"]
    bollinger_std = group["收盤價"].transform(
        lambda s: s.rolling(20, min_periods=20).std()
    )
    df["bollinger_upper"] = df["bollinger_middle"] + 2 * bollinger_std
    df["bollinger_lower"] = df["bollinger_middle"] - 2 * bollinger_std

    return df


def calculate_signal_counts(df):
    df = df.copy()

    bull_rules = [
        df["ret_5d"] > 0.02,
        df["ret_20d"] > 0.05,
        df["ma5_bias"] > 0.01,
        df["ma20_bias"] > 0.03,
        (df["volume_ratio_5d"] > 1.5) & (df["ret_1d"] > 0),
        df["rsi_14"] > 55,
        df["k_value"] > df["d_value"],
        df["macd_hist"] > 0,
        df["收盤價"] > df["bollinger_middle"],
    ]

    bear_rules = [
        df["ret_5d"] < -0.02,
        df["ret_20d"] < -0.05,
        df["ma5_bias"] < -0.01,
        df["ma20_bias"] < -0.03,
        (df["volume_ratio_5d"] > 1.5) & (df["ret_1d"] < 0),
        df["rsi_14"] < 45,
        df["k_value"] < df["d_value"],
        df["macd_hist"] < 0,
        df["收盤價"] < df["bollinger_middle"],
    ]

    bull_df = pd.concat(bull_rules, axis=1).fillna(False).astype(int)
    bear_df = pd.concat(bear_rules, axis=1).fillna(False).astype(int)

    df["bullish_signal_count"] = bull_df.sum(axis=1)
    df["bearish_signal_count"] = bear_df.sum(axis=1)

    df["long_short_signal_score"] = (
        df["bullish_signal_count"] - df["bearish_signal_count"]
    )

    total = df["bullish_signal_count"] + df["bearish_signal_count"]

    df["long_short_signal_ratio"] = np.where(
        total > 0,
        df["long_short_signal_score"] / total,
        np.nan
    )

    return df
def get_all_stock_ids():
    conn = sqlite3.connect(SOURCE_DB_PATH)

    query = """
    SELECT DISTINCT stock_id
    FROM price
    ORDER BY stock_id
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df["stock_id"].astype(str).tolist()

def main():
    print("開始計算全部股票完整技術型多空指標")

    init_output_db(
        output_db_path=OUTPUT_DB_PATH,
        schema_path=SCHEMA_PATH
    )

    stock_ids = get_all_stock_ids()
    print("股票檔數：", len(stock_ids))

    all_results = []

    for index, stock_id in enumerate(stock_ids, start=1):
        print(f"[{index}/{len(stock_ids)}] 計算 {stock_id}")

        df = read_price(stock_id=stock_id)
        print("讀到 price 筆數：", len(df))

        if df.empty:
            print(f"{stock_id} 沒有 price 資料，略過")
            continue

        df = calculate_indicators(df)
        df = calculate_signal_counts(df)

        all_results.append(df)

    if not all_results:
        print("沒有任何股票可計算")
        return

    df = pd.concat(all_results, ignore_index=True)

    output_columns = [
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
        "bullish_signal_count",
        "bearish_signal_count",
        "long_short_signal_score",
        "long_short_signal_ratio",
    ]

    output_df = df[output_columns].copy()

    with connect_db(OUTPUT_DB_PATH) as conn:
        upsert_indicators(conn, output_df)

    print("完成：2330 完整技術型多空指標已寫入 indicator.db")


if __name__ == "__main__":
    main()
