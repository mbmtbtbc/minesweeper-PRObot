import random
# import threading
import keyboard
import os
# import time  # added for sleep in alert waiting

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
var face = document.getElementById('face').className;
var tiles = document.querySelectorAll('div.square');
var board = {};
for (var i=0; i<tiles.length; i++) {
    var t = tiles[i];
    var id = t.id;
    if (!id || !/^\d+_\d+$/.test(id)) continue;
    var cls = t.className;
    var type = null;
    if (cls.indexOf('blank') !== -1) type = 0;
    else if (cls.indexOf('flag') !== -1) type = -1;
    else {
        for (var n=1; n<=8; n++) {
            if (cls.indexOf('open'+n) !== -1) { type = n; break; }
        }
    }
    if (type !== null) board[id] = type;
}
return [face, board];
"""


# ───────── ACTION SCRIPT ─────────
def make_action_script(left_clicks, right_clicks):
    calls = []

    # FLAGS FIRST (CRITICAL FIX)
    for tid in right_clicks:
        calls.append(
            f"(function(){{var e=document.getElementById('{tid}');if(!e)return;"
            f"var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
            f"e.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,button:2,buttons:2,clientX:x,clientY:y}}));"
            f"e.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,button:2,buttons:0,clientX:x,clientY:y}}));}})();"
        )

    for tid in left_clicks:
        calls.append(
            f"(function(){{var e=document.getElementById('{tid}');if(!e)return;"
            f"var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
            f"e.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,button:0,buttons:1,clientX:x,clientY:y}}));"
            f"e.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,button:0,buttons:0,clientX:x,clientY:y}}));}})();"
        )

    return "".join(calls)


# ───────── HARD STOP KEY ─────────
keyboard.add_hotkey("q", lambda: os._exit(0))


# ───────── DRIVER ─────────
def get_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUG_PORT)
    opts.set_capability("goog:unhandledPromptBehavior", "ignore")
    opts.binary_location = r"C://Users//ryvy2//AppData//Local//Programs//Opera GX//opera.exe"

    # Specify ChromeDriver version matching your Opera's Chromium version
    service = Service(ChromeDriverManager("143.0.7499.194").install())

    return webdriver.Chrome(service=service, options=opts)


# ───────── NEW ALERT HANDLER ─────────
def wait_for_alert_handled_and_exit(driver):
    """
    Freeze bot completely.
    User handles alert manually.
    Press ENTER afterwards to exit.
    """
    print("\n🏆 WIN DETECTED!")
    print("Handle the alert manually.")
    print("Press ENTER here after you finish.")

    input()   # <-- program fully pauses
    os._exit(0)


# ───────── SAFE EXECUTION ─────────
def safe_exec(driver, script, *args):
    """
    Execute JS safely. If a win alert appears, exit immediately.
    """
    try:
        return driver.execute_script(script, *args)
    except UnexpectedAlertPresentException:
        print("\n🏆 safe exec WIN DETECTED! Bot stopped. Please handle the alert manually.")
        wait_for_alert_handled_and_exit(driver)


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
    # Removed dismiss_alert() call – we no longer auto‑dismiss alerts
    driver.find_element(By.ID, "face").click()

    while FACE_LOSE in driver.find_element(By.ID, "face").get_attribute("class"):
        pass


def parse_board(raw):
    return {
        (int(k.split("_")[0]), int(k.split("_")[1])): int(v)
        for k, v in raw.items()
    }


# ───────── START CLICK ─────────
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
        if "minesweeperonline" in driver.current_url:
            break

    while True:

        face_class = driver.find_element(By.ID, "face").get_attribute("class")

        if FACE_WIN in face_class:
            print("\n🏆 WIN DETECTED! Handle the alert manually.")
            wait_for_alert_handled_and_exit(driver)

        # Only click face if it's a loss (reset), not a win
        if FACE_LOSE in face_class:
            do_reset(driver)
        
        driver.execute_script(LEFT_CLICK_START)

        while True:
            result = safe_exec(driver, READ_ALL)
            face, raw = result

            if FACE_WIN in face:
                print("\n🏆 WIN DETECTED! Handle the alert manually.")
                wait_for_alert_handled_and_exit(driver)

            if FACE_LOSE in face:
                do_reset(driver)
                break

            board = parse_board(raw)

            # safety check
            if sum(1 for v in board.values() if v == -1) > TOTAL_MINES:
                do_reset(driver)
                break

            # ───── FLAG PHASE (FIRST) ─────
            safe, flags = solve(board)

            to_flag = [
                f"{r}_{c}"
                for r, c in flags
                if board.get((r, c)) != -1
            ]

            if to_flag:
                safe_exec(driver, make_action_script([], to_flag))
                continue  # ← FORCE RE-READ (FIX #2)

            # ───── CLICK PHASE (SECOND) ─────
            to_click = [f"{r}_{c}" for r, c in safe]

            if to_click:
                safe_exec(driver, make_action_script(to_click, []))
                continue  # ← FORCE RE-READ

            # ───── GUESS ONLY IF NO LOGIC ─────
            blanks = [pos for pos, v in board.items() if v == 0]

            if blanks:
                r, c = random.choice(blanks)
                safe_exec(driver, make_action_script([f"{r}_{c}"], []))


if __name__ == "__main__":
    run()