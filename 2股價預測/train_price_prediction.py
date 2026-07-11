import os
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_CSV = os.path.join(
    BASE_DIR,
    "..",
    "1計算多空指標",
    "subproject_1_market_indicators",
    "output",
    "market_indicators.csv"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_PATH = os.path.join(OUTPUT_DIR, "price_prediction_model.pkl")
PREDICTION_CSV = os.path.join(OUTPUT_DIR, "price_predictions.csv")
LATEST_PREDICTION_CSV = os.path.join(OUTPUT_DIR, "latest_price_predictions.csv")
REPORT_TXT = os.path.join(OUTPUT_DIR, "model_report.txt")
FEATURE_IMPORTANCE_CSV = os.path.join(OUTPUT_DIR, "feature_importance.csv")
FEATURE_COLUMNS_TXT = os.path.join(OUTPUT_DIR, "feature_columns.txt")


def load_data():
    print("正在讀取資料：")
    print(INPUT_CSV)

    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"找不到輸入檔案：{INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")

    # 移除重複欄位，避免 pandas 抓到 DataFrame 不是 Series
    df = df.loc[:, ~df.columns.duplicated()].copy()

    print("\n原始資料筆數/欄位數：", df.shape)
    print("欄位：")
    print(df.columns.tolist())

    return df


def create_target(df):
    df = df.copy()

    if "stock_id" not in df.columns:
        raise ValueError("資料中找不到必要欄位：stock_id")

    if "date" not in df.columns:
        raise ValueError("資料中找不到必要欄位：date")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["stock_id", "date"])
    df = df.sort_values(["stock_id", "date"]).reset_index(drop=True)

    close_candidates = ["收盤價", "close", "Close", "close_price"]
    close_col = next(
        (col for col in close_candidates if col in df.columns),
        None
    )

    if close_col is not None:
        df[close_col] = pd.to_numeric(df[close_col], errors="coerce")
        df["next_close"] = df.groupby("stock_id")[close_col].shift(-1)
        df["next_return"] = (
            (df["next_close"] - df[close_col]) / df[close_col]
        )

    elif "ret_1d" in df.columns:
        df["ret_1d"] = pd.to_numeric(df["ret_1d"], errors="coerce")
        df["next_return"] = df.groupby("stock_id")["ret_1d"].shift(-1)
        df["next_close"] = np.nan

    else:
        raise ValueError(
            "資料中沒有收盤價，也沒有可替代的 ret_1d 欄位。"
        )

    df["target_up"] = np.where(
        df["next_return"].isna(),
        np.nan,
        np.where(df["next_return"] > 0, 1, 0)
    )

    return df


def prepare_features(df):
    df = df.copy()
    df = df.loc[:, ~df.columns.duplicated()].copy()

    signal_map = {
        "偏多": 2,
        "弱多": 1,
        "中性": 0,
        "弱空": -1,
        "偏空": -2
    }

    if "signal" in df.columns:
        df["signal_num"] = df["signal"].map(signal_map)
    else:
        df["signal_num"] = 0

    feature_cols = [
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
        "融資餘額變化",
        "融券餘額變化",
        "bull_bear_score",
        "signal_num"
    ]

    feature_cols = [col for col in feature_cols if col in df.columns]
    feature_cols = list(dict.fromkeys(feature_cols))

    print("\n原本使用特徵欄位：")
    print(feature_cols)

    base_cols = [
        "stock_id",
        "股票名稱",
        "date",
        "收盤價",
        "next_close",
        "next_return",
        "target_up",
        "bull_bear_score",
        "signal"
    ]

    base_cols = [col for col in base_cols if col in df.columns]

    # 避免欄位重複，例如「收盤價」同時在 base_cols 和 feature_cols
    use_cols = base_cols + [col for col in feature_cols if col not in base_cols]
    use_cols = list(dict.fromkeys(use_cols))

    model_df = df[use_cols].copy()
    model_df = model_df.replace([np.inf, -np.inf], np.nan)

    valid_feature_cols = []
    removed_cols = []

    for col in feature_cols:
        if col not in model_df.columns:
            removed_cols.append(col)
            continue

        model_df[col] = pd.to_numeric(model_df[col], errors="coerce")

        if model_df[col].notna().sum() > 0:
            valid_feature_cols.append(col)
        else:
            removed_cols.append(col)

    feature_cols = valid_feature_cols

    print("\n移除無法使用或整欄都是空值的特徵：")
    print(removed_cols)

    print("\n最後使用特徵欄位：")
    print(feature_cols)

    if len(feature_cols) == 0:
        raise ValueError("沒有任何可用特徵欄位，請檢查 market_indicators.csv")

    # 用中位數補缺值
    for col in feature_cols:
        median_value = model_df[col].median()
        model_df[col] = model_df[col].fillna(median_value)
        model_df[col] = model_df[col].fillna(0)

    train_df = model_df.dropna(subset=["target_up", "next_return"]).copy()
    train_df["target_up"] = train_df["target_up"].astype(int)

    X = train_df[feature_cols]
    y = train_df["target_up"]

    return model_df, train_df, X, y, feature_cols


