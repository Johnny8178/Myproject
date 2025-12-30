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

    def sync_data(self, symbol):
        print(f"正在同步 {symbol} 数据...")
        df_new = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20230101", adjust="hfq")
        if df_new.empty: return
        df_new = df_new.rename(columns={"日期": "trade_date", "收盘": "close_price", "最高": "high_price", "最低": "low_price"})
        df_new['trade_date'] = pd.to_datetime(df_new['trade_date']).dt.date
        self.con.execute("CREATE OR REPLACE TABLE hongdu_stock AS SELECT * FROM df_new")

    def _get_fft_wave(self, data, prices):
        """通用FFT核心算法逻辑 (内部复用)"""
        high_limit, low_limit = data['high_price'].max(), data['low_price'].min()
        mean_p = prices.mean()
        N = len(prices)
        yf = fft(prices)
        xf = np.fft.fftfreq(N, 1)[:N//2]
        amps = 2.0/N * np.abs(yf[0:N//2])
        phases = np.arctan2(np.imag(yf[0:N//2]), np.real(yf[0:N//2]))
        eligible_idx = np.where(xf > 0.01)[0]
        if len(eligible_idx) == 0: return None
        main_idx = eligible_idx[np.argmax(amps[eligible_idx])]
        f, a, p = xf[main_idx], amps[main_idx], phases[main_idx]
        # 物理约束裁剪
        a_final = min(a, high_limit - mean_p, mean_p - low_limit)
        return mean_p + a_final * np.sin(2 * np.pi * f * np.arange(N) + p)

    def run_focused_logic(self, symbol):
        """逻辑1：3个月局部深度观察"""
        self.sync_data(symbol)
        data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        wave = self._get_fft_wave(data, data['close_price'].values)
        if wave is not None:
            data['main_wave'] = wave
            self._save_plot(data, symbol, "focused")

    def run_term_wave_logic(self, symbol):
        """逻辑2：合成3个月期限波 (基于3个月数据重新拟合)"""
        self.sync_data(symbol)
        all_data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        # 截取最近3个月
        cutoff = all_data['trade_date'].max() - pd.Timedelta(days=90)
        term_data = all_data[all_data['trade_date'] >= cutoff].copy()
        # 针对这3个月的数据进行独立FFT合成
        wave = self._get_fft_wave(term_data, term_data['close_price'].values)
        if wave is not None:
            term_data['main_wave'] = wave
            self._save_plot(term_data, symbol, "term_wave")

    def _save_plot(self, data, symbol, suffix):
        plt.rcParams['font.sans-serif'] = ['SimHei']; plt.rcParams['axes.unicode_minus'] = False
        plt.figure(figsize=(15, 7))
        # 绘图截取展示范围
        cutoff = data['trade_date'].max() - pd.Timedelta(days=90)
        plot_df = data[data['trade_date'] >= cutoff]
        plt.plot(plot_df['trade_date'], plot_df['close_price'], label='价格', color='blue', alpha=0.6)
        plt.plot(plot_df['trade_date'], plot_df['main_wave'], label='主力波', color='red', linewidth=3)
        img_path = f"output/{symbol}_{suffix}.png"
        plt.savefig(img_path)
        plt.close()
        print(f"[{suffix}] 图像已保存: {img_path}")
