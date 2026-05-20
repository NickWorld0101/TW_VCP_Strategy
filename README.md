# ⚡ 台股 VCP 動能選股儀表板

> 每個交易日自動掃描台股，篩選符合 **Minervini 趨勢模板 + VCP 波動收縮型態**的潛力個股。

🌐 **線上示範**：部署後網址格式為 `https://你的名字-tw-vcp.streamlit.app`

---

## 📁 專案結構

```
taiwan-vcp-monitor/
├── app.py                          # Streamlit 網頁介面
├── fetch_vcp.py                    # VCP 掃描演算法
├── requirements.txt                # Python 相依套件
├── vcp_today.csv                   # 每日自動產生的結果（勿手動修改）
└── .github/
    └── workflows/
        └── update_data.yml         # GitHub Actions 每日排程
```

---

## 🚀 五步驟上線教學

### 步驟 1：上傳到 GitHub

1. 前往 [github.com](https://github.com) 註冊或登入
2. 點右上角 **+** → **New repository**
3. 名稱填 `taiwan-vcp-monitor`，設為 **Public**
4. 把這個資料夾所有檔案（含 `.github/` 資料夾）上傳 → **Commit changes**

### 步驟 2：手動觸發第一次掃描

1. 在你的 GitHub 專案頁，點上方 **Actions** 頁籤
2. 左側找到 **Daily VCP Stock Screener**
3. 點右側 **Run workflow** → **Run workflow**
4. 等約 1–2 分鐘，專案首頁會出現 `vcp_today.csv`

### 步驟 3：登入 Streamlit Cloud

1. 前往 [share.streamlit.io](https://share.streamlit.io)
2. 點 **Continue with GitHub** 登入並授權

### 步驟 4：部署網頁

1. 點右上角 **New app**
2. 填寫：
   - **Repository**：選你的 `taiwan-vcp-monitor`
   - **Branch**：`main`
   - **Main file path**：`app.py`
   - **App URL**：自訂（例如 `my-tw-vcp`）
3. 點 **Deploy!**

### 步驟 5：完成！

🎉 約 30 秒後網站上線，網址可直接分享給任何人！
從此每個交易日下午 4 點，GitHub 自動幫你更新資料。

---

## ⚙️ 自訂股票清單

編輯 `fetch_vcp.py` 的 `STOCK_LIST`：
- 上市股票代號後面加 `.TW`（例如 `2330.TW`）
- 上櫃股票代號後面加 `.TWO`（例如 `6271.TWO`）

---

## 📊 VCP 篩選邏輯

| 條件 | 說明 |
|------|------|
| 趨勢模板 | 股價 > 50MA > 150MA > 200MA |
| 200MA 向上 | 20 天前 200MA < 今日 200MA |
| 距高點 | 距 52 週最高點 25% 以內 |
| 縮量 | 近 10 日均量 < 50 日均量 × 90% |
| 波動收縮 | 至少 2 次振幅縮小（VCP 核心）|
| RS 分數 | 相對強弱排名（0–99）|

---

## 💰 費用

| 項目 | 費用 |
|------|------|
| GitHub 儲存 + Actions | **免費** |
| Streamlit Community Cloud | **免費** |
| Yahoo Finance 資料 | **免費** |
| **總計** | **$0** |

---

⚠️ **免責聲明**：本系統僅供技術分析參考，不構成任何投資建議。投資有風險，請自行評估。
