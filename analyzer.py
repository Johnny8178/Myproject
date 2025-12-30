import akshare as ak
import pandas as pd
import numpy as np
from scipy.fft import fft
import duckdb
import matplotlib.pyplot as plt
import os
from interface import AnalyzerInterface

class HongduAnalyzer(AnalyzerInterface):
    def __init__(self, db_path='hongdu_analysis.db'):
        self.con = duckdb.connect(db_path)
        if not os.path.exists('output'):
            os.makedirs('output')
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

    def sync_data(self, symbol: str):
        print(f"正在同步 {symbol} 的多维数据...")
        df_hfq = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20230101", adjust="hfq")
        df_real = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20230101", adjust="")
        if df_hfq.empty or df_real.empty:
            print("数据同步失败")
            return
        df_hfq = df_hfq.rename(columns={"日期": "trade_date", "收盘": "close_hfq", "最高": "high_hfq", "最低": "low_hfq"})
        df_hfq['trade_date'] = pd.to_datetime(df_hfq['trade_date']).dt.date
        df_real = df_real.rename(columns={"日期": "trade_date", "收盘": "close_real"})
        df_real['trade_date'] = pd.to_datetime(df_real['trade_date']).dt.date
        df_merged = pd.merge(df_hfq, df_real[['trade_date', 'close_real']], on='trade_date')
        self.con.execute("CREATE OR REPLACE TABLE hongdu_stock AS SELECT * FROM df_merged")
        print(f"DEBUG: 数据同步完成，当前最大日期: {df_merged['trade_date'].max()}")

    def _get_hfq_fft_params(self, data):
        prices = data['close_hfq'].values
        N = len(prices)
        yf = fft(prices)
        xf = np.fft.fftfreq(N, 1)[:N//2]
        amps = 2.0/N * np.abs(yf[0:N//2])
        phases = np.arctan2(np.imag(yf[0:N//2]), np.real(yf[0:N//2]))
        eligible_idx = np.where(xf > 0.01)[0]
        if len(eligible_idx) == 0: return None
        main_idx = eligible_idx[np.argmax(amps[eligible_idx])]
        f, a, p = xf[main_idx], amps[main_idx], phases[main_idx]
        mean_p = prices.mean()
        high_limit = data['high_hfq'].max()
        low_limit = data['low_hfq'].min()
        a_final = min(a, high_limit - mean_p, mean_p - low_limit)
        return {"f": f, "a": a_final, "p": p, "mean": mean_p, "N": N}

    def run_focused_logic(self, symbol: str):
        self.sync_data(symbol)
        data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        params = self._get_hfq_fft_params(data)
        if not params: return
        t = np.arange(params['N'])
        wave_hfq = params['mean'] + params['a'] * np.sin(2 * np.pi * params['f'] * t + params['p'])
        ratio = data['close_real'].iloc[-1] / data['close_hfq'].iloc[-1]
        data['main_wave_real'] = wave_hfq * ratio
        cutoff = data['trade_date'].max() - pd.Timedelta(days=90)
        plot_df = data[data['trade_date'] >= cutoff]
        plt.figure(figsize=(15, 7))
        plt.plot(plot_df['trade_date'], plot_df['close_real'], label='真实价格', color='blue', alpha=0.6)
        plt.plot(plot_df['trade_date'], plot_df['main_wave_real'], label='还原主力波', color='red', linewidth=3)
        plt.ylabel("真实股价 (元)")
        plt.title(f"{symbol} 深度波形观察 (真实价格空间) - {data['trade_date'].max()}")
        plt.legend()
        img_path = f"output/{symbol}_current_analysis.png" # 固定文件名方便前端读取
        plt.savefig(img_path)
        plt.close()
        print(f"[Focused Logic] 图像已保存: {img_path}")

    def run_term_wave_logic(self, symbol: str):
        self.run_focused_logic(symbol)

    def run_resonance_logic(self, symbol: str):
        self.sync_data(symbol)
        data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        params = self._get_hfq_fft_params(data)
        if not params: return
        ratio = data['close_real'].iloc[-1] / data['close_hfq'].iloc[-1]
        t_last = params['N'] - 1
        wave_now = (params['mean'] + params['a'] * np.sin(2 * np.pi * params['f'] * t_last + params['p'])) * ratio
        wave_prev = (params['mean'] + params['a'] * np.sin(2 * np.pi * params['f'] * (t_last-1) + params['p'])) * ratio
        df_min = ak.stock_zh_a_hist_min_em(symbol=symbol, period='1', adjust="")
        if df_min.empty: return
        M = len(df_min)
        today_wave_interp = np.interp(np.linspace(0, 1, M), [0, 1], [wave_prev, wave_now])
        plt.figure(figsize=(15, 7))
        plt.plot(range(M), df_min['收盘'], label='分时真实价', color='blue', alpha=0.7)
        plt.plot(range(M), today_wave_interp, label='今日主力中轴(还原)', color='red', linewidth=3)
        plt.ylabel("真实价格 (元)")
        plt.title(f"{symbol} 价格共振图 - 纵轴已还原至真实股价")
        plt.legend()
        img_path = f"output/{symbol}_current_analysis.png" # 固定文件名方便前端读取
        plt.savefig(img_path)
        plt.close()
        print(f"[Resonance Logic] 图像已保存: {img_path}")
        print(f"共振图已生成。当前还原因子: {ratio:.4f}")
