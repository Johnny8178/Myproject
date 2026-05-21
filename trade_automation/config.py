from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    value = str(os.getenv(name, str(default))).strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _parse_coord(raw: str) -> Optional[tuple[int, int]]:
    text = str(raw or "").strip()
    if not text:
        return None
    parts = text.split(",")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except (TypeError, ValueError):
        return None


@dataclass
class AutomationConfig:
    api_key: str
    broker_password: str
    submit_enabled: bool
    default_dry_run: bool
    allow_non_trading_time: bool
    action_delay_seconds: float
    max_order_amount: float
    max_daily_amount: float
    min_symbol_interval_seconds: int
    screenshot_dir: str
    login_password_coord: Optional[tuple[int, int]]
    login_button_coord: Optional[tuple[int, int]]
    buy_code_coord: Optional[tuple[int, int]]
    buy_price_coord: Optional[tuple[int, int]]
    buy_qty_coord: Optional[tuple[int, int]]
    buy_submit_coord: Optional[tuple[int, int]]
    sell_code_coord: Optional[tuple[int, int]]
    sell_price_coord: Optional[tuple[int, int]]
    sell_qty_coord: Optional[tuple[int, int]]
    sell_submit_coord: Optional[tuple[int, int]]

    @classmethod
    def from_env(cls) -> "AutomationConfig":
        screenshot_dir = Path(os.getenv("AUTO_TRADE_SCREENSHOT_DIR", "output/auto_trade")).resolve()
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            api_key=str(os.getenv("AUTO_TRADE_API_KEY", "")).strip(),
            broker_password=str(os.getenv("BROKER_PASSWORD", "")).strip(),
            submit_enabled=_env_bool("AUTO_TRADE_SUBMIT_ENABLED", False),
            default_dry_run=_env_bool("AUTO_TRADE_DEFAULT_DRY_RUN", True),
            allow_non_trading_time=_env_bool("AUTO_TRADE_ALLOW_NON_TRADING_TIME", False),
            action_delay_seconds=max(0.05, _env_float("AUTO_TRADE_ACTION_DELAY_SECONDS", 0.3)),
            max_order_amount=max(1000.0, _env_float("AUTO_TRADE_MAX_ORDER_AMOUNT", 100000.0)),
            max_daily_amount=max(1000.0, _env_float("AUTO_TRADE_MAX_DAILY_AMOUNT", 300000.0)),
            min_symbol_interval_seconds=max(1, _env_int("AUTO_TRADE_MIN_SYMBOL_INTERVAL_SECONDS", 20)),
            screenshot_dir=str(screenshot_dir),
            login_password_coord=_parse_coord(os.getenv("BROKER_LOGIN_PASSWORD_COORD", "")),
            login_button_coord=_parse_coord(os.getenv("BROKER_LOGIN_BUTTON_COORD", "")),
            buy_code_coord=_parse_coord(os.getenv("BROKER_BUY_CODE_COORD", "")),
            buy_price_coord=_parse_coord(os.getenv("BROKER_BUY_PRICE_COORD", "")),
            buy_qty_coord=_parse_coord(os.getenv("BROKER_BUY_QTY_COORD", "")),
            buy_submit_coord=_parse_coord(os.getenv("BROKER_BUY_SUBMIT_COORD", "")),
            sell_code_coord=_parse_coord(os.getenv("BROKER_SELL_CODE_COORD", "")),
            sell_price_coord=_parse_coord(os.getenv("BROKER_SELL_PRICE_COORD", "")),
            sell_qty_coord=_parse_coord(os.getenv("BROKER_SELL_QTY_COORD", "")),
            sell_submit_coord=_parse_coord(os.getenv("BROKER_SELL_SUBMIT_COORD", "")),
        )
