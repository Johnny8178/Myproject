from analyzer import HongduAnalyzer

if __name__ == "__main__":
    analyzer = HongduAnalyzer()
    symbol = "600316"
    analyzer.run_focused_logic(symbol)
    analyzer.generate_simulated_thermo_phase_plot()
    analyzer.generate_simulated_vector_field_plot()
