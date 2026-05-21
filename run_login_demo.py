import os
import time
from pprint import pprint

from trade_automation import AutomationConfig
from trade_automation.executor import DesktopExecutor


def main():
    config = AutomationConfig.from_env()
    if config.login_button_coord is None:
        raise RuntimeError("BROKER_LOGIN_BUTTON_COORD is missing")
    if not config.broker_password:
        raise RuntimeError("BROKER_PASSWORD is missing")

    executor = DesktopExecutor(config)

    print("Broker login demo")
    print(f"Login button coord: {config.login_button_coord}")
    print("Please bring the broker login window to the foreground.")
    print("Assumption: the password input already has focus.")
    print("Automation starts in 5 seconds...")
    time.sleep(5)

    gui = executor._load_pyautogui()
    for ch in str(config.broker_password):
        if ch.isdigit():
            gui.press(ch)
            time.sleep(0.12)
        else:
            raise RuntimeError("BROKER_PASSWORD must contain digits only for this demo")
    executor._sleep()
    before = executor._take_screenshot("LOGIN_before")
    executor._click(config.login_button_coord)
    after = executor._take_screenshot("LOGIN_after")

    pprint(
        {
            "ok": True,
            "message": "login automation executed",
            "before_screenshot": before,
            "after_screenshot": after,
        }
    )


if __name__ == "__main__":
    os.environ.setdefault("BROKER_LOGIN_BUTTON_COORD", "1223,484")
    main()
