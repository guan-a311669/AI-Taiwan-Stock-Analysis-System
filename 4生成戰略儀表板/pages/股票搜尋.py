import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="股票搜尋與股價走勢", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DB_PATH = PROJECT_ROOT / "股市資料庫" / "data" / "data.db"


@st.cache_data
def load_stock_list():
    conn = sqlite3.connect(DATA_DB_PATH)
    df = pd.read_sql("SELECT * FROM stockList", conn)
    conn.close()
    return df


@st.cache_data
def load_stock_price(stock_id):
    conn = sqlite3.connect(DATA_DB_PATH)
    query = """
        SELECT stock_id, date, 開盤價, 最高價, 最低價, 收盤價, 成交股數, 成交金額, 本益比
        FROM price
        WHERE stock_id = ?
        ORDER BY date
    """
    df = pd.read_sql(query, conn, params=(stock_id,))
    conn.close()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["開盤價", "最高價", "最低價", "收盤價", "成交股數", "成交金額", "本益比"]:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("--", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["date", "收盤價"])


st.title("股票搜尋與股價走勢")

stock_list_df = load_stock_list()

keyword = st.text_input("輸入股票代碼或名稱，例如 2330 或 台積電")

if keyword:
    result = stock_list_df[
        stock_list_df["stock_id"].astype(str).str.contains(keyword, case=False, na=False)
        | stock_list_df["股票名稱"].astype(str).str.contains(keyword, case=False, na=False)
    ].copy()

    if result.empty:
        st.warning("找不到符合的股票")
    else:
        result["顯示名稱"] = result["stock_id"].astype(str) + " " + result["股票名稱"].astype(str)

        selected = st.selectbox("選擇股票", result["顯示名稱"].tolist())
        selected_stock_id = selected.split(" ")[0]

        st.dataframe(result[["stock_id", "股票名稱", "市場別", "產業別", "上市日"]], use_container_width=True)

        price_df = load_stock_price(selected_stock_id)

        if price_df.empty:
            st.warning("這檔股票目前沒有股價資料")
        else:
            st.subheader(f"{selected} 股價走勢")

            latest = price_df.iloc[-1]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新收盤價", f"{latest['收盤價']:.2f}")
            c2.metric("最高價", f"{latest['最高價']:.2f}")
            c3.metric("最低價", f"{latest['最低價']:.2f}")
            c4.metric("本益比", f"{latest['本益比']:.2f}" if pd.notna(latest["本益比"]) else "無資料")

            st.line_chart(price_df.set_index("date")[["收盤價"]], use_container_width=True)
            st.bar_chart(price_df.set_index("date")[["成交股數"]], use_container_width=True)

            with st.expander("查看最近 100 筆股價資料"):
                st.dataframe(price_df.tail(100), use_container_width=True)