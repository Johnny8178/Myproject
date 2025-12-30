import backtrader as bt
import json
import os

# 1. 扩展数据类，增加 wave_real 这一线 (line)
class MainWaveData(bt.feeds.GenericCSVData):
    lines = ('wave_real',)
    params = (
        ('datetime', 0),
        ('close', 1),
        ('high', 2),
        ('low', 3),
        ('wave_real', 4),
        ('open', -1),
        ('volume', -1),
        ('openinterest', -1),
    )

# 2. 编写利用该指标的策略
class WaveStrategy(bt.Strategy):
    def next(self):
        current_wave = self.datas[0].wave_real[0]
        current_close = self.datas[0].close[0]
        if not self.position:
            if current_close < current_wave:
                self.buy()
                print(f"{self.datetime.date(0)} 买入: 价格 {current_close:.2f} < 主力波 {current_wave:.2f}")
        elif current_close > current_wave * 1.05:
            self.sell()
            print(f"{self.datetime.date(0)} 卖出: 价格 {current_close:.2f}")

def export_to_json(strat, filename='equity_curve.json'):
    equity_values = list(strat.observers.broker.value)
    dates = [strat.datas[0].datetime.date(i).isoformat() for i in range(-len(equity_values) + 1, 1)]
    equity_data = []
    for date, value in zip(dates, equity_values):
        equity_data.append({
            "date": date,
            "value": round(value, 2)
        })
    output_path = os.path.join('output', filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(equity_data, f, indent=4)
    print(f">>> 资金曲线已导出至: {output_path}")

def run_report():
    cerebro = bt.Cerebro()
    data = MainWaveData(dataname='precomputed_wave.csv')
    cerebro.adddata(data)
    cerebro.addstrategy(WaveStrategy)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addobserver(bt.observers.Broker)
    results = cerebro.run()
    strat = results[0]
    export_to_json(strat)
    print(f"年化收益率: {strat.analyzers.returns.get_analysis()['rnorm100']:.2f}%")
    print(f"最大回撤: {strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")
    print(f"夏普比率: {strat.analyzers.sharpe.get_analysis()['sharperatio']:.2f}")
    cerebro.plot()

if __name__ == '__main__':
    run_report()
