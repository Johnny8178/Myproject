import backtrader as bt
from analyzer import HongduAnalyzer
import pandas as pd

# --- 1. 定义策略类 ---
class MainWaveStrategy(bt.Strategy):
    def __init__(self):
        self.analyzer = HongduAnalyzer()
        self.dataclose = self.datas[0].close
        self.order = None

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        symbol = "600316"
        main_wave_price = self.get_wave_price(current_date)
        if not self.position:
            if self.dataclose[0] < main_wave_price:
                self.log(f'BUY CREATE, 价格: {self.dataclose[0]:.2f}, 主力波: {main_wave_price:.2f}')
                self.buy()
        elif self.dataclose[0] > main_wave_price * 1.05:
            self.log(f'SELL CREATE, 价格: {self.dataclose[0]:.2f}')
            self.sell()

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def get_wave_price(self, date):
        # 这里集成你的 FFT 逻辑，返回该日期对应的主力波数值
        # 注意：回测时严禁使用未来数据
        return 28.5  # 示例数值

# --- 2. 启动回测引擎 ---
def run_backtest():
    cerebro = bt.Cerebro()
    data = bt.feeds.GenericCSVData(
        dataname='your_stock_data.csv',
        dtformat='%Y-%m-%d',
        datetime=0, high=2, low=3, open=1, close=4, volume=5
    )
    cerebro.adddata(data)
    cerebro.addstrategy(MainWaveStrategy)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0003)
    print('期初资金: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('期末资金: %.2f' % cerebro.broker.getvalue())
    cerebro.plot(style='candlestick')

if __name__ == '__main__':
    run_backtest()
