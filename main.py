from analyzer import HongduAnalyzer

if __name__ == "__main__":
    analyzer = HongduAnalyzer()
    symbol = "600316"
    analyzer.sync_data(symbol)
    analyzer.run_focused_logic(symbol)
