import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    go = None
    make_subplots = None
    PLOTLY_AVAILABLE = False


# =========================================================
# 基本設定
# =========================================================
st.set_page_config(
    page_title="AI 奇摩股價分析系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 深色莫蘭迪配色
# =========================================================
COLORS = {
    "background": "#20262D",
    "background_2": "#252D35",
    "sidebar": "#1A2128",
    "card": "#2D3740",
    "card_2": "#343F49",
    "border": "#55636D",
    "text": "#F1EDE6",
    "muted": "#C8C2B8",
    "accent": "#8397A3",
    "accent_2": "#A6B4BC",
    "green": "#8FA58E",
    "red": "#B78F8F",
    "yellow": "#C3A87A",
    "blue": "#7D909D",
    "grid": "rgba(200, 194, 184, 0.14)",
}


def apply_custom_style() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --bg: {COLORS['background']};
            --bg2: {COLORS['background_2']};
            --sidebar: {COLORS['sidebar']};
            --card: {COLORS['card']};
            --card2: {COLORS['card_2']};
            --border: {COLORS['border']};
            --text: {COLORS['text']};
            --muted: {COLORS['muted']};
            --accent: {COLORS['accent']};
            --green: {COLORS['green']};
            --red: {COLORS['red']};
            --yellow: {COLORS['yellow']};
        }}

        html, body, [class*="css"] {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
        }}

        .stApp {{
            background: linear-gradient(145deg, var(--bg) 0%, var(--bg2) 100%);
            color: var(--text);
        }}

        header[data-testid="stHeader"] {{
            background: rgba(26, 33, 40, 0.96) !important;
            border-bottom: 1px solid rgba(85, 99, 109, 0.50);
        }}

        .block-container {{
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        h1, h2, h3, h4 {{
            color: var(--text) !important;
            letter-spacing: 0.2px;
        }}

        h1 {{
            font-weight: 850 !important;
        }}

        p, li, label, .stMarkdown, [data-testid="stCaptionContainer"] {{
            color: var(--muted) !important;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, var(--sidebar) 0%, #202830 100%) !important;
            border-right: 1px solid rgba(85, 99, 109, 0.65);
        }}

        section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.4rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }}

        .sidebar-title-card {{
            background: linear-gradient(145deg, #2B353E 0%, #35424C 100%);
            border: 1px solid rgba(131, 151, 163, 0.55);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.20);
        }}

        .sidebar-title-card h2 {{
            color: var(--text) !important;
            font-size: 1.25rem;
            line-height: 1.35;
            margin: 0;
        }}

        .sidebar-title-card p {{
            color: var(--muted) !important;
            font-size: 0.88rem;
            line-height: 1.6;
            margin: 8px 0 0;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] {{
            gap: 0.35rem;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            background: rgba(45, 55, 64, 0.72);
            border: 1px solid rgba(85, 99, 109, 0.55);
            border-radius: 12px;
            padding: 9px 12px;
            margin-bottom: 4px;
            transition: 0.16s ease;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: rgba(52, 63, 73, 0.95);
            border-color: rgba(131, 151, 163, 0.90);
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background: linear-gradient(135deg, rgba(125, 144, 157, 0.78), rgba(75, 91, 103, 0.92));
            border-color: rgba(166, 180, 188, 0.95);
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
            color: var(--text) !important;
            font-weight: 650 !important;
        }}

        .hero-card, .custom-card, .section-card {{
            background: linear-gradient(145deg, rgba(45, 55, 64, 0.96), rgba(52, 63, 73, 0.93));
            border: 1px solid rgba(85, 99, 109, 0.70);
            border-radius: 18px;
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
        }}

        .hero-card {{
            padding: 28px 30px;
            margin-bottom: 20px;
        }}

        .hero-title {{
            font-size: 2.35rem;
            line-height: 1.25;
            color: var(--text);
            font-weight: 900;
        }}

        .hero-subtitle {{
            color: var(--muted);
            font-size: 1.02rem;
            line-height: 1.75;
            margin-top: 8px;
        }}

        .section-card {{
            padding: 20px 22px;
            margin-bottom: 18px;
        }}

        .tag {{
            display: inline-block;
            background: rgba(131, 151, 163, 0.20);
            color: var(--text);
            border: 1px solid rgba(166, 180, 188, 0.45);
            border-radius: 999px;
            padding: 5px 11px;
            margin: 12px 6px 0 0;
            font-size: 0.84rem;
            font-weight: 650;
        }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, rgba(45, 55, 64, 0.98), rgba(52, 63, 73, 0.95));
            border: 1px solid rgba(85, 99, 109, 0.72);
            border-radius: 15px;
            padding: 16px 18px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.15);
        }}

        div[data-testid="stMetricLabel"] p {{
            color: var(--muted) !important;
            font-size: 0.91rem !important;
            font-weight: 650 !important;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--text) !important;
            font-weight: 850 !important;
        }}

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div {{
            background-color: #232B32 !important;
            border-color: rgba(131, 151, 163, 0.68) !important;
            color: var(--text) !important;
            border-radius: 11px !important;
        }}

        input, textarea {{
            color: var(--text) !important;
            caret-color: var(--text) !important;
        }}

        div[data-baseweb="popover"],
        ul[role="listbox"] {{
            background: #273039 !important;
            color: var(--text) !important;
        }}

        li[role="option"] {{
            color: var(--text) !important;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            background: linear-gradient(135deg, #778B98 0%, #607580 100%);
            color: #FFFDF8 !important;
            border: 1px solid rgba(166, 180, 188, 0.60);
            border-radius: 11px;
            font-weight: 750;
            min-height: 2.8rem;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.16);
            transition: 0.15s ease;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: linear-gradient(135deg, #889CA8 0%, #6D818D 100%);
            border-color: rgba(241, 237, 230, 0.75);
            transform: translateY(-1px);
        }}

        .stButton > button:disabled {{
            background: #46525B !important;
            color: #AFA9A0 !important;
            border-color: #55636D !important;
            opacity: 0.75;
        }}

        div[data-testid="stDataFrame"] {{
            background: rgba(35, 43, 50, 0.88);
            border: 1px solid rgba(85, 99, 109, 0.72);
            border-radius: 14px;
            padding: 6px;
        }}

        div[data-testid="stAlert"] {{
            background: rgba(52, 63, 73, 0.92) !important;
            border: 1px solid rgba(131, 151, 163, 0.55) !important;
            border-radius: 13px !important;
        }}

        div[data-testid="stTabs"] button {{
            color: var(--muted) !important;
            font-weight: 700 !important;
        }}

        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--text) !important;
            border-bottom-color: var(--accent) !important;
        }}

        details {{
            background: rgba(45, 55, 64, 0.76);
            border: 1px solid rgba(85, 99, 109, 0.62);
            border-radius: 12px;
            padding: 4px 10px;
        }}

        hr {{
            border-color: rgba(85, 99, 109, 0.62) !important;
        }}

        code, pre {{
            background: #182027 !important;
            color: #E5E0D8 !important;
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_custom_style()


# =========================================================
# 路徑設定
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
LOCAL_DB_PATH = PROJECT_ROOT / "股市資料庫" / "data" / "data.db"
DEMO_DB_PATH = PROJECT_ROOT / "demo" / "demo_data.db"
DATA_DB_PATH = LOCAL_DB_PATH if LOCAL_DB_PATH.exists() else DEMO_DB_PATH
IS_DEMO_MODE = DATA_DB_PATH == DEMO_DB_PATH

SCRIPT_1 = PROJECT_ROOT / "1計算多空指標" / "calculate_price_indicators.py"
SCRIPT_2 = PROJECT_ROOT / "2股價預測" / "train_price_prediction.py"
SCRIPT_3 = PROJECT_ROOT / "3多空指標股票篩選器" / "simple_stock_screener.py"

MARKET_CSV = (
    PROJECT_ROOT
    / "1計算多空指標"
    / "subproject_1_market_indicators"
    / "output"
    / "market_indicators.csv"
)
LATEST_MARKET_CSV = (
    PROJECT_ROOT
    / "1計算多空指標"
    / "subproject_1_market_indicators"
    / "output"
    / "latest_market_indicators.csv"
)
BULL_BEAR_SUMMARY_CSV = (
    PROJECT_ROOT
    / "1計算多空指標"
    / "subproject_1_market_indicators"
    / "output"
    / "bull_bear_summary.csv"
)
PREDICTION_CSV = PROJECT_ROOT / "2股價預測" / "output" / "latest_price_predictions.csv"
PREDICTION_HISTORY_CSV = PROJECT_ROOT / "2股價預測" / "output" / "price_predictions.csv"
MODEL_REPORT_TXT = PROJECT_ROOT / "2股價預測" / "output" / "model_report.txt"
FEATURE_IMPORTANCE_CSV = PROJECT_ROOT / "2股價預測" / "output" / "feature_importance.csv"
SCREENER_CSV = (
    PROJECT_ROOT
    / "3多空指標股票篩選器"
    / "output"
    / "simple_stock_screener_results.csv"
)

HISTORY_ROOT = BASE_DIR / "output" / "analysis_history"


# =========================================================
# 共用資料工具
# =========================================================
def normalize_stock_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().replace(".0", "")
    if text.isdigit() and len(text) <= 4:
        return text.zfill(4)
    return text


def normalize_stock_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "stock_id" in df.columns:
        df["stock_id"] = df["stock_id"].map(normalize_stock_id)
    return df


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("--", "", regex=False)
        .str.replace("%", "", regex=False),
        errors="coerce",
    )


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = normalize_stock_column(df)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df.loc[:, ~df.columns.duplicated()].copy()


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    attempts = ["utf-8-sig", "utf-8", "big5"]
    last_error = None
    for encoding in attempts:
        try:
            return prepare_dataframe(pd.read_csv(path, encoding=encoding))
        except Exception as exc:  # pragma: no cover - 介面執行時才會顯示
            last_error = exc

    st.error(f"讀取檔案失敗：{path}")
    if last_error:
        st.caption(str(last_error))
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_stock_list(db_path: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()

    try:
        with sqlite3.connect(path) as conn:
            df = pd.read_sql("SELECT * FROM stockList", conn)
        return prepare_dataframe(df)
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_stock_price(db_path: str, stock_id: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()

    sid = normalize_stock_id(stock_id)
    sid_number = sid.lstrip("0") or "0"

    try:
        with sqlite3.connect(path) as conn:
            query = """
                SELECT *
                FROM price
                WHERE CAST(stock_id AS TEXT) = ?
                   OR CAST(stock_id AS TEXT) = ?
                   OR CAST(stock_id AS INTEGER) = ?
                ORDER BY date
            """
            df = pd.read_sql(query, conn, params=(sid, sid_number, int(sid_number)))
    except Exception:
        return pd.DataFrame()

    df = prepare_dataframe(df)
    if df.empty:
        return df

    price_number_cols = [
        "開盤價",
        "最高價",
        "最低價",
        "收盤價",
        "成交股數",
        "成交金額",
        "本益比",
    ]
    for col in price_number_cols:
        if col in df.columns:
            df[col] = numeric_series(df[col])

    if "date" in df.columns:
        df = df.dropna(subset=["date"])
    if "收盤價" in df.columns:
        df = df.dropna(subset=["收盤價"])

    return df.sort_values("date").reset_index(drop=True)


def file_status(path: Path) -> tuple[str, str, str]:
    if path.exists():
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = f"{path.stat().st_size / 1024:.2f}"
        return "存在", modified, size_kb
    return "不存在", "-", "-"


def safe_unique_count(df: pd.DataFrame, column: str) -> int:
    if df.empty or column not in df.columns:
        return 0
    return int(df[column].astype(str).nunique())


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def filter_stock(df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    if df.empty or "stock_id" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    sid = normalize_stock_id(stock_id)
    return df[df["stock_id"].astype(str) == sid].copy()


def filter_date_range(
    df: pd.DataFrame,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df.copy()

    result = df.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["date"])

    if start_date is not None:
        result = result[result["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        result = result[result["date"] <= pd.Timestamp(end_date)]
    return result.sort_values("date").reset_index(drop=True)


def resolve_range(
    range_label: str,
    maximum_date: pd.Timestamp,
    custom_value,
) -> tuple[pd.Timestamp | None, pd.Timestamp]:
    end_date = pd.Timestamp(maximum_date).normalize()

    day_map = {
        "近 1 個月": 31,
        "近 3 個月": 93,
        "近 6 個月": 186,
        "近 1 年": 366,
        "近 3 年": 1096,
    }

    if range_label in day_map:
        return end_date - pd.Timedelta(days=day_map[range_label]), end_date

    if range_label == "自訂日期":
        if isinstance(custom_value, (tuple, list)) and len(custom_value) == 2:
            return pd.Timestamp(custom_value[0]), pd.Timestamp(custom_value[1])
        if isinstance(custom_value, date):
            custom_date = pd.Timestamp(custom_value)
            return custom_date, custom_date

    return None, end_date


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if result.empty or "收盤價" not in result.columns:
        return result

    result["收盤價"] = numeric_series(result["收盤價"])
    for period in (5, 20, 60):
        result[f"MA{period}"] = result["收盤價"].rolling(period, min_periods=1).mean()
    return result


def to_probability_percent(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if pd.isna(number):
        return None
    if 0 <= number <= 1:
        return number * 100
    return number


def find_prediction_percent(*rows: pd.Series | None) -> float | None:
    candidate_columns = [
        "prediction_percent",
        "predict_proba_up",
        "up_probability",
        "probability_up",
    ]
    for row in rows:
        if row is None:
            continue
        for col in candidate_columns:
            if col in row.index:
                result = to_probability_percent(row.get(col))
                if result is not None:
                    return result
    return None


# =========================================================
# 執行腳本
# =========================================================
def run_script(script_path: Path) -> dict:
    if not script_path.exists():
        return {
            "name": script_path.name,
            "success": False,
            "stdout": "",
            "stderr": f"找不到程式檔案：{script_path}",
        }

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "name": script_path.name,
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def render_execution_result(result: dict) -> None:
    if result["success"]:
        st.success(f"{result['name']} 執行成功")
    else:
        st.error(f"{result['name']} 執行失敗")

    output = result["stdout"] if result["success"] else result["stderr"]
    if output:
        with st.expander(f"查看 {result['name']} 執行內容"):
            st.code(output)


# =========================================================
# Plotly 圖表工具
# =========================================================
def base_layout(title: str, height: int = 430) -> dict:
    return {
        "title": {
            "text": title,
            "x": 0.01,
            "xanchor": "left",
            "font": {"color": COLORS["text"], "size": 18},
        },
        "height": height,
        "paper_bgcolor": COLORS["card"],
        "plot_bgcolor": COLORS["card"],
        "font": {"color": COLORS["muted"]},
        "margin": {"l": 45, "r": 25, "t": 60, "b": 55},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"color": COLORS["muted"]},
        },
        "hovermode": "x unified",
    }


def style_axis(fig, x_title: str = "日期", y_title: str = "") -> None:
    fig.update_xaxes(
        title_text=x_title,
        tickangle=0,
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"], "size": 11},
        title_font={"color": COLORS["muted"]},
        automargin=True,
    )
    fig.update_yaxes(
        title_text=y_title,
        gridcolor=COLORS["grid"],
        zerolinecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"], "size": 11},
        title_font={"color": COLORS["muted"]},
        automargin=True,
    )


def render_plotly(fig) -> None:
    st.plotly_chart(
        fig,
        use_container_width=True,
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )


def horizontal_bar_chart(
    data: pd.DataFrame,
    name_col: str,
    value_col: str,
    title: str,
    value_title: str = "數值",
) -> None:
    plot_df = data[[name_col, value_col]].copy().dropna()
    if plot_df.empty:
        st.info("目前沒有可繪製的資料。")
        return

    plot_df[value_col] = numeric_series(plot_df[value_col])
    plot_df = plot_df.dropna(subset=[value_col]).sort_values(value_col, ascending=True)

    if not PLOTLY_AVAILABLE:
        st.bar_chart(plot_df.set_index(name_col)[value_col])
        return

    fig = go.Figure(
        go.Bar(
            x=plot_df[value_col],
            y=plot_df[name_col].astype(str),
            orientation="h",
            marker_color=COLORS["accent"],
            text=plot_df[value_col],
            textposition="auto",
            hovertemplate=f"%{{y}}<br>{value_title}：%{{x}}<extra></extra>",
        )
    )
    fig.update_layout(**base_layout(title, max(360, len(plot_df) * 28 + 120)))
    style_axis(fig, x_title=value_title, y_title="")
    render_plotly(fig)


def price_volume_chart(price_df: pd.DataFrame, title: str) -> None:
    if price_df.empty or "date" not in price_df.columns or "收盤價" not in price_df.columns:
        st.info("目前沒有足夠的股價資料可以繪圖。")
        return

    if not PLOTLY_AVAILABLE:
        cols = [col for col in ["收盤價", "MA5", "MA20", "MA60"] if col in price_df.columns]
        st.line_chart(price_df.set_index("date")[cols])
        return

    has_ohlc = all(col in price_df.columns for col in ["開盤價", "最高價", "最低價", "收盤價"])
    has_volume = "成交股數" in price_df.columns

    rows = 2 if has_volume else 1
    row_heights = [0.72, 0.28] if has_volume else [1.0]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=row_heights,
    )

    if has_ohlc:
        fig.add_trace(
            go.Candlestick(
                x=price_df["date"],
                open=price_df["開盤價"],
                high=price_df["最高價"],
                low=price_df["最低價"],
                close=price_df["收盤價"],
                name="K 線",
                increasing_line_color=COLORS["red"],
                increasing_fillcolor=COLORS["red"],
                decreasing_line_color=COLORS["green"],
                decreasing_fillcolor=COLORS["green"],
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=price_df["date"],
                y=price_df["收盤價"],
                mode="lines",
                name="收盤價",
                line={"color": COLORS["text"], "width": 2.2},
            ),
            row=1,
            col=1,
        )

    ma_colors = {"MA5": COLORS["yellow"], "MA20": COLORS["accent_2"], "MA60": COLORS["blue"]}
    for ma_col in ["MA5", "MA20", "MA60"]:
        if ma_col in price_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=price_df["date"],
                    y=price_df[ma_col],
                    mode="lines",
                    name=ma_col,
                    line={"color": ma_colors[ma_col], "width": 1.7},
                ),
                row=1,
                col=1,
            )

    if has_volume:
        volume_colors = [
            COLORS["red"] if close >= open_ else COLORS["green"]
            for close, open_ in zip(price_df["收盤價"], price_df.get("開盤價", price_df["收盤價"]))
        ]
        fig.add_trace(
            go.Bar(
                x=price_df["date"],
                y=price_df["成交股數"],
                name="成交股數",
                marker_color=volume_colors,
                opacity=0.72,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(**base_layout(title, 650 if has_volume else 500))
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_xaxes(
        tickangle=0,
        tickformat="%Y-%m-%d",
        showgrid=False,
        linecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"], "size": 10},
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor=COLORS["grid"],
        linecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"], "size": 10},
        automargin=True,
    )
    fig.update_yaxes(title_text="股價", row=1, col=1)
    if has_volume:
        fig.update_yaxes(title_text="成交量", row=2, col=1)
    render_plotly(fig)


def multi_line_chart(
    df: pd.DataFrame,
    columns: list[str],
    title: str,
    y_title: str = "數值",
    reference_lines: list[tuple[float, str]] | None = None,
) -> None:
    columns = [col for col in columns if col in df.columns]
    if df.empty or "date" not in df.columns or not columns:
        st.info(f"目前沒有 {title} 的可用資料。")
        return

    plot_df = df[["date"] + columns].copy()
    for col in columns:
        plot_df[col] = numeric_series(plot_df[col])
    plot_df = plot_df.dropna(subset=["date"])

    if not PLOTLY_AVAILABLE:
        st.line_chart(plot_df.set_index("date")[columns])
        return

    palette = [COLORS["accent_2"], COLORS["yellow"], COLORS["green"], COLORS["red"]]
    fig = go.Figure()
    for index, col in enumerate(columns):
        fig.add_trace(
            go.Scatter(
                x=plot_df["date"],
                y=plot_df[col],
                mode="lines",
                name=col,
                line={"color": palette[index % len(palette)], "width": 2.0},
            )
        )

    if reference_lines:
        for line_value, label in reference_lines:
            fig.add_hline(
                y=line_value,
                line_dash="dot",
                line_color=COLORS["border"],
                annotation_text=label,
                annotation_font_color=COLORS["muted"],
            )

    fig.update_layout(**base_layout(title, 410))
    style_axis(fig, x_title="日期", y_title=y_title)
    fig.update_xaxes(tickformat="%Y-%m-%d", nticks=9)
    render_plotly(fig)


def macd_chart(df: pd.DataFrame) -> None:
    macd_col = first_existing_column(df, ["macd", "MACD"])
    signal_col = first_existing_column(df, ["macd_signal", "signal_line", "MACD_signal"])
    hist_col = first_existing_column(df, ["macd_hist", "macd_histogram", "histogram"])

    if not macd_col:
        st.info("目前沒有 MACD 欄位。")
        return

    plot_df = df[[col for col in ["date", macd_col, signal_col, hist_col] if col]].copy()
    for col in [macd_col, signal_col, hist_col]:
        if col and col in plot_df.columns:
            plot_df[col] = numeric_series(plot_df[col])

    if not PLOTLY_AVAILABLE:
        line_cols = [col for col in [macd_col, signal_col] if col]
        st.line_chart(plot_df.set_index("date")[line_cols])
        return

    fig = go.Figure()
    if hist_col:
        colors = [COLORS["red"] if value >= 0 else COLORS["green"] for value in plot_df[hist_col].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=plot_df["date"],
                y=plot_df[hist_col],
                name="MACD 柱狀",
                marker_color=colors,
                opacity=0.72,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=plot_df["date"],
            y=plot_df[macd_col],
            name="MACD",
            mode="lines",
            line={"color": COLORS["accent_2"], "width": 2},
        )
    )
    if signal_col:
        fig.add_trace(
            go.Scatter(
                x=plot_df["date"],
                y=plot_df[signal_col],
                name="Signal",
                mode="lines",
                line={"color": COLORS["yellow"], "width": 2},
            )
        )

    fig.update_layout(**base_layout("MACD", 420))
    style_axis(fig, x_title="日期", y_title="MACD")
    fig.update_xaxes(tickformat="%Y-%m-%d", nticks=9)
    render_plotly(fig)


# =========================================================
# 分析紀錄
# =========================================================
def history_available() -> bool:
    try:
        HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def save_analysis_record(payload: dict) -> tuple[str | None, str | None]:
    if not history_available():
        return None, "無法建立分析紀錄資料夾。"

    record_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    record_dir = HISTORY_ROOT / record_id

    try:
        record_dir.mkdir(parents=True, exist_ok=False)

        metadata = {
            "record_id": record_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "stock_id": payload["stock_id"],
            "stock_name": payload["stock_name"],
            "range_label": payload["range_label"],
            "start_date": str(payload["start_date"].date()) if payload["start_date"] is not None else "最早資料",
            "end_date": str(payload["end_date"].date()),
            "summary": payload["summary"],
        }

        with (record_dir / "summary.json").open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

        dataframe_map = {
            "price.csv": payload["price_df"],
            "indicator.csv": payload["indicator_df"],
            "prediction.csv": payload["prediction_df"],
            "screen.csv": payload["screen_df"],
        }
        for filename, dataframe in dataframe_map.items():
            dataframe.to_csv(record_dir / filename, index=False, encoding="utf-8-sig")

        return record_id, None
    except Exception as exc:
        return None, str(exc)


def load_history_records() -> list[dict]:
    if not HISTORY_ROOT.exists():
        return []

    records = []
    for summary_path in HISTORY_ROOT.glob("*/summary.json"):
        try:
            with summary_path.open("r", encoding="utf-8") as file:
                metadata = json.load(file)
            metadata["record_dir"] = str(summary_path.parent)
            records.append(metadata)
        except (OSError, json.JSONDecodeError):
            continue

    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


def load_history_payload(record: dict) -> dict:
    record_dir = Path(record["record_dir"])

    def load_snapshot(filename: str) -> pd.DataFrame:
        path = record_dir / filename
        return read_csv_safe(path)

    start_text = record.get("start_date")
    end_text = record.get("end_date")
    start_date = None if start_text in (None, "", "最早資料") else pd.Timestamp(start_text)
    end_date = pd.Timestamp(end_text)

    return {
        "stock_id": record.get("stock_id", ""),
        "stock_name": record.get("stock_name", ""),
        "range_label": record.get("range_label", "歷史紀錄"),
        "start_date": start_date,
        "end_date": end_date,
        "summary": record.get("summary", {}),
        "price_df": load_snapshot("price.csv"),
        "indicator_df": load_snapshot("indicator.csv"),
        "prediction_df": load_snapshot("prediction.csv"),
        "screen_df": load_snapshot("screen.csv"),
        "record_id": record.get("record_id"),
        "history_mode": True,
    }


# =========================================================
# 分析核心
# =========================================================
def build_stock_catalog(
    stock_list_df: pd.DataFrame,
    screener_df: pd.DataFrame,
    market_df: pd.DataFrame,
) -> pd.DataFrame:
    pieces = []

    if not stock_list_df.empty and "stock_id" in stock_list_df.columns:
        columns = ["stock_id"]
        if "股票名稱" in stock_list_df.columns:
            columns.append("股票名稱")
        pieces.append(stock_list_df[columns].copy())

    if not screener_df.empty and "stock_id" in screener_df.columns:
        columns = ["stock_id"]
        if "股票名稱" in screener_df.columns:
            columns.append("股票名稱")
        pieces.append(screener_df[columns].copy())

    if not market_df.empty and "stock_id" in market_df.columns:
        columns = ["stock_id"]
        if "股票名稱" in market_df.columns:
            columns.append("股票名稱")
        pieces.append(market_df[columns].copy())

    if not pieces:
        return pd.DataFrame(columns=["stock_id", "股票名稱", "顯示名稱"])

    catalog = pd.concat(pieces, ignore_index=True, sort=False)
    catalog = normalize_stock_column(catalog)
    if "股票名稱" not in catalog.columns:
        catalog["股票名稱"] = ""
    catalog["股票名稱"] = catalog["股票名稱"].fillna("").astype(str)
    catalog = catalog.sort_values(["stock_id", "股票名稱"]).drop_duplicates("stock_id", keep="last")
    catalog["顯示名稱"] = catalog.apply(
        lambda row: f"{row['stock_id']} - {row['股票名稱']}" if row["股票名稱"] else row["stock_id"],
        axis=1,
    )
    return catalog.reset_index(drop=True)


def extract_latest_row(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    if "date" in df.columns:
        ordered = df.sort_values("date")
        return ordered.iloc[-1]
    return df.iloc[0]


def make_strategy_summary(
    price_df: pd.DataFrame,
    indicator_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    screen_df: pd.DataFrame,
) -> dict:
    latest_price = extract_latest_row(price_df)
    latest_indicator = extract_latest_row(indicator_df)
    latest_prediction = extract_latest_row(prediction_df)
    latest_screen = extract_latest_row(screen_df)

    close_price = None
    ma20 = None
    ma60 = None
    if latest_price is not None:
        close_price = latest_price.get("收盤價")
        ma20 = latest_price.get("MA20")
        ma60 = latest_price.get("MA60")

    signal = "—"
    for row in [latest_screen, latest_indicator]:
        if row is not None:
            signal_col = first_existing_column(pd.DataFrame([row]), ["signal", "多空訊號"])
            if signal_col and pd.notna(row.get(signal_col)):
                signal = str(row.get(signal_col))
                break

    category = "—"
    if latest_screen is not None and "screen_category" in latest_screen.index:
        category = str(latest_screen.get("screen_category", "—"))

    probability = find_prediction_percent(latest_screen, latest_prediction)

    rsi_value = None
    if latest_indicator is not None:
        rsi_col = first_existing_column(pd.DataFrame([latest_indicator]), ["rsi_14", "RSI", "rsi"])
        if rsi_col:
            try:
                rsi_value = float(latest_indicator.get(rsi_col))
            except (TypeError, ValueError):
                rsi_value = None

    score_value = None
    if latest_indicator is not None:
        score_col = first_existing_column(
            pd.DataFrame([latest_indicator]),
            ["long_short_signal_score", "bull_bear_score", "score"],
        )
        if score_col:
            try:
                score_value = float(latest_indicator.get(score_col))
            except (TypeError, ValueError):
                score_value = None

    positive_points = 0
    negative_points = 0

    if close_price is not None and ma20 is not None and pd.notna(close_price) and pd.notna(ma20):
        positive_points += int(float(close_price) >= float(ma20))
        negative_points += int(float(close_price) < float(ma20))
    if close_price is not None and ma60 is not None and pd.notna(close_price) and pd.notna(ma60):
        positive_points += int(float(close_price) >= float(ma60))
        negative_points += int(float(close_price) < float(ma60))
    if probability is not None:
        positive_points += int(probability >= 55)
        negative_points += int(probability <= 45)
    if rsi_value is not None:
        positive_points += int(50 <= rsi_value <= 70)
        negative_points += int(rsi_value < 40 or rsi_value > 75)
    if score_value is not None:
        positive_points += int(score_value > 0)
        negative_points += int(score_value < 0)
    if "強勢看多" in category or "偏多" in signal:
        positive_points += 2
    if "風險偏高" in category or "偏空" in signal:
        negative_points += 2

    if positive_points >= negative_points + 2:
        strategy = "偏多觀察"
        strategy_note = "多項指標偏正向，可持續觀察趨勢與量能是否延續。"
    elif negative_points >= positive_points + 2:
        strategy = "風險偏高"
        strategy_note = "目前負向條件較多，應留意跌破均線、量價背離或預測轉弱。"
    else:
        strategy = "中性觀察"
        strategy_note = "多空條件尚未形成明顯共識，建議等待訊號更清楚。"

    return {
        "close_price": None if close_price is None or pd.isna(close_price) else float(close_price),
        "ma20": None if ma20 is None or pd.isna(ma20) else float(ma20),
        "ma60": None if ma60 is None or pd.isna(ma60) else float(ma60),
        "signal": signal,
        "category": category,
        "probability": probability,
        "rsi": rsi_value,
        "score": score_value,
        "strategy": strategy,
        "strategy_note": strategy_note,
        "positive_points": positive_points,
        "negative_points": negative_points,
    }


def perform_stock_analysis(
    stock_id: str,
    stock_name: str,
    range_label: str,
    custom_dates,
    market_df: pd.DataFrame,
    prediction_history_df: pd.DataFrame,
    screener_df: pd.DataFrame,
) -> dict:
    sid = normalize_stock_id(stock_id)

    full_price_df = calculate_moving_averages(load_stock_price(str(DATA_DB_PATH), sid))
    full_indicator_df = filter_stock(market_df, sid)
    full_prediction_df = filter_stock(prediction_history_df, sid)
    screen_df = filter_stock(screener_df, sid)

    available_max_dates = []
    for dataframe in [full_price_df, full_indicator_df, full_prediction_df]:
        if not dataframe.empty and "date" in dataframe.columns:
            maximum = pd.to_datetime(dataframe["date"], errors="coerce").max()
            if pd.notna(maximum):
                available_max_dates.append(maximum)

    maximum_date = max(available_max_dates) if available_max_dates else pd.Timestamp.today().normalize()
    start_date, end_date = resolve_range(range_label, maximum_date, custom_dates)

    price_df = filter_date_range(full_price_df, start_date, end_date)
    indicator_df = filter_date_range(full_indicator_df, start_date, end_date)
    prediction_df = filter_date_range(full_prediction_df, start_date, end_date)

    summary = make_strategy_summary(price_df, indicator_df, prediction_df, screen_df)

    return {
        "stock_id": sid,
        "stock_name": stock_name or sid,
        "range_label": range_label,
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "price_df": price_df,
        "indicator_df": indicator_df,
        "prediction_df": prediction_df,
        "screen_df": screen_df,
        "history_mode": False,
    }


def show_dataframe(df: pd.DataFrame, title: str, max_rows: int | None = None) -> None:
    st.subheader(title)
    if df.empty:
        st.info("目前沒有資料。")
        return

    display_df = df.tail(max_rows) if max_rows else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# =========================================================
# 載入資料
# =========================================================
market_df = read_csv_safe(MARKET_CSV)
latest_market_df = read_csv_safe(LATEST_MARKET_CSV)
summary_df = read_csv_safe(BULL_BEAR_SUMMARY_CSV)
prediction_df = read_csv_safe(PREDICTION_CSV)
prediction_history_df = read_csv_safe(PREDICTION_HISTORY_CSV)
feature_importance_df = read_csv_safe(FEATURE_IMPORTANCE_CSV)
screener_df = read_csv_safe(SCREENER_CSV)
stock_list_df = load_stock_list(str(DATA_DB_PATH))

# 股票名稱補齊
if not stock_list_df.empty and "stock_id" in stock_list_df.columns and "股票名稱" in stock_list_df.columns:
    name_map = (
        stock_list_df[["stock_id", "股票名稱"]]
        .dropna(subset=["stock_id"])
        .drop_duplicates("stock_id")
    )
    for dataframe_name in ["market_df", "latest_market_df", "prediction_df", "prediction_history_df", "screener_df"]:
        dataframe = globals()[dataframe_name]
        if not dataframe.empty and "stock_id" in dataframe.columns and "股票名稱" not in dataframe.columns:
            globals()[dataframe_name] = dataframe.merge(name_map, on="stock_id", how="left")

catalog_df = build_stock_catalog(stock_list_df, screener_df, market_df)
if IS_DEMO_MODE and not stock_list_df.empty and "stock_id" in stock_list_df.columns:
    demo_stock_ids = set(stock_list_df["stock_id"].astype(str))
    catalog_df = catalog_df[catalog_df["stock_id"].astype(str).isin(demo_stock_ids)].reset_index(drop=True)


# =========================================================
# 側邊欄
# =========================================================
st.sidebar.markdown(
    """
    <div class="sidebar-title-card">
        <h2>📊 AI 奇摩股價分析系統</h2>
        <p>保留原本功能，新增時間 Range、一鍵完整分析、Power BI 風格圖表與分析紀錄。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

PAGE_OPTIONS = {
    "🏠 首頁": "首頁",
    "🗂️ 資料檢查": "資料檢查",
    "⚙️ 流程執行": "流程執行",
    "📈 多空指標分析": "多空指標分析",
    "🤖 股價預測模型": "股價預測模型",
    "🔎 股票篩選器": "股票篩選器",
    "📊 戰略儀表板": "戰略儀表板",
    "🕘 分析紀錄": "分析紀錄",
    "📘 專案說明": "專案說明",
}

def open_stock_in_dashboard(stock_display_name: str, stock_id: str) -> None:
    """把側邊欄搜尋結果真正帶入戰略儀表板，並切換到該頁。"""
    st.session_state["preferred_stock_id"] = stock_id
    st.session_state["dashboard_stock"] = stock_display_name
    st.session_state["page_selector"] = "📊 戰略儀表板"
    # 避免仍顯示上一支股票的分析結果，要求使用者重新按一次完整分析。
    st.session_state.pop("active_analysis", None)
    st.session_state.pop("analysis_save_error", None)


selected_page_label = st.sidebar.radio("選擇頁面", list(PAGE_OPTIONS.keys()), key="page_selector")
page = PAGE_OPTIONS[selected_page_label]

st.sidebar.markdown("---")
st.sidebar.subheader("股票搜尋")
search_text = st.sidebar.text_input("輸入股票代碼或名稱", placeholder="例如：0050、台積電")

if search_text and not catalog_df.empty:
    keyword = search_text.strip()
    search_result = catalog_df[
        catalog_df["stock_id"].astype(str).str.contains(keyword, case=False, na=False)
        | catalog_df["股票名稱"].astype(str).str.contains(keyword, case=False, na=False)
    ].copy()

    if search_result.empty:
        st.sidebar.warning("找不到符合的股票")
    else:
        selected_search_stock = st.sidebar.selectbox(
            "搜尋結果",
            search_result["顯示名稱"].tolist(),
            key="sidebar_search_result",
        )
        selected_search_id = selected_search_stock.split(" - ")[0]
        st.sidebar.caption("選好股票後，按下方按鈕即可直接前往戰略儀表板。")
        st.sidebar.button(
            "帶入戰略儀表板",
            use_container_width=True,
            type="primary",
            on_click=open_stock_in_dashboard,
            args=(selected_search_stock, selected_search_id),
        )
elif search_text and catalog_df.empty:
    st.sidebar.warning("目前沒有可搜尋的股票基本資料。")

st.sidebar.markdown("---")
st.sidebar.caption("系統僅供資料分析練習與輔助觀察，不構成投資建議。")


# =========================================================
# 首頁
# =========================================================
if page == "首頁":
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">AI 奇摩股價分析系統</div>
            <div class="hero-subtitle">
                整合多空指標、機器學習預測、股票篩選器、技術線圖與歷史分析紀錄，
                讓一次股票查詢可以完整完成資料整理、趨勢判讀與回顧。
            </div>
            <div>
                <span class="tag">Python</span>
                <span class="tag">Pandas</span>
                <span class="tag">Scikit-learn</span>
                <span class="tag">Streamlit</span>
                <span class="tag">Plotly</span>
                <span class="tag">SQLite</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    database_stock_count = safe_unique_count(market_df, "stock_id")
    screener_stock_count = safe_unique_count(screener_df, "stock_id")
    strong_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "強勢看多").sum())
    watch_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "保守觀察").sum())
    risk_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "風險偏高").sum())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("資料庫股票數", database_stock_count)
    col2.metric("篩選股票數", screener_stock_count)
    col3.metric("強勢看多", strong_count)
    col4.metric("保守觀察", watch_count)
    col5.metric("風險偏高", risk_count)

    st.markdown(
        """
        <div class="section-card">
            <h3>系統流程</h3>
            <p>原始股價資料 → 多空指標 → 股價預測 → 股票篩選 → 個股完整分析 → 自動儲存分析紀錄。</p>
            <p>在「戰略儀表板」選擇股票與時間 Range，只要按一次「開始完整分析」，即可完成所有圖表與策略摘要。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 資料檢查
# =========================================================
elif page == "資料檢查":
    st.title("🗂️ 資料檢查")

    check_items = [
        ("股市原始資料庫", DATA_DB_PATH),
        ("子專案 1 多空指標總表", MARKET_CSV),
        ("子專案 1 最新多空指標", LATEST_MARKET_CSV),
        ("子專案 1 多空統計", BULL_BEAR_SUMMARY_CSV),
        ("子專案 2 最新預測結果", PREDICTION_CSV),
        ("子專案 2 歷史預測結果", PREDICTION_HISTORY_CSV),
        ("子專案 2 模型報告", MODEL_REPORT_TXT),
        ("子專案 2 特徵重要性", FEATURE_IMPORTANCE_CSV),
        ("子專案 3 股票篩選結果", SCREENER_CSV),
    ]

    rows = []
    for name, path in check_items:
        status, modified_time, size_kb = file_status(path)
        rows.append(
            {
                "項目": name,
                "狀態": status,
                "最後修改時間": modified_time,
                "大小 KB": size_kb,
                "路徑": str(path),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("資料來源診斷"):
        st.write(f"專案根目錄：`{PROJECT_ROOT}`")
        st.write(f"資料庫路徑：`{DATA_DB_PATH}`")
        st.write(f"stockList 筆數：{len(stock_list_df):,}")
        st.write(f"market_indicators 筆數：{len(market_df):,}")
        st.write(f"screener 筆數：{len(screener_df):,}")


# =========================================================
# 流程執行
# =========================================================
elif page == "流程執行":
    st.title("⚙️ 流程執行")
    st.info("可一鍵依序執行子專案 1、2、3，也保留原本的單獨執行按鈕。")
    if IS_DEMO_MODE:
        st.warning("目前為公開 Demo 模式，為避免雲端重新訓練與覆寫資料，流程執行功能已停用。其他分析與圖表功能可正常操作。")
        st.stop()

    if st.button("▶ 一鍵執行完整流程（1 → 2 → 3）", use_container_width=True, type="primary"):
        results = []
        progress = st.progress(0, text="準備執行完整流程…")
        scripts = [SCRIPT_1, SCRIPT_2, SCRIPT_3]

        for index, script in enumerate(scripts, start=1):
            progress.progress((index - 1) / len(scripts), text=f"正在執行：{script.name}")
            result = run_script(script)
            results.append(result)
            if not result["success"]:
                break

        progress.progress(1.0, text="完整流程執行完成")
        st.session_state["pipeline_results"] = results
        st.cache_data.clear()

    if "pipeline_results" in st.session_state:
        for result in st.session_state["pipeline_results"]:
            render_execution_result(result)

    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 子專案 1")
        st.write("重新計算多空指標")
        if st.button("執行子專案 1", use_container_width=True):
            result = run_script(SCRIPT_1)
            render_execution_result(result)
            st.cache_data.clear()

    with col2:
        st.markdown("### 子專案 2")
        st.write("重新訓練股價預測模型")
        if st.button("執行子專案 2", use_container_width=True):
            result = run_script(SCRIPT_2)
            render_execution_result(result)
            st.cache_data.clear()

    with col3:
        st.markdown("### 子專案 3")
        st.write("重新產生股票篩選清單")
        if st.button("執行子專案 3", use_container_width=True):
            result = run_script(SCRIPT_3)
            render_execution_result(result)
            st.cache_data.clear()


# =========================================================
# 多空指標分析
# =========================================================
elif page == "多空指標分析":
    st.title("📈 多空指標分析")

    if not summary_df.empty:
        st.subheader("多空分類統計")
        signal_col = first_existing_column(summary_df, ["signal", "多空訊號"])
        count_col = first_existing_column(summary_df, ["stock_count", "股票數", "count"])

        if signal_col and count_col:
            horizontal_bar_chart(summary_df, signal_col, count_col, "多空分類統計", "股票數")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("目前沒有多空分類統計資料。")

    if not latest_market_df.empty:
        signal_col = first_existing_column(latest_market_df, ["signal", "多空訊號"])
        options = ["全部"]
        if signal_col:
            options += sorted(latest_market_df[signal_col].dropna().astype(str).unique().tolist())

        selected_signal = st.selectbox("依多空訊號篩選", options)
        filtered = latest_market_df.copy()
        if selected_signal != "全部" and signal_col:
            filtered = filtered[filtered[signal_col].astype(str) == selected_signal]

        show_cols = [
            "stock_id",
            "股票名稱",
            "市場別",
            "產業別",
            "date",
            "收盤價",
            "daily_return",
            "bull_bear_score",
            "long_short_signal_score",
            "signal",
        ]
        show_cols = [col for col in show_cols if col in filtered.columns]
        st.subheader("最新多空指標資料")
        st.dataframe(filtered[show_cols] if show_cols else filtered, use_container_width=True, hide_index=True)
    else:
        st.info("目前沒有最新多空指標資料。")


# =========================================================
# 股價預測模型
# =========================================================
elif page == "股價預測模型":
    st.title("🤖 股價預測模型")

    st.subheader("模型報告")
    if MODEL_REPORT_TXT.exists():
        st.code(MODEL_REPORT_TXT.read_text(encoding="utf-8"), language="text")
    else:
        st.warning("找不到 model_report.txt")

    if not feature_importance_df.empty:
        feature_col = first_existing_column(feature_importance_df, ["feature", "特徵"])
        importance_col = first_existing_column(feature_importance_df, ["importance", "重要性"])

        if feature_col and importance_col:
            chart_df = feature_importance_df[[feature_col, importance_col]].copy()
            chart_df[importance_col] = numeric_series(chart_df[importance_col])
            chart_df = chart_df.nlargest(15, importance_col)
            horizontal_bar_chart(chart_df, feature_col, importance_col, "前 15 名特徵重要性", "重要性")
        st.dataframe(feature_importance_df, use_container_width=True, hide_index=True)
    else:
        st.info("目前沒有特徵重要性資料。")

    show_dataframe(prediction_df, "最新股價預測結果")


# =========================================================
# 股票篩選器
# =========================================================
elif page == "股票篩選器":
    st.title("🔎 股票篩選器")

    if screener_df.empty:
        st.warning("找不到股票篩選結果，請先執行子專案 3。")
    elif "screen_category" not in screener_df.columns:
        st.warning("資料中找不到 screen_category 欄位。")
    else:
        category_count = (
            screener_df["screen_category"]
            .fillna("未分類")
            .astype(str)
            .value_counts()
            .rename_axis("分類")
            .reset_index(name="股票數")
        )
        horizontal_bar_chart(category_count, "分類", "股票數", "股票篩選分類統計", "股票數")

        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            selected_category = st.selectbox(
                "選擇分類",
                ["全部"] + sorted(screener_df["screen_category"].dropna().astype(str).unique().tolist()),
            )
        with filter_col2:
            stock_keyword = st.text_input("在結果中搜尋股票代碼或名稱")

        filtered = screener_df.copy()
        if selected_category != "全部":
            filtered = filtered[filtered["screen_category"].astype(str) == selected_category]
        if stock_keyword:
            mask = filtered["stock_id"].astype(str).str.contains(stock_keyword, case=False, na=False)
            if "股票名稱" in filtered.columns:
                mask = mask | filtered["股票名稱"].astype(str).str.contains(stock_keyword, case=False, na=False)
            filtered = filtered[mask]

        probability_col = first_existing_column(filtered, ["predict_proba_up", "prediction_percent"])
        if probability_col:
            filtered[probability_col] = numeric_series(filtered[probability_col])
            filtered = filtered.sort_values(probability_col, ascending=False)

        st.dataframe(filtered, use_container_width=True, hide_index=True)


# =========================================================
# 戰略儀表板
# =========================================================
elif page == "戰略儀表板":
    st.title("📊 戰略儀表板")
    st.caption("選股票、選 Range、按一次按鈕，即可完成股價、均線、多空、預測、策略與自動存檔。")

    database_stock_count = safe_unique_count(market_df, "stock_id")
    screener_stock_count = safe_unique_count(screener_df, "stock_id")
    strong_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "強勢看多").sum())
    watch_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "保守觀察").sum())
    risk_count = int((screener_df.get("screen_category", pd.Series(dtype=str)) == "風險偏高").sum())

    metric_cols = st.columns(5)
    metric_cols[0].metric("資料庫股票數", database_stock_count)
    metric_cols[1].metric("篩選股票數", screener_stock_count)
    metric_cols[2].metric("強勢看多", strong_count)
    metric_cols[3].metric("保守觀察", watch_count)
    metric_cols[4].metric("風險偏高", risk_count)

    st.markdown("### 分析條件")
    if catalog_df.empty:
        st.error("目前無法取得股票清單，請先到『資料檢查』確認 data.db 與輸出檔案。")
    else:
        preferred_id = st.session_state.get("preferred_stock_id", "")
        default_index = 0
        if preferred_id in catalog_df["stock_id"].tolist():
            default_index = catalog_df["stock_id"].tolist().index(preferred_id)

        input_col1, input_col2 = st.columns([2, 1])
        with input_col1:
            selected_stock_text = st.selectbox(
                "股票代碼／名稱",
                catalog_df["顯示名稱"].tolist(),
                index=default_index,
                key="dashboard_stock",
            )
        with input_col2:
            range_label = st.selectbox(
                "時間 Range",
                ["近 1 個月", "近 3 個月", "近 6 個月", "近 1 年", "近 3 年", "全部資料", "自訂日期"],
                index=2,
                key="dashboard_range",
            )

        custom_dates = None
        if range_label == "自訂日期":
            today = date.today()
            custom_dates = st.date_input(
                "自訂日期範圍",
                value=(today - timedelta(days=180), today),
                key="dashboard_custom_dates",
            )

        selected_stock_id = selected_stock_text.split(" - ")[0]
        selected_row = catalog_df[catalog_df["stock_id"] == selected_stock_id].iloc[0]
        selected_stock_name = selected_row.get("股票名稱", "") or selected_stock_id

        if st.button("開始完整分析", use_container_width=True, type="primary"):
            with st.spinner(f"正在分析 {selected_stock_id} {selected_stock_name}…"):
                payload = perform_stock_analysis(
                    selected_stock_id,
                    selected_stock_name,
                    range_label,
                    custom_dates,
                    market_df,
                    prediction_history_df,
                    screener_df,
                )

                record_id, save_error = save_analysis_record(payload)
                if record_id:
                    payload["record_id"] = record_id
                st.session_state["active_analysis"] = payload
                st.session_state["analysis_save_error"] = save_error

        payload = st.session_state.get("active_analysis")

        if not payload:
            st.info("請選擇股票與時間 Range，再按一次「開始完整分析」。")
        else:
            if st.session_state.get("analysis_save_error"):
                st.warning(f"分析已完成，但紀錄儲存失敗：{st.session_state['analysis_save_error']}")
            elif payload.get("record_id") and not payload.get("history_mode"):
                st.success(f"分析完成並已自動存檔。紀錄編號：{payload['record_id']}")
            elif payload.get("history_mode"):
                st.info("目前顯示的是歷史分析快照。")

            stock_title = f"{payload['stock_id']} {payload['stock_name']}"
            range_start = payload["start_date"].strftime("%Y-%m-%d") if payload["start_date"] is not None else "最早資料"
            range_end = payload["end_date"].strftime("%Y-%m-%d")
            st.markdown(f"## {stock_title}")
            st.caption(f"分析區間：{range_start} ～ {range_end}（{payload['range_label']}）")

            summary = payload["summary"]
            summary_cols = st.columns(5)
            summary_cols[0].metric(
                "最新收盤價",
                f"{summary['close_price']:.2f}" if summary.get("close_price") is not None else "—",
            )
            summary_cols[1].metric("目前分類", summary.get("category", "—"))
            summary_cols[2].metric("多空訊號", summary.get("signal", "—"))
            summary_cols[3].metric(
                "預測上漲機率",
                f"{summary['probability']:.1f}%" if summary.get("probability") is not None else "—",
            )
            summary_cols[4].metric("策略摘要", summary.get("strategy", "—"))

            st.markdown(
                f"""
                <div class="section-card">
                    <h3>{summary.get('strategy', '中性觀察')}</h3>
                    <p>{summary.get('strategy_note', '')}</p>
                    <p>正向條件：{summary.get('positive_points', 0)}｜負向條件：{summary.get('negative_points', 0)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            overview_tab, technical_tab, prediction_tab, data_tab = st.tabs(
                ["價格與成交量", "技術指標", "預測與策略", "原始資料"]
            )

            with overview_tab:
                price_volume_chart(payload["price_df"], f"{stock_title}｜K 線、均線與成交量")

            with technical_tab:
                indicator_df = payload["indicator_df"]
                rsi_col = first_existing_column(indicator_df, ["rsi_14", "RSI", "rsi"])
                if rsi_col:
                    multi_line_chart(
                        indicator_df,
                        [rsi_col],
                        "RSI",
                        "RSI",
                        reference_lines=[(70, "超買 70"), (30, "超賣 30")],
                    )
                else:
                    st.info("目前沒有 RSI 欄位。")

                k_col = first_existing_column(indicator_df, ["k_value", "K", "k"])
                d_col = first_existing_column(indicator_df, ["d_value", "D", "d"])
                if k_col or d_col:
                    multi_line_chart(
                        indicator_df,
                        [col for col in [k_col, d_col] if col],
                        "KD 指標",
                        "KD",
                        reference_lines=[(80, "高檔 80"), (20, "低檔 20")],
                    )
                else:
                    st.info("目前沒有 KD 欄位。")

                macd_chart(indicator_df)

                score_col = first_existing_column(
                    indicator_df,
                    ["long_short_signal_score", "bull_bear_score", "score"],
                )
                if score_col:
                    multi_line_chart(indicator_df, [score_col], "多空分數", "分數", reference_lines=[(0, "中線")])
                else:
                    st.info("目前沒有多空分數欄位。")

            with prediction_tab:
                prediction_chart_df = payload["prediction_df"].copy()
                probability_col = first_existing_column(
                    prediction_chart_df,
                    ["predict_proba_up", "prediction_percent", "up_probability"],
                )
                if probability_col and not prediction_chart_df.empty:
                    prediction_chart_df["預估上漲機率 (%)"] = prediction_chart_df[probability_col].map(to_probability_percent)
                    multi_line_chart(
                        prediction_chart_df,
                        ["預估上漲機率 (%)"],
                        "歷史預估上漲機率",
                        "機率 (%)",
                        reference_lines=[(50, "50%")],
                    )
                else:
                    st.info("目前沒有此股票的歷史預測機率。")

                strategy_df = pd.DataFrame(
                    [
                        {"項目": "策略摘要", "內容": summary.get("strategy", "—")},
                        {"項目": "目前分類", "內容": summary.get("category", "—")},
                        {"項目": "多空訊號", "內容": summary.get("signal", "—")},
                        {
                            "項目": "預測上漲機率",
                            "內容": f"{summary['probability']:.1f}%" if summary.get("probability") is not None else "—",
                        },
                        {
                            "項目": "RSI",
                            "內容": f"{summary['rsi']:.2f}" if summary.get("rsi") is not None else "—",
                        },
                        {
                            "項目": "多空分數",
                            "內容": f"{summary['score']:.2f}" if summary.get("score") is not None else "—",
                        },
                        {"項目": "判讀說明", "內容": summary.get("strategy_note", "")},
                    ]
                )
                st.dataframe(strategy_df, use_container_width=True, hide_index=True)
                st.warning("以上結果為模型與技術指標的輔助整理，不應作為單一投資依據。")

            with data_tab:
                data_choice = st.selectbox(
                    "選擇資料表",
                    ["股價資料", "多空指標資料", "歷史預測資料", "股票篩選結果"],
                    key="analysis_data_choice",
                )
                data_map = {
                    "股價資料": payload["price_df"],
                    "多空指標資料": payload["indicator_df"],
                    "歷史預測資料": payload["prediction_df"],
                    "股票篩選結果": payload["screen_df"],
                }
                selected_data = data_map[data_choice]
                st.dataframe(selected_data, use_container_width=True, hide_index=True)
                if not selected_data.empty:
                    st.download_button(
                        "下載目前資料表 CSV",
                        data=selected_data.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"{payload['stock_id']}_{data_choice}.csv",
                        mime="text/csv",
                    )


# =========================================================
# 分析紀錄
# =========================================================
elif page == "分析紀錄":
    st.title("🕘 分析紀錄與回顧")
    st.caption("每次在戰略儀表板按下「開始完整分析」後，系統會自動保存當下結果。")

    records = load_history_records()
    if not records:
        st.info("目前還沒有分析紀錄。請先到戰略儀表板完成一次分析。")
    else:
        history_rows = []
        for record in records:
            summary = record.get("summary", {})
            history_rows.append(
                {
                    "分析時間": record.get("created_at", "").replace("T", " "),
                    "股票代碼": record.get("stock_id", ""),
                    "股票名稱": record.get("stock_name", ""),
                    "Range": record.get("range_label", ""),
                    "分析區間": f"{record.get('start_date', '')} ～ {record.get('end_date', '')}",
                    "策略摘要": summary.get("strategy", ""),
                    "目前分類": summary.get("category", ""),
                    "多空訊號": summary.get("signal", ""),
                    "紀錄編號": record.get("record_id", ""),
                }
            )

        history_df = pd.DataFrame(history_rows)
        st.dataframe(history_df, use_container_width=True, hide_index=True)

        label_map = {
            f"{row['分析時間']}｜{row['股票代碼']} {row['股票名稱']}｜{row['Range']}｜{row['策略摘要']}": index
            for index, row in enumerate(history_rows)
        }
        selected_label = st.selectbox("選擇要回顧的分析", list(label_map.keys()))
        selected_record = records[label_map[selected_label]]

        selected_summary = selected_record.get("summary", {})
        detail_cols = st.columns(4)
        detail_cols[0].metric("策略摘要", selected_summary.get("strategy", "—"))
        detail_cols[1].metric("目前分類", selected_summary.get("category", "—"))
        detail_cols[2].metric("多空訊號", selected_summary.get("signal", "—"))
        detail_cols[3].metric(
            "預測上漲機率",
            f"{selected_summary['probability']:.1f}%" if selected_summary.get("probability") is not None else "—",
        )

        if st.button("載入這筆紀錄到戰略儀表板", use_container_width=True, type="primary"):
            st.session_state["active_analysis"] = load_history_payload(selected_record)
            st.session_state["analysis_save_error"] = None
            st.success("已載入。請切換到『戰略儀表板』查看完整圖表。")

        record_dir = Path(selected_record["record_dir"])
        with st.expander("查看紀錄檔案位置"):
            st.code(str(record_dir))


# =========================================================
# 專案說明
# =========================================================
elif page == "專案說明":
    st.title("📘 專案說明")

    st.markdown(
        """
        ## 專案定位

        本專案為台股資料分析與機器學習預測練習系統，建立從資料整理、指標計算、
        模型訓練、股票篩選、視覺化儀表板到分析紀錄回顧的完整流程。

        ## 四個子專案

        ### 1. 計算多空指標
        根據股價、均線、成交量、動能等欄位計算多空訊號與分數。

        ### 2. 股價預測
        建立隔日漲跌預測模型，輸出預測上漲機率與特徵重要性。

        ### 3. 多空指標股票篩選器
        整合多空指標與模型預測，將股票分類為強勢看多、保守觀察、風險偏高或一般觀察。

        ### 4. 戰略儀表板
        使用 Streamlit 與 Plotly 呈現 K 線、均線、成交量、RSI、KD、MACD、多空分數與預測趨勢。

        ## 本版新增

        - 深色莫蘭迪藍灰配色，降低畫面刺激感。
        - 股票代碼與名稱正常水平顯示。
        - 日期座標固定水平顯示。
        - 近 1 個月到全部資料，以及自訂日期 Range。
        - 一個按鈕完成個股完整分析。
        - 分析完成後自動保存，可從「分析紀錄」重新載入。
        - 0050 等前導零股票代碼可正常查詢。
        - Power BI 風格的互動式 Plotly 圖表。

        ## 模型限制

        模型與技術指標皆有誤差，系統主要用於資料分析流程展示與輔助觀察，
        不應作為單一投資決策依據。
        """
    )


if not PLOTLY_AVAILABLE:
    st.sidebar.warning("尚未安裝 Plotly，部分圖表會改用 Streamlit 基礎圖表。請執行：python -m pip install plotly")
