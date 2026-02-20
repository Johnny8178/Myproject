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

    def _compute_wave_metrics_from_data(self, data):
        params = self._get_hfq_fft_params(data)
        if not params or data.empty:
            return None
        t = np.arange(params['N'])
        wave_hfq = params['mean'] + params['a'] * np.sin(2 * np.pi * params['f'] * t + params['p'])
        ratio = data['close_real'].iloc[-1] / data['close_hfq'].iloc[-1]
        main_wave_real = wave_hfq * ratio

        residual = data['close_real'].values - main_wave_real
        q90 = float(np.quantile(residual, 0.90))
        q10 = float(np.quantile(residual, 0.10))

        current_price = float(data['close_real'].iloc[-1])
        current_wave = float(main_wave_real[-1])
        upper_bound = current_wave + q90
        lower_bound = current_wave + q10
        deviation_pct = ((current_price - current_wave) / current_wave) * 100 if current_wave else 0.0

        returns = data['close_real'].pct_change().dropna()
        volatility_pct = float(returns.tail(60).std() * 100) if not returns.empty else 0.0

        return {
            "current_price": current_price,
            "current_wave": current_wave,
            "upper_bound": float(upper_bound),
            "lower_bound": float(lower_bound),
            "deviation_pct": float(deviation_pct),
            "volatility_pct": volatility_pct,
            "latest_trade_date": str(data['trade_date'].iloc[-1])
        }

    def get_wave_metrics(self, symbol: str, refresh: bool = True):
        if refresh:
            self.sync_data(symbol)
        data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        return self._compute_wave_metrics_from_data(data)

    def get_phase_position(self, symbol: str, refresh: bool = False):
        if refresh:
            self.sync_data(symbol)
        data = self.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
        metrics = self._compute_wave_metrics_from_data(data)
        if not metrics or len(data) < 2:
            return None

        close = data["close_real"].astype(float)
        x = float(metrics["deviation_pct"])

        lookback = 5 if len(close) > 5 else 1
        prev_price = float(close.iloc[-1 - lookback])
        curr_price = float(close.iloc[-1])
        y = ((curr_price - prev_price) / prev_price) * 100 if prev_price else 0.0

        if x >= 0 and y >= 0:
            quadrant = "Q1_overheat_uptrend"
            quadrant_name = "高位加速区"
            interpretation = "price above wave and still accelerating upward"
            meaning = "价格在主力波上方且动量继续增强，短期延续强势但回撤风险同步抬升。"
            risk_level = "high"
            grid_hint = "减少追涨买入，抬高卖出网格密度，优先锁定利润。"
        elif x < 0 and y >= 0:
            quadrant = "Q2_rebound_zone"
            quadrant_name = "低位修复区"
            interpretation = "price below wave but momentum is recovering"
            meaning = "价格仍在主力波下方，但动量转正，常见于下跌后修复反弹阶段。"
            risk_level = "medium"
            grid_hint = "以分批回补为主，买入网格可略密，卖出网格保持常规间距。"
        elif x < 0 and y < 0:
            quadrant = "Q3_weak_downtrend"
            quadrant_name = "低位走弱区"
            interpretation = "price below wave and momentum still weakening"
            meaning = "价格和动量都偏弱，趋势惯性仍向下，抄底成功率受限。"
            risk_level = "high"
            grid_hint = "放宽网格间距并缩小单笔股数，优先保留现金和风险预算。"
        else:
            quadrant = "Q4_mean_reversion_watch"
            quadrant_name = "高位回落观察区"
            interpretation = "price above wave but momentum is cooling"
            meaning = "价格高于主力波但动量转弱，常见于冲高后回归过程。"
            risk_level = "medium_high"
            grid_hint = "减少新增买网格，提升卖网格权重，关注回归中轴后的再平衡。"

        return {
            "x_deviation_pct": round(x, 3),
            "y_momentum_pct": round(float(y), 3),
            "quadrant": quadrant,
            "quadrant_name": quadrant_name,
            "interpretation": interpretation,
            "meaning": meaning,
            "risk_level": risk_level,
            "grid_hint": grid_hint,
        }

    def generate_simulated_thermo_phase_plot(self, output_path: str = "output/simulated_thermo_phase.png"):
        T, X = 240, 180
        t = np.linspace(0, 12, T)
        x = np.linspace(-3.5, 3.5, X)
        TT, XX = np.meshgrid(t, x)

        volume_driver = 1.0 + 0.35 * np.sin(0.9 * t) + 0.18 * np.sin(2.1 * t + 0.7)
        volume_grid = np.tile(volume_driver, (X, 1))

        field = (
            0.9 * np.exp(-((XX - 0.9 * np.sin(0.6 * TT)) ** 2) / (0.45 + 0.2 * np.cos(0.3 * TT) ** 2))
            + 0.55 * np.exp(-((XX + 1.1 * np.cos(0.5 * TT + 0.8)) ** 2) / (0.9 + 0.25 * np.sin(0.4 * TT) ** 2))
        )
        field = field * (0.85 + 0.35 * volume_grid)

        for _ in range(14):
            field[1:-1, :] = 0.82 * field[1:-1, :] + 0.09 * field[:-2, :] + 0.09 * field[2:, :]

        field = (field - field.min()) / (field.max() - field.min() + 1e-12)

        fig, ax = plt.subplots(figsize=(11, 5.8), dpi=150)
        image = ax.imshow(
            field,
            origin='lower',
            aspect='auto',
            extent=[t.min(), t.max(), x.min(), x.max()],
            cmap='inferno'
        )
        ax.set_title('Simulated Thermodynamic-Style Phase Field: u(x,t)')
        ax.set_xlabel('time t')
        ax.set_ylabel('price-axis x')
        colorbar = fig.colorbar(image, ax=ax)
        colorbar.set_label('field intensity u')

        trajectory = 0.35 * np.sin(0.65 * t) + 0.55 * np.sin(0.18 * t + 1.1)
        ax.plot(t, trajectory, color='#5dd6ff', linewidth=2.2, alpha=0.95, label='state trajectory')
        ax.legend(loc='upper right')

        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        print(f"[Simulated Thermo] plot saved: {output_path}")

    def generate_simulated_vector_field_plot(self, output_path: str = "output/simulated_vector_field.png"):
        x = np.linspace(-3.0, 3.0, 31)
        y = np.linspace(-3.0, 3.0, 31)
        X, Y = np.meshgrid(x, y)

        U = Y - 0.28 * X * (X ** 2 + Y ** 2 - 2.2)
        V = -X - 0.28 * Y * (X ** 2 + Y ** 2 - 2.2)
        speed = np.sqrt(U ** 2 + V ** 2)

        fig, ax = plt.subplots(figsize=(7.5, 7), dpi=160)
        quiver = ax.quiver(X, Y, U, V, speed, cmap='viridis', scale=55, width=0.0032)
        colorbar = fig.colorbar(quiver, ax=ax)
        colorbar.set_label('vector magnitude')
        ax.streamplot(x, y, U, V, color='black', density=1.1, linewidth=0.6, arrowsize=0.8)

        ax.set_title('Simulated Phase-Space Vector Field')
        ax.set_xlabel('state x (e.g., normalized price)')
        ax.set_ylabel('state y (e.g., normalized momentum)')
        ax.set_aspect('equal', adjustable='box')
        ax.grid(alpha=0.2)

        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        print(f"[Simulated Vector] plot saved: {output_path}")

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
