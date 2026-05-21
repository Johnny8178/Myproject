# Trade Automation

## Current skeleton

- `trade_automation/config.py`
  Loads environment variables, safety switches, and desktop coordinates.
- `trade_automation/validator.py`
  Validates action, symbol, price, quantity, and trading-hour risk flags.
- `trade_automation/executor.py`
  Contains the desktop execution layer for `pyautogui`.
- `trade_automation/service.py`
  Orchestrates validation, daily limit checks, and execution.
- `run_trade_demo.py`
  Small demo entry point for the first end-to-end test.

## Safe defaults

- `AUTO_TRADE_DEFAULT_DRY_RUN=true`
- `AUTO_TRADE_SUBMIT_ENABLED=false`

These defaults are intended to keep the first iteration from sending a real order.

## Important environment variables

- `BROKER_PASSWORD`
- `BROKER_LOGIN_PASSWORD_COORD`
- `BROKER_LOGIN_BUTTON_COORD`
- `BROKER_BUY_CODE_COORD`
- `BROKER_BUY_PRICE_COORD`
- `BROKER_BUY_QTY_COORD`
- `BROKER_BUY_SUBMIT_COORD`
- `BROKER_SELL_CODE_COORD`
- `BROKER_SELL_PRICE_COORD`
- `BROKER_SELL_QTY_COORD`
- `BROKER_SELL_SUBMIT_COORD`

## Next steps

1. Install `pyautogui`.
2. Add a coordinate capture helper.
3. Add a login flow.
4. Connect this skeleton to a local API or desktop control panel.

## Current login coordinates

- `BROKER_LOGIN_PASSWORD_COORD=529,339`
- `BROKER_LOGIN_BUTTON_COORD=790,263`
