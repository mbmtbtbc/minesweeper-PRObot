import random
import keyboard
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    NoAlertPresentException,
)

# ───────── CONFIG ─────────
DEBUG_PORT = "127.0.0.1:9222"
TOTAL_MINES = 40
FACE_WIN = "facewin"
FACE_LOSE = "facedead"


# ───────── FAST BOARD READ ─────────
READ_ALL = r"""
var face = document.getElementById('face')?.className || '';
var tiles = document.querySelectorAll('div.square');
var board = {};
for (var i = 0; i < tiles.length; i++) {
    var t = tiles[i];
    var id = t.id;
    if (!id || !/^\d+_\d+$/.test(id)) continue;
    var cls = t.className;
    var type = null;
    if (cls.indexOf('blank') !== -1) type = 0;
    else if (cls.indexOf('flag') !== -1) type = -1;
    else {
        for (var n = 1; n <= 8; n++) {
            if (cls.indexOf('open' + n) !== -1) { type = n; break; }
        }
    }
    if (type !== null) board[id] = type;
}
return [face, board];
"""


# ───────── ACTION SCRIPT (batches left + right clicks) ─────────
def make_action_script(left_clicks, right_clicks):
    calls = []

    # Right clicks (flags) first — important order
    for tid in right_clicks:
        calls.append(
            f"(function(){{var e=document.getElementById('{tid}');if(!e)return;"
            f"var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
            f"e.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,button:2,buttons:2,clientX:x,clientY:y}}));"
            f"e.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,button:2,buttons:0,clientX:x,clientY:y}}));}})();"
        )

    # Then left clicks
    for tid in left_clicks:
        calls.append(
            f"(function(){{var e=document.getElementById('{tid}');if(!e)return;"
            f"var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
            f"e.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,button:0,buttons:1,clientX:x,clientY:y}}));"
            f"e.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,button:0,buttons:0,clientX:x,clientY:y}}));}})();"
        )

    return "".join(calls)


# ───────── HARD STOP ─────────
keyboard.add_hotkey("q", lambda: os._exit(0))


# ───────── DRIVER ─────────
def get_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUG_PORT)
    # Removed "ignore" — default is usually better for manual alert control
    opts.binary_location = r"C://Users//ryvy2//AppData//Local//Programs//Opera GX//opera.exe"
    opts.add_argument("--disable-popup-blocking")

    service = Service(ChromeDriverManager("143.0.7499.194").install())
    return webdriver.Chrome(service=service, options=opts)


# ───────── ALERT HANDLER ─────────
def check_and_handle_win_alert(driver, timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        try:
            alert = driver.switch_to.alert
            print("\n" + "═" * 70)
            print(" 🔔 WIN ALERT DETECTED")
            print(f" Text: {alert.text.strip()}")
            print(" → Click OK in browser NOW")
            print(" → Then press ENTER here to continue...")
            print("═" * 70)
            input()
            driver.switch_to.default_content()
            return True
        except NoAlertPresentException:
            time.sleep(0.12)  # tight polling
    return False


# ───────── SAFE EXEC ─────────
def safe_exec(driver, script, *args):
    for attempt in range(1, 6):
        try:
            return driver.execute_script(script, *args)
        except UnexpectedAlertPresentException:
            print(f"  Alert during JS (attempt {attempt})")
            if check_and_handle_win_alert(driver):
                continue
            print("  Alert timeout → aborting action")
            break
        except Exception as e:
            raise e
    raise RuntimeError("JS execution failed after retries (alert issues)")


# ───────── SOLVER LOGIC (UNCHANGED) ─────────
def neighbors(r, c):
    return [
        (r + dr, c + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if dr or dc
    ]


def solve(board):
    safe, flags = set(), set()

    for pos, val in board.items():
        if val <= 0:
            continue
        r, c = pos
        nbs = neighbors(r, c)
        blanks = [p for p in nbs if board.get(p) == 0]
        flagged = sum(1 for p in nbs if board.get(p) == -1)
        remaining = val - flagged

        if remaining == len(blanks) > 0:
            flags.update(blanks)
        if remaining == 0 and blanks:
            safe.update(blanks)

    return safe, flags


def do_reset(driver):
    face = driver.find_element(By.ID, "face")
    face.click()
    # Quick poll instead of blind sleep
    for _ in range(50):  # max ~2.5s
        if FACE_LOSE not in face.get_attribute("class"):
            return
        time.sleep(0.05)
    print("Warning: reset face didn't recover quickly")


def parse_board(raw):
    return {
        (int(k.split("_")[0]), int(k.split("_")[1])): int(v)
        for k, v in raw.items()
    }


# ───────── INITIAL CLICK ─────────
LEFT_CLICK_START = (
    "var e=document.getElementById('8_8');if(!e)return;"
    "var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
    "e.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0,buttons:1,clientX:x,clientY:y}));"
    "e.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,buttons:0,clientX:x,clientY:y}));"
)


# ───────── MAIN LOOP ─────────
def run():
    driver = get_driver()

    for h in driver.window_handles:
        driver.switch_to.window(h)
        if "minesweeperonline" in driver.current_url.lower():
            break
    else:
        print("Minesweeper tab not found")
        return

    print("Bot running — press Q to exit")

    while True:
        # Quick alert check
        if check_and_handle_win_alert(driver, timeout=4):
            print("Win alert handled → stopping")
            break

        # Read board once (includes face status)
        result = safe_exec(driver, READ_ALL)
        face, raw = result

        if FACE_WIN in face:
            print("Win detected via board read")
            if check_and_handle_win_alert(driver):
                print("Alert handled → stopping")
                break
            # If no alert → strange state, reset
            do_reset(driver)
            continue

        if FACE_LOSE in face:
            do_reset(driver)
            driver.execute_script(LEFT_CLICK_START)
            continue

        board = parse_board(raw)

        # Safety net
        if sum(1 for v in board.values() if v == -1) > TOTAL_MINES:
            do_reset(driver)
            continue

        safe, flags = solve(board)

        to_flag = [f"{r}_{c}" for r, c in flags if board.get((r, c)) != -1]
        to_click = [f"{r}_{c}" for r, c in safe]

        if to_flag or to_click:
            # Batch both in one go → big speed win
            script = make_action_script(to_click, to_flag)
            safe_exec(driver, script)
            continue

        # Guess only when necessary
        blanks = [pos for pos, v in board.items() if v == 0]
        if blanks:
            r, c = random.choice(blanks)
            safe_exec(driver, make_action_script([f"{r}_{c}"], []))


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print("Error:", type(e).__name__, str(e))
    finally:
        print("Bot finished.")