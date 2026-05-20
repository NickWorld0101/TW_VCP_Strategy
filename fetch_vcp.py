import yfinance as yf
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────
# 監控清單：上市加 .TW，上櫃加 .TWO
# 可自行擴充，這裡涵蓋半導體、AI、電子、金融等主流族群
# ─────────────────────────────────────────────
STOCK_LIST = [
    # 半導體 / AI
    "2330.TW", "2454.TW", "2379.TW", "3711.TW", "2344.TW",
    # 電子零組件
    "2317.TW", "2382.TW", "2308.TW", "2357.TW", "3231.TW",
    # 伺服器 / AI 受惠
    "3017.TW", "6669.TW", "2376.TW", "3034.TW", "4938.TW",
    # 金融
    "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2884.TW",
    # 傳產 / 其他
    "1301.TW", "1303.TW", "2002.TW", "1216.TW", "2912.TW",
]

SECTOR_MAP = {
    "2330.TW": "半導體", "2454.TW": "半導體", "2379.TW": "半導體",
    "3711.TW": "半導體", "2344.TW": "半導體",
    "2317.TW": "電子", "2382.TW": "電子", "2308.TW": "電子",
    "2357.TW": "電子", "3231.TW": "電子",
    "3017.TW": "AI/伺服器", "6669.TW": "AI/伺服器", "2376.TW": "AI/伺服器",
    "3034.TW": "AI/伺服器", "4938.TW": "AI/伺服器",
    "2881.TW": "金融", "2882.TW": "金融", "2891.TW": "金融",
    "2886.TW": "金融", "2884.TW": "金融",
    "1301.TW": "傳產", "1303.TW": "傳產", "2002.TW": "傳產",
    "1216.TW": "消費", "2912.TW": "消費",
}


def compute_rs_score(df_close_all: dict, ticker: str) -> int:
    """
    簡化版相對強弱 RS 分數（0–99）
    比較個股近 63 個交易日漲幅 vs 全清單中位數
    """
    try:
        gains = {}
        for t, close in df_close_all.items():
            if len(close) >= 63:
                gains[t] = (close.iloc[-1] - close.iloc[-63]) / close.iloc[-63]
        if ticker not in gains or len(gains) < 2:
            return 50
        sorted_gains = sorted(gains.values())
        rank = sorted(gains.keys(), key=lambda x: gains[x]).index(ticker)
        return int(rank / len(gains) * 99)
    except Exception:
        return 50


def check_vcp(df: pd.DataFrame) -> dict | None:
    """
    VCP 核心演算法：
      1. Minervini 趨勢模板（多頭排列 + 200MA 向上）
      2. 近 52 週高點 25% 以內
      3. 成交量縮量（近 10 日量 < 近 50 日均量 * 0.85）
      4. 計算波動收縮次數、建議進場 Pivot、停損位
    """
    if len(df) < 200:
        return None

    df = df.copy()
    df["SMA50"]  = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["VolMA20"] = df["Volume"].rolling(20).mean()
    df["VolMA50"] = df["Volume"].rolling(50).mean()

    last = df.iloc[-1]

    # ── 趨勢模板 ──
    if not (last["Close"] > last["SMA50"] > last["SMA150"] > last["SMA200"]):
        return None
    if df.iloc[-20]["SMA200"] >= last["SMA200"]:          # 200MA 須向上
        return None

    # ── 距 52 週高點 ──
    high_52 = df["High"].tail(252).max()
    from_high = (last["Close"] - high_52) / high_52 * 100
    if from_high < -25:
        return None

    # ── 縮量條件 ──
    recent_vol  = df["Volume"].tail(10).mean()
    mid_vol     = float(last["VolMA50"]) if not pd.isna(last["VolMA50"]) else recent_vol
    if recent_vol > mid_vol * 0.9:                        # 量未縮則略過
        return None
    vol_ratio = round(recent_vol / mid_vol, 2)

    # ── 波動收縮次數（VCP 核心）──
    # 分析近 60 日，每 10 日為一段，計算高低振幅是否持續縮小
    contractions = 0
    prev_range = None
    for i in range(5, 0, -1):
        segment = df.iloc[-i*10 : -(i-1)*10] if i > 1 else df.iloc[-10:]
        cur_range = (segment["High"].max() - segment["Low"].min()) / segment["Close"].mean()
        if prev_range is not None and cur_range < prev_range:
            contractions += 1
        prev_range = cur_range

    if contractions < 2:
        return None

    # ── Pivot Point（近期高點 + 一點突破）──
    pivot = round(df["High"].tail(20).max() * 1.005, 2)
    stop  = round(last["SMA50"] * 0.97, 2)

    return {
        "收盤價":       round(float(last["Close"]), 2),
        "今日漲跌%":   round((float(last["Close"]) - float(df.iloc[-2]["Close"])) / float(df.iloc[-2]["Close"]) * 100, 2),
        "距高點%":     round(from_high, 1),
        "縮量次數":    contractions,
        "量比":        vol_ratio,
        "Pivot進場價": pivot,
        "建議停損":    stop,
        "更新日期":    df.index[-1].strftime("%Y-%m-%d"),
    }


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 開始台股 VCP 掃描（共 {len(STOCK_LIST)} 檔）")

    # 批次下載所有股票
    raw = yf.download(
        STOCK_LIST, period="1y", group_by="ticker",
        auto_adjust=True, progress=False, threads=True
    )

    # 建立各股收盤價字典，供 RS 計算
    close_dict: dict[str, pd.Series] = {}
    for ticker in STOCK_LIST:
        try:
            close_dict[ticker] = raw[ticker]["Close"].dropna()
        except Exception:
            pass

    results = []
    for ticker in STOCK_LIST:
        try:
            df = raw[ticker].dropna()
        except Exception:
            continue

        info = check_vcp(df)
        if info is None:
            continue

        code = ticker.replace(".TW", "").replace(".TWO", "")
        rs   = compute_rs_score(close_dict, ticker)

        # VCP 強度分（綜合 RS + 縮量 + 距高點）
        vcp_score = min(99, int(rs * 0.5 + contractions_score(info["縮量次數"]) + distance_score(info["距高點%"])))

        results.append({
            "股票代號":    code,
            "產業":       SECTOR_MAP.get(ticker, "其他"),
            **info,
            "RS分數":     rs,
            "VCP強度":    vcp_score,
        })
        print(f"  ✓ {code}  RS={rs}  VCP={vcp_score}  縮量={info['縮量次數']}次")

    # 依 VCP 強度排序
    df_out = pd.DataFrame(results).sort_values("VCP強度", ascending=False)
    df_out.to_csv("vcp_today.csv", index=False, encoding="utf-8-sig")
    print(f"\n掃描完成！共找到 {len(results)} 檔 VCP 個股 → 已寫入 vcp_today.csv")


def contractions_score(n: int) -> int:
    return min(30, n * 10)

def distance_score(pct: float) -> int:
    # 越接近高點分數越高（-5% → 20分，-25% → 0分）
    return max(0, int((25 + pct) / 25 * 20))


if __name__ == "__main__":
    main()
