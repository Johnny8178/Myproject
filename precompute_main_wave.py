import pandas as pd
from analyzer import HongduAnalyzer

def precompute_main_wave(symbol="600316"):
    analyzer = HongduAnalyzer()
    analyzer.sync_data(symbol)
    df = analyzer.con.execute("SELECT * FROM hongdu_stock ORDER BY trade_date").fetchdf()
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['wave_real'] = 0.0
    print("开始预计算主力波数值，请稍候...")
    for i in range(60, len(df)):
        sub_data = df.iloc[:i+1].copy()
        params = analyzer._get_hfq_fft_params(sub_data)
        if params:
            t_last = params['N'] - 1
            wave_hfq = params['mean'] + params['a'] * np.sin(2 * np.pi * params['f'] * t_last + params['p'])
            ratio = df.iloc[i]['close_real'] / df.iloc[i]['close_hfq']
            df.at[i, 'wave_real'] = wave_hfq * ratio
        if i % 100 == 0:
            print(f"进度: {i}/{len(df)}")
    output_df = df.iloc[60:].rename(columns={'trade_date': 'datetime', 'close_real': 'close'})
    output_df = output_df[['datetime', 'close', 'high_hfq', 'low_hfq', 'wave_real']]
    output_df.to_csv('precomputed_wave.csv', index=False)
    print("预计算完成，文件已保存为 precomputed_wave.csv")

if __name__ == '__main__':
    precompute_main_wave()
