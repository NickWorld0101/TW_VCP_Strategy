import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import time
import urllib3

# 關閉 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_all_tw_stocks():
    """透過官方 OpenAPI 獲取全台股最新代號與名稱列表"""
    print("正在獲取全台股最新清單與名稱...")
    stocks_info = {} # 用來儲存 {代號: 名稱} 的對應
    
    # 1. 上市股票 (TWSE)
    try:
        url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url_twse, timeout=10)
        for item in res.json():
            stock_id = item.get('Code', '')
            stock_name = item.get('Name', '').strip()
            if len(stock_id) == 4 and stock_id.isdigit():
                stocks_info[f"{stock_id}.TW"] = stock_name
    except Exception as e:
        print(f"上市清單獲取失敗: {e}")

    # 2. 上櫃股票 (TPEx)
    try:
        url_tpex = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        res = requests.get(url_tpex, timeout=10, verify=False) 
        for item in res.json():
            stock_id = item.get('SecuritiesCompanyCode', '')
            stock_name = item.get('CompanyName', '').strip()
            if len(stock_id) == 4 and stock_id.isdigit():
                stocks_info[f"{stock_id}.TWO"] = stock_name
    except Exception as e:
        print(f"上櫃清單獲取失敗: {e}")

    print(f"✅ 成功取得全台股共 {len(stocks_info)} 檔標的。")
    return stocks_info

def map_industry_sector(stock_id):
    """根據台股代號區間快速進行粗略產業分類"""
    id_num = int(stock_id)
    if id_num in [2330, 2454, 3034, 2379, 3661, 3443, 6415]: return "半導體"
    if id_num in [2317, 2382, 3231, 6669, 2308, 3017, 2376]: return "AI/伺服器"
    if 2300 <= id_num <= 2499 or 3000 <= id_num <= 3799 or 6100 <= id_num <= 6299: return "電子"
    if 2800 <= id_num <= 2899: return "金融"
    if id_num in [1216, 2912, 5904]: return "消費"
    if id_num <= 2299 or (9900 <= id_num <= 9999): return "傳產"
    return "其他"

def main():
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 開始執行全台股 VCP 進階量化掃描...")
    
    stocks_info = get_all_tw_stocks()
    if not stocks_info:
        print("❌ 無法取得股票清單，程式終止。")
        return

    all_stocks = list(stocks_info.keys())
    raw_data_list = []
    chunk_size = 40 

    print("開始下載歷史 K 線數據並計算型態指標...")
    for i in range(0, len(all_stocks), chunk_size):
        chunk = all_stocks[i:i+chunk_size]
        try:
            data = yf.download(chunk, period="1y", group_by='ticker', progress=False, threads=False)
            current_tickers = chunk if len(chunk) > 1 else [chunk[0]]
            
            for stock in current_tickers:
                try:
                    if len(chunk) > 1:
                        if stock not in data.columns.levels[0]: continue
                        df = data[stock].dropna(subset=['Close'])
                    else:
                        df = data.dropna(subset=['Close'])
                        
                    if df.empty or len(df) < 200: continue
                    
                    df['SMA50'] = df['Close'].rolling(50).mean()
                    df['SMA150'] = df['Close'].rolling(150).mean()
                    df['SMA200'] = df['Close'].rolling(200).mean()
                    df['Vol20MA'] = df['Volume'].rolling(20).mean()
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    if not (last['Close'] > last['SMA50'] > last['SMA150'] > last['SMA200']): continue
                    if df.iloc[-20]['SMA200'] >= last['SMA200']: continue
                    
                    high_52wk = df['High'].tail(252).max()
                    if last['Close'] < high_52wk * 0.75: continue
                    
                    dist_to_high = ((high_52wk - last['Close']) / high_52wk) * 100
                    daily_chg = ((last['Close'] - prev['Close']) / prev['Close']) * 100
                    vol_ratio = df['Volume'].tail(10).mean() / df['Volume'].tail(50).mean() if df['Volume'].tail(50).mean() > 0 else 1.0
                    
                    recent_df = df.tail(15)
                    contract_days = sum((recent_df['Volume'] < recent_df['Vol20MA']) & (recent_df['Volume'] < recent_df['Volume'].shift(1).fillna(0)))
                    
                    vcp_score = int(min(99, max(10, ((last['SMA50'] - last['SMA200']) / last['SMA200'] * 200) + (15 - dist_to_high))))
                    one_year_return = ((last['Close'] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
                    
                    pivot_price = round(df['High'].tail(20).max(), 2) 
                    stop_loss = round(last['Close'] * 0.93, 2) 
                    clean_id = stock.replace(".TW", "").replace(".TWO", "")
                    stock_name = stocks_info.get(stock, "") # 取得股票名稱
                    
                    raw_data_list.append({
                        "股票代號": clean_id,
                        "股票名稱": stock_name, # 新增欄位
                        "產業": map_industry_sector(clean_id),
                        "收盤價": round(last['Close'], 2),
                        "今日漲跌%": daily_chg,
                        "VCP強度": vcp_score,
                        "Pivot進場價": pivot_price,
                        "建議停損": stop_loss,
                        "距高點%": dist_to_high,
                        "縮量次數": int(contract_days),
                        "量比": vol_ratio,
                        "成交量(股)": int(last['Volume']),
                        "更新日期": df.index[-1].strftime("%Y-%m-%d"),
                        "_1y_ret": one_year_return 
                    })
                except Exception:
                    continue
            
            print(f"進度: {min(i+chunk_size, len(all_stocks))}/{len(all_stocks)} 檔已掃描...")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ 批次 {i} 發生異常: {e}")
            time.sleep(2)

    if len(raw_data_list) > 0:
        final_df = pd.DataFrame(raw_data_list)
        final_df['RS分數'] = final_df['_1y_ret'].rank(pct=True).apply(lambda x: int(x * 100))
        final_df.drop(columns=['_1y_ret'], inplace=True)
        final_df = final_df.sort_values(by=["VCP強度", "RS分數"], ascending=[False, False])
    else:
        final_df = pd.DataFrame(columns=[
            "股票代號", "股票名稱", "產業", "收盤價", "今日漲跌%", "RS分數", "VCP強度", 
            "Pivot進場價", "建議停損", "距高點%", "縮量次數", "量比", "成交量(股)", "更新日期"
        ])
        
    today_str = datetime.now().strftime("%Y%m%d")
    filename = f"vcp_{today_str}.csv"
    final_df.to_csv(filename, index=False)
    
    end_time = time.time()
    print(f"🎉 掃描完成！檔案已儲存為 {filename}。共篩選出 {len(final_df)} 檔強勢股。總耗時: {round((end_time - start_time)/60, 2)} 分鐘。")

if __name__ == "__main__":
    main()