from datetime import datetime
import os
import time

from .config import AutomationConfig
from .models import OrderRequest


class DesktopExecutor:
    def __init__(self, config: AutomationConfig):
        self.config = config
        self._pyautogui = None

    def _load_pyautogui(self):
        if self._pyautogui is not None:
            return self._pyautogui
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("pyautogui is not installed. Run: pip install pyautogui") from exc
        pyautogui.PAUSE = self.config.action_delay_seconds
        pyautogui.FAILSAFE = True
        self._pyautogui = pyautogui
        return pyautogui

    def _sleep(self):
        time.sleep(self.config.action_delay_seconds)

    def _click_and_fill(self, coord: tuple[int, int], text: str):
        gui = self._load_pyautogui()
        gui.click(coord[0], coord[1])
        gui.hotkey("ctrl", "a")
        gui.press("backspace")
        gui.write(str(text), interval=0.01)
        self._sleep()

    def _click(self, coord: tuple[int, int]):
        gui = self._load_pyautogui()
        gui.click(coord[0], coord[1])
        self._sleep()

    def _press_trade_panel_hotkey(self, action: str):
        gui = self._load_pyautogui()
        gui.press("f1" if action == "BUY" else "f2")
        self._sleep()

    def _take_screenshot(self, suffix: str) -> str:
        gui = self._load_pyautogui()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}.png"
        path = os.path.join(self.config.screenshot_dir, filename)
        gui.screenshot(path)
        return path

    def execute_order(self, order: OrderRequest) -> dict:
        action = order.action.upper()
        self._press_trade_panel_hotkey(action)
        before = self._take_screenshot(f"{action}_before")

        if action == "BUY":
            self._click_and_fill(self.config.buy_code_coord, order.symbol)
            self._click_and_fill(self.config.buy_price_coord, f"{order.price:.3f}".rstrip("0").rstrip("."))
            self._click_and_fill(self.config.buy_qty_coord, str(order.quantity))
            submit_coord = self.config.buy_submit_coord
        else:
            self._click_and_fill(self.config.sell_code_coord, order.symbol)
            self._click_and_fill(self.config.sell_price_coord, f"{order.price:.3f}".rstrip("0").rstrip("."))
            self._click_and_fill(self.config.sell_qty_coord, str(order.quantity))
            submit_coord = self.config.sell_submit_coord

        should_submit = self.config.submit_enabled and not order.dry_run
        if should_submit:
            self._click(submit_coord)
            broker_status = "SUBMIT_CLICKED"
            message = "order form submitted"
        else:
            broker_status = "READY_FOR_MANUAL_SUBMIT"
            message = "order form filled, waiting for manual submit"

        after = self._take_screenshot(f"{action}_after")
        return {
            "submitted": should_submit,
            "before_screenshot": before,
            "after_screenshot": after,
            "broker_status": broker_status,
            "message": message,
        }
