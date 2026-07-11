import os
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_CSV = os.path.join(
    PROJECT_ROOT,
    "1計算多空指標",
    "subproject_1_market_indicators",
    "output",
    "market_indicators.csv"
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "5策略回測", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUMMARY_CSV = os.path.join(OUTPUT_DIR, "backtest_summary.csv")
TRADES_CSV = os.path.join(OUTPUT_DIR, "trade_records.csv")
EQUITY_CSV = os.path.join(OUTPUT_DIR, "equity_curve.csv")

INITIAL_CAPITAL = 1_000_000
BUY_SCORE = 70
SELL_SCORE = 40
MAX_POSITIONS = 5


def clean_number(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("--", "", regex=False),
        errors="coerce"
    )


def load_data():
    df = pd.read_csv(INPUT_CSV)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["收盤價"] = clean_number(df["收盤價"])
    df["bull_bear_score"] = clean_number(df["bull_bear_score"])

    df = df.dropna(subset=["date", "stock_id", "收盤價", "bull_bear_score"])
    df["stock_id"] = df["stock_id"].astype(str)
    df = df.sort_values(["date", "stock_id"])

    return df


def run_backtest(df):
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    equity_curve = []

    all_dates = sorted(df["date"].unique())

    for current_date in all_dates:
        day_df = df[df["date"] == current_date].copy()

        # 先賣出：分數低於賣出門檻
        for stock_id in list(positions.keys()):
            row = day_df[day_df["stock_id"] == stock_id]

            if row.empty:
                continue

            row = row.iloc[0]
            close_price = row["收盤價"]
            score = row["bull_bear_score"]

            if score <= SELL_SCORE:
                position = positions.pop(stock_id)
                sell_value = position["shares"] * close_price
                cash += sell_value

                profit = sell_value - position["cost"]
                return_pct = profit / position["cost"] * 100

                trades.append({
                    "stock_id": stock_id,
                    "股票名稱": row.get("股票名稱", ""),
                    "buy_date": position["buy_date"],
                    "sell_date": current_date,
                    "buy_price": position["buy_price"],
                    "sell_price": close_price,
                    "shares": position["shares"],
                    "cost": position["cost"],
                    "sell_value": sell_value,
                    "profit": profit,
                    "return_pct": return_pct,
                    "buy_score": position["buy_score"],
                    "sell_score": score
                })

        # 再買進：分數高於買進門檻，優先買分數最高
        available_slots = MAX_POSITIONS - len(positions)

        if available_slots > 0:
            candidates = day_df[
                (day_df["bull_bear_score"] >= BUY_SCORE)
                & (~day_df["stock_id"].isin(positions.keys()))
            ].sort_values("bull_bear_score", ascending=False)

            for _, row in candidates.head(available_slots).iterrows():
                stock_id = row["stock_id"]
                close_price = row["收盤價"]

                if close_price <= 0:
                    continue

                budget = cash / max(1, available_slots)
                shares = int(budget // close_price)

                if shares <= 0:
                    continue

                cost = shares * close_price
                cash -= cost

                positions[stock_id] = {
                    "buy_date": current_date,
                    "buy_price": close_price,
                    "shares": shares,
                    "cost": cost,
                    "buy_score": row["bull_bear_score"]
                }

                available_slots -= 1

                if available_slots <= 0:
                    break

        # 計算每日資產
        market_value = 0

        for stock_id, position in positions.items():
            row = day_df[day_df["stock_id"] == stock_id]

            if row.empty:
                market_value += position["cost"]
            else:
                close_price = row.iloc[0]["收盤價"]
                market_value += position["shares"] * close_price

        total_equity = cash + market_value

        equity_curve.append({
            "date": current_date,
            "cash": cash,
            "market_value": market_value,
            "total_equity": total_equity,
            "holding_count": len(positions)
        })

    return pd.DataFrame(trades), pd.DataFrame(equity_curve)


def summarize(trades_df, equity_df):
    final_equity = equity_df["total_equity"].iloc[-1]
    total_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    if trades_df.empty:
        win_rate = 0
        trade_count = 0
    else:
        trade_count = len(trades_df)
        win_rate = (trades_df["profit"] > 0).mean() * 100

    equity_df["cummax"] = equity_df["total_equity"].cummax()
    equity_df["drawdown"] = (equity_df["total_equity"] - equity_df["cummax"]) / equity_df["cummax"] * 100
    max_drawdown = equity_df["drawdown"].min()

    summary = pd.DataFrame([{
        "initial_capital": INITIAL_CAPITAL,
        "final_equity": final_equity,
        "total_return_pct": total_return,
        "trade_count": trade_count,
        "win_rate_pct": win_rate,
        "max_drawdown_pct": max_drawdown,
        "buy_score": BUY_SCORE,
        "sell_score": SELL_SCORE,
        "max_positions": MAX_POSITIONS
    }])

    return summary


def main():
    print("讀取多空指標資料...")
    df = load_data()

    print(f"資料筆數：{len(df)}")
    print(f"股票檔數：{df['stock_id'].nunique()}")
    print(f"日期範圍：{df['date'].min().date()} ~ {df['date'].max().date()}")

    trades_df, equity_df = run_backtest(df)
    summary_df = summarize(trades_df, equity_df)

    trades_df.to_csv(TRADES_CSV, index=False, encoding="utf-8-sig")
    equity_df.to_csv(EQUITY_CSV, index=False, encoding="utf-8-sig")
    summary_df.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")

    print("策略回測完成")
    print(summary_df)
    print(f"交易紀錄：{TRADES_CSV}")
    print(f"資產曲線：{EQUITY_CSV}")
    print(f"回測摘要：{SUMMARY_CSV}")


if __name__ == "__main__":
    main()