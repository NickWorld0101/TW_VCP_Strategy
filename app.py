import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from datetime import datetime

# ── 頁面設定 ──────────────────────────────────────────
st.set_page_config(
    page_title="台股 VCP 動能選股儀表板",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 美化 ──────────────────────────────────────────
st.markdown("""
<style>
  .metric-box {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 14px 18px;
    border: 1px solid #e9ecef;
  }
  .vcp-title {
    font-size: 26px;
    font-weight: 700;
    color: #1a1a2e;
  }
  .tag-top    { background:#dbeafe; color:#1d4ed8; padding:2px 10px; border-radius:20px; font-size:12px; }
  .tag-strong { background:#dcfce7; color:#15803d; padding:2px 10px; border-radius:20px; font-size:12px; }
  .tag-watch  { background:#fef9c3; color:#92400e; padding:2px 10px; border-radius:20px; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# ── 側邊欄篩選 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 篩選條件")
    min_rs = st.slider("最低 RS 分數", 0, 99, 70)
    min_vcp = st.slider("最低 VCP 強度", 0, 99, 50)
    sectors = ["全部產業", "半導體", "AI/伺服器", "電子", "金融", "傳產", "消費", "其他"]
    sel_sector = st.selectbox("產業別", sectors)
    max_rows = st.selectbox("最多顯示幾檔", [5, 10, 20, 50], index=1)
    st.markdown("---")
    st.markdown("**資料說明**")
    st.caption("每個交易日台灣時間 16:00 自動更新\n\n資料來源：Yahoo Finance\n\n篩選依據：Minervini 趨勢模板 + VCP 波動收縮")

# ── 主標題 ─────────────────────────────────────────────
st.markdown('<div class="vcp-title">⚡ 台股 VCP 動能選股儀表板</div>', unsafe_allow_html=True)
st.caption("Volatility Contraction Pattern — 自動掃描符合趨勢模板 + 縮量整理型態的潛力個股")
st.markdown("---")

# ── 讀取資料 (加入智慧尋找最新檔與快取) ──────────────────
@st.cache_data(ttl=3600)
def load_latest_data():
    csv_files = glob.glob("vcp_*.csv")
    if not csv_files:
        return None
    latest_file = max(csv_files)
    df = pd.read_csv(latest_file)
    return df, latest_file

data_result = load_latest_data()

if data_result is None:
    st.warning("⚠️ 尚未產生資料，請在終端機執行 `python3 fetch_vcp.py` 或至 GitHub Actions 手動觸發第一次掃描。")
    st.stop()

df, current_file = data_result
st.caption(f"📂 目前讀取檔案：`{current_file}`")

if df.empty:
    st.info("今日無任何個股符合 VCP 條件，明日再來。")
    st.stop()

# ── 資料篩選 ───────────────────────────────────────────
df_f = df[df["RS分數"] >= min_rs]
df_f = df_f[df_f["VCP強度"] >= min_vcp]
if sel_sector != "全部產業":
    df_f = df_f[df_f["產業"] == sel_sector]
df_f = df_f.head(max_rows)

update_date = df["更新日期"].iloc[0] if "更新日期" in df.columns and not df.empty else datetime.now().strftime("%Y-%m-%d")

# ── 頂部統計卡片 ───────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 資料日期", update_date)
c2.metric("🎯 今日 VCP 個股數", f"{len(df)} 檔")
c3.metric("⭐ 篩選後顯示", f"{len(df_f)} 檔")
avg_rs = int(df_f["RS分數"].mean()) if not df_f.empty else 0
c4.metric("📈 平均 RS 分數", avg_rs)

st.markdown("---")

# ── 個股卡片 ───────────────────────────────────────────
st.markdown("### 🎯 個股清單")

if df_f.empty:
    st.warning("目前篩選條件下無符合個股，請調寬側邊欄的門檻。")
else:
    def rating(row):
        if row["VCP強度"] >= 80 and row["RS分數"] >= 85:
            return "top"
        elif row["VCP強度"] >= 65:
            return "strong"
        return "watch"

    df_f = df_f.copy()
    df_f["評級"] = df_f.apply(rating, axis=1)

    RATING_LABEL = {"top": "⭐ 強力推薦", "strong": "✓ 強勢候選", "watch": "👀 觀察名單"}
    RATING_COLOR = {"top": "#1d4ed8", "strong": "#15803d", "watch": "#92400e"}

    for _, row in df_f.iterrows():
        with st.container():
            col_title, col_badge = st.columns([3, 1])
            with col_title:
                # 這裡加入了股票名稱顯示，用 get 防止舊資料報錯
                stock_name = row.get('股票名稱', '')
                st.markdown(f"#### {row['股票代號']} {stock_name}　<small style='color:#888'>{row['產業']}</small>", unsafe_allow_html=True)
            with col_badge:
                label = RATING_LABEL[row['評級']]
                color = RATING_COLOR[row['評級']]
                st.markdown(f"<span style='color:{color};font-weight:600'>{label}</span>", unsafe_allow_html=True)

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("現價", f"${row['收盤價']}")
            chg = row.get("今日漲跌%", 0)
            m2.metric("今日漲跌", f"{chg:+.2f}%", delta=f"{chg:.2f}%")
            m3.metric("RS 分數", int(row["RS分數"]))
            m4.metric("VCP 強度", int(row["VCP強度"]))
            m5.metric("Pivot 進場價", f"${row['Pivot進場價']}")
            m6.metric("建議停損", f"${row['建議停損']}")

            detail1, detail2, detail3 = st.columns(3)
            detail1.caption(f"距 52 週高點：{row['距高點%']:.1f}%")
            detail2.caption(f"縮量次數：{int(row['縮量次數'])} 次")
            detail3.caption(f"量比（近10日/50日均量）：{row['量比']:.2f}")

            st.markdown("---")

# ── 圖表區 ────────────────────────────────────────────
if not df_f.empty:
    st.markdown("### 📊 視覺化分析")
    tab1, tab2 = st.tabs(["VCP 強度 vs RS 分數", "產業分佈"])

    with tab1:
        # 在圖表 hover 資訊中也加入名稱
        df_f["股票標籤"] = df_f["股票代號"].astype(str) + " " + df_f["股票名稱"].fillna("")
        fig = px.scatter(
            df_f, x="RS分數", y="VCP強度",
            size="收盤價", color="產業",
            hover_name="股票標籤",
            hover_data={"股票代號": False, "股票標籤": False, "縮量次數": True, "距高點%": True, "Pivot進場價": True},
            title="VCP 強度 vs RS 分數（泡泡大小 = 股價）",
            height=420,
        )
        fig.add_hline(y=65, line_dash="dash", line_color="gray", annotation_text="VCP 門檻")
        fig.add_vline(x=70, line_dash="dash", line_color="gray", annotation_text="RS 門檻")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        sector_cnt = df_f["產業"].value_counts().reset_index()
        sector_cnt.columns = ["產業", "數量"]
        fig2 = px.pie(sector_cnt, names="產業", values="數量",
                      title="符合條件個股產業分佈", height=380)
        st.plotly_chart(fig2, use_container_width=True)

# ── 完整資料表 ─────────────────────────────────────────
with st.expander("📋 完整原始資料表（可排序）"):
    # 調整顯示順序讓名稱排在前面
    cols = df_f.columns.tolist()
    if "股票標籤" in cols: cols.remove("股票標籤")
    if "評級" in cols: cols.remove("評級")
    st.dataframe(df_f[cols], use_container_width=True, hide_index=True)

# ── 免責聲明 ───────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ 免責聲明：本系統僅供技術分析參考，不構成任何投資建議。投資有風險，請自行評估並做好資金控管。")