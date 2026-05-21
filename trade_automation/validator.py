from datetime import datetime
import re

from .config import AutomationConfig
from .models import OrderRequest


SYMBOL_RE = re.compile(r"^\d{6}$")
VALID_ACTIONS = {"BUY", "SELL"}


class ValidationError(ValueError):
    pass


def is_trading_time(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    minute = now.hour * 60 + now.minute
    morning = 9 * 60 + 30 <= minute <= 11 * 60 + 30
    afternoon = 13 * 60 <= minute <= 14 * 60 + 57
    return morning or afternoon


def validate_order(order: OrderRequest, config: AutomationConfig) -> list[str]:
    risk_flags: list[str] = []
    action = str(order.action or "").strip().upper()
    if action not in VALID_ACTIONS:
        raise ValidationError("action must be BUY or SELL")
    if not SYMBOL_RE.match(str(order.symbol or "").strip()):
        raise ValidationError("symbol must be a 6-digit code")
    if float(order.price or 0) <= 0:
        raise ValidationError("price must be greater than 0")
    if int(order.quantity or 0) <= 0:
        raise ValidationError("quantity must be greater than 0")
    if int(order.quantity) % 100 != 0:
        risk_flags.append("quantity is not a 100-share lot")
    amount = float(order.price) * int(order.quantity)
    if amount > config.max_order_amount:
        raise ValidationError(f"order amount exceeds limit: {config.max_order_amount}")
    if not config.allow_non_trading_time and not is_trading_time(datetime.now()):
        risk_flags.append("outside trading hours")
    if order.dry_run:
        risk_flags.append("dry run enabled")
    if not config.submit_enabled:
        risk_flags.append("submit disabled by config")
    return risk_flags


def validate_runtime_readiness(order: OrderRequest, config: AutomationConfig) -> None:
    action = str(order.action).strip().upper()
    if action == "BUY":
        required = {
            "BROKER_BUY_CODE_COORD": config.buy_code_coord,
            "BROKER_BUY_PRICE_COORD": config.buy_price_coord,
            "BROKER_BUY_QTY_COORD": config.buy_qty_coord,
            "BROKER_BUY_SUBMIT_COORD": config.buy_submit_coord,
        }
    else:
        required = {
            "BROKER_SELL_CODE_COORD": config.sell_code_coord,
            "BROKER_SELL_PRICE_COORD": config.sell_price_coord,
            "BROKER_SELL_QTY_COORD": config.sell_qty_coord,
            "BROKER_SELL_SUBMIT_COORD": config.sell_submit_coord,
        }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValidationError(f"missing coordinates: {', '.join(missing)}")