def train_model(X, y, feature_cols):
    print("\n可用於訓練的資料筆數/欄位數：", X.shape)

    print("\n上漲/下跌分布：")
    print(y.value_counts())

    if len(X) == 0:
        raise ValueError("訓練資料為 0 筆，請檢查資料是否被清理掉")

    if y.nunique() < 2:
        raise ValueError("target_up 只有一種類別，模型無法訓練")

    class_counts = y.value_counts()
    min_class_count = class_counts.min()
    stratify_y = y if min_class_count >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify_y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        random_state=42,
        class_weight="balanced"
    )

    print("\n開始訓練模型...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    print("\n模型準確率：", round(acc, 4))

    print("\n混淆矩陣：")
    print(cm)

    print("\n分類報告：")
    print(report)

    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write("子專案 2：股價漲跌預測模型報告\n")
        f.write("=" * 40)
        f.write("\n\n")
        f.write("模型：RandomForestClassifier\n")
        f.write(f"訓練資料筆數：{len(X)}\n")
        f.write(f"特徵欄位數：{len(feature_cols)}\n")
        f.write(f"模型準確率：{round(acc, 4)}\n\n")
        f.write("上漲/下跌分布：\n")
        f.write(str(y.value_counts()))
        f.write("\n\n混淆矩陣：\n")
        f.write(str(cm))
        f.write("\n\n分類報告：\n")
        f.write(report)

    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    importance_df.to_csv(FEATURE_IMPORTANCE_CSV, index=False, encoding="utf-8-sig")

    print("\n特徵重要性已輸出：")
    print(FEATURE_IMPORTANCE_CSV)

    print("\n前 10 名重要特徵：")
    print(importance_df.head(10))

    return model


def save_model_and_features(model, feature_cols):
    joblib.dump(model, MODEL_PATH)

    with open(FEATURE_COLUMNS_TXT, "w", encoding="utf-8") as f:
        for col in feature_cols:
            f.write(col + "\n")

    print("\n模型已儲存：")
    print(MODEL_PATH)

    print("\n特徵欄位已儲存：")
    print(FEATURE_COLUMNS_TXT)


def export_predictions(model, model_df, feature_cols):
    model_df = model_df.copy()

    X_all = model_df[feature_cols]

    model_df["predict_up"] = model.predict(X_all)
    model_df["predict_proba_up"] = model.predict_proba(X_all)[:, 1]

    model_df["prediction_signal"] = model_df["predict_up"].map({
        1: "預測上漲",
        0: "預測下跌或持平"
    })

    output_cols = [
        "stock_id",
        "股票名稱",
        "date",
        "收盤價",
        "next_close",
        "next_return",
        "target_up",
        "predict_up",
        "predict_proba_up",
        "prediction_signal",
        "bull_bear_score",
        "signal"
    ]

    output_cols = [col for col in output_cols if col in model_df.columns]

    result_df = model_df[output_cols].sort_values(
        ["date", "predict_proba_up"],
        ascending=[False, False]
    )

    result_df.to_csv(PREDICTION_CSV, index=False, encoding="utf-8-sig")

    print("\n完整預測結果已輸出：")
    print(PREDICTION_CSV)

    latest_date = model_df["date"].max()

    latest_df = model_df[model_df["date"] == latest_date][output_cols].sort_values(
        "predict_proba_up",
        ascending=False
    )

    latest_df.to_csv(LATEST_PREDICTION_CSV, index=False, encoding="utf-8-sig")

    print("\n最新日期預測結果已輸出：")
    print(LATEST_PREDICTION_CSV)

    print("\n最新日期：", latest_date)

    print("\n最新預測前 20 筆：")
    print(latest_df.head(20))


def main():
    df = load_data()
    df = create_target(df)

    model_df, train_df, X, y, feature_cols = prepare_features(df)

    model = train_model(X, y, feature_cols)

    save_model_and_features(model, feature_cols)

    export_predictions(model, model_df, feature_cols)

    print("\n✅ 子專案 2 第一版完成")


if __name__ == "__main__":
    main()
