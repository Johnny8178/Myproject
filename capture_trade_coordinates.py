import ctypes
import time


VK_F8 = 0x77
VK_F9 = 0x78
VK_ESC = 0x1B

FIELDS = [
    ("BROKER_LOGIN_PASSWORD_COORD", "login password box"),
    ("BROKER_LOGIN_BUTTON_COORD", "login button"),
    ("BROKER_BUY_CODE_COORD", "buy symbol box"),
    ("BROKER_BUY_PRICE_COORD", "buy price box"),
    ("BROKER_BUY_QTY_COORD", "buy quantity box"),
    ("BROKER_BUY_SUBMIT_COORD", "buy submit button"),
    ("BROKER_SELL_CODE_COORD", "sell symbol box"),
    ("BROKER_SELL_PRICE_COORD", "sell price box"),
    ("BROKER_SELL_QTY_COORD", "sell quantity box"),
    ("BROKER_SELL_SUBMIT_COORD", "sell submit button"),
]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos() -> tuple[int, int]:
    point = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def is_key_pressed(vk_code: int) -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)


def wait_key_release(vk_code: int):
    while is_key_pressed(vk_code):
        time.sleep(0.05)


def print_banner():
    print("Trade coordinate capture")
    print("Move the mouse to each target and press F8 to capture.")
    print("Press F9 to skip a field. Press Esc to exit early.")
    print("-" * 48)


def capture_fields() -> dict[str, str]:
    captured: dict[str, str] = {}
    for env_name, label in FIELDS:
        print()
        print(f"Target: {label}")
        print(f"Env var: {env_name}")
        while True:
            if is_key_pressed(VK_F8):
                x, y = get_cursor_pos()
                captured[env_name] = f"{x},{y}"
                print(f"Captured {env_name}={x},{y}")
                wait_key_release(VK_F8)
                break
            if is_key_pressed(VK_F9):
                captured[env_name] = ""
                print(f"Skipped {env_name}")
                wait_key_release(VK_F9)
                break
            if is_key_pressed(VK_ESC):
                print("Capture cancelled.")
                return captured
            time.sleep(0.05)
    return captured


def print_env_output(captured: dict[str, str]):
    print()
    print("PowerShell:")
    for env_name, value in captured.items():
        if value:
            print(f'$env:{env_name}="{value}"')
    print()
    print("CMD:")
    for env_name, value in captured.items():
        if value:
            print(f"set {env_name}={value}")


def main():
    print_banner()
    captured = capture_fields()
    print("-" * 48)
    if not captured:
        print("No coordinates captured.")
        return
    print_env_output(captured)


if __name__ == "__main__":
    main()
