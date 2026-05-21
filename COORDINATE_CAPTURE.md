# Coordinate Capture

Run:

```powershell
python capture_trade_coordinates.py
```

Instructions:

- Move the mouse to the requested broker control.
- Press `F8` to capture the current mouse position.
- Press `F9` to skip the current field.
- Press `Esc` to stop early.

The script prints ready-to-use environment variable commands for both:

- PowerShell
- CMD

Fields captured:

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

## Login-only test

After you capture the first two login coordinates, you can run:

```powershell
$env:BROKER_PASSWORD="your_trade_password"
python run_login_demo.py
```

The current saved login coordinates are:

```text
BROKER_LOGIN_PASSWORD_COORD=529,339
BROKER_LOGIN_BUTTON_COORD=790,263
```
