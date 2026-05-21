from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OrderRequest:
    action: str
    symbol: str
    price: float
    quantity: int
    market: str = "SH"
    order_id: str = ""
    dry_run: bool = True
    account: str = ""
    note: str = ""


@dataclass
class OrderResult:
    ok: bool
    status: str
    message: str
    order_id: str
    action: str
    symbol: str
    price: float
    quantity: int
    dry_run: bool
    submitted: bool = False
    before_screenshot: str = ""
    after_screenshot: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    broker_status: str = ""
    error_code: str = ""
    risk_flags: list[str] = field(default_factory=list)
    exception: Optional[str] = None
