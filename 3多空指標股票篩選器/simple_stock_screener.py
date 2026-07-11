import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "..",
    "2股價預測",
    "output",
    "latest_price_predictions.csv"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "simple_stock_screener_results.csv")
SUMMARY_FILE = os.path.join(OUTPUT_DIR, "simple_screener_summary.txt")


def classify_stock(row):
    proba = row["predict_proba_up"]
    signal = row.get("signal", "中性")

    if proba >= 0.55 and signal in ["偏多", "弱多"]:
        return "強勢看多"
    elif proba >= 0.52:
        return "保守觀察"
    elif proba <= 0.48 or signal in ["弱空", "偏空"]:
        return "風險偏高"
    else:
        return "一般觀察"


def main():
    print("讀取預測結果：")
    print(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    df["predict_proba_up"] = pd.to_numeric(df["predict_proba_up"], errors="coerce")
    df["predict_proba_up"] = df["predict_proba_up"].fillna(0.5)

    df["screen_category"] = df.apply(classify_stock, axis=1)

    df["prediction_percent"] = (df["predict_proba_up"] * 100).round(2)

    output_cols = [
        "stock_id",
        "股票名稱",
        "date",
        "收盤價",
        "bull_bear_score",
        "signal",
        "predict_proba_up",
        "prediction_percent",
        "prediction_signal",
        "screen_category"
    ]

    output_cols = [col for col in output_cols if col in df.columns]

    result_df = df[output_cols].sort_values(
        "predict_proba_up",
        ascending=False
    )

    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    summary = result_df["screen_category"].value_counts()

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("子專案 3 簡單版股票篩選器\n")
        f.write("========================\n\n")
        f.write("分類統計：\n")
        f.write(str(summary))

    print("\n分類統計：")
    print(summary)

    print("\n前 20 筆篩選結果：")
    print(result_df.head(20))

    print("\n篩選結果已輸出：")
    print(OUTPUT_FILE)

    print("\n✅ 子專案 3 簡單版完成")


if __name__ == "__main__":
    main()
