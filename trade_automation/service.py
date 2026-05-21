from datetime import datetime
import threading
import uuid

from .config import AutomationConfig
from .executor import DesktopExecutor
from .models import OrderRequest, OrderResult
from .validator import ValidationError, validate_order, validate_runtime_readiness


class TradeAutomationService:
    def __init__(self, config: AutomationConfig | None = None, executor: DesktopExecutor | None = None):
        self.config = config or AutomationConfig.from_env()
        self.executor = executor or DesktopExecutor(self.config)
        self._lock = threading.Lock()
        self._daily_date = datetime.now().date()
        self._daily_amount = 0.0

    def _roll_daily_window(self):
        today = datetime.now().date()
        if today != self._daily_date:
            self._daily_date = today
            self._daily_amount = 0.0

    def _next_order_id(self) -> str:
        return f"ord_{uuid.uuid4().hex[:12]}"

    def execute(self, order: OrderRequest) -> OrderResult:
        order.action = str(order.action or "").strip().upper()
        order.symbol = str(order.symbol or "").strip()
        order.market = str(order.market or "SH").strip().upper() or "SH"
        order.order_id = str(order.order_id or "").strip() or self._next_order_id()

        if order.dry_run is None:
            order.dry_run = self.config.default_dry_run

        try:
            risk_flags = validate_order(order, self.config)
            amount = order.price * order.quantity
            with self._lock:
                self._roll_daily_window()
                if self._daily_amount + amount > self.config.max_daily_amount:
                    raise ValidationError(f"daily amount exceeds limit: {self.config.max_daily_amount}")
                validate_runtime_readiness(order, self.config)
                run_result = self.executor.execute_order(order)
                self._daily_amount += amount
            return OrderResult(
                ok=True,
                status="ACCEPTED",
                message=run_result["message"],
                order_id=order.order_id,
                action=order.action,
                symbol=order.symbol,
                price=order.price,
                quantity=order.quantity,
                dry_run=order.dry_run,
                submitted=run_result["submitted"],
                before_screenshot=run_result["before_screenshot"],
                after_screenshot=run_result["after_screenshot"],
                broker_status=run_result["broker_status"],
                risk_flags=risk_flags,
            )
        except ValidationError as exc:
            return OrderResult(
                ok=False,
                status="REJECTED",
                message=str(exc),
                order_id=order.order_id,
                action=order.action,
                symbol=order.symbol,
                price=order.price,
                quantity=order.quantity,
                dry_run=order.dry_run,
                broker_status="VALIDATION_FAILED",
                error_code="VALIDATION_ERROR",
            )
        except Exception as exc:
            return OrderResult(
                ok=False,
                status="FAILED",
                message="desktop automation execution failed",
                order_id=order.order_id,
                action=order.action,
                symbol=order.symbol,
                price=order.price,
                quantity=order.quantity,
                dry_run=order.dry_run,
                broker_status="EXECUTION_FAILED",
                error_code="EXECUTION_ERROR",
                exception=str(exc),
            )
