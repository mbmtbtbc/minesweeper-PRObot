import random
import keyboard
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

DEBUG_PORT = "127.0.0.1:9222"
TOTAL_MINES = 40
FACE_WIN = "facewin"
FACE_LOSE = "facedead"

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
return { face: face, board: board };
"""

LEFT_CLICK_START = (
    "var e=document.getElementById('8_8');if(!e)return;"
    "var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
    "e.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0,buttons:1,clientX:x,clientY:y}));"
    "e.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,button:0,buttons:0,clientX:x,clientY:y}));"
)

keyboard.add_hotkey("q", lambda: os._exit(0))


def get_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUG_PORT)
    opts.binary_location = r"C://Users//ryvy2//AppData//Local//Programs//Opera GX//opera.exe"
    return webdriver.Chrome(service=Service(ChromeDriverManager("143.0.7499.194").install()), options=opts)


def check_for_alert(driver):
    """Proactively check if an alert is open. If so, wait for user to dismiss it manually."""
    try:
        driver.switch_to.alert  # Alert is open
        print("\n🏆 WIN! Dismiss the alert manually to stop the bot.")
        while True:
            try:
                driver.switch_to.alert  # Still open — keep waiting
                time.sleep(0.3)
            except NoAlertPresentException:
                print("✅ Alert dismissed — stopping.")
                os._exit(0)
    except NoAlertPresentException:
        return  # No alert, carry on


def make_action_script(left_clicks, right_clicks):
    calls = []
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


def safe_exec(driver, script):
    try:
        return driver.execute_script(script)
    except UnexpectedAlertPresentException:
        check_for_alert(driver)


def neighbors(r, c):
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]


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


def parse_board(raw):
    return {(int(k.split("_")[0]), int(k.split("_")[1])): int(v) for k, v in raw.items()}


def do_reset(driver):
    driver.find_element(By.ID, "face").click()
    while FACE_LOSE in driver.find_element(By.ID, "face").get_attribute("class"):
        pass


def run():
    driver = get_driver()

    for h in driver.window_handles:
        driver.switch_to.window(h)
        if "minesweeperonline" in driver.current_url:
            break

    while True:
        # Proactive alert check before touching anything
        check_for_alert(driver)

        try:
            face_class = driver.find_element(By.ID, "face").get_attribute("class")
        except UnexpectedAlertPresentException:
            check_for_alert(driver)
            continue

        if FACE_WIN in face_class:
            check_for_alert(driver)
        if FACE_LOSE in face_class:
            do_reset(driver)

        driver.execute_script(LEFT_CLICK_START)

        while True:
            # Proactive alert check at the top of every inner loop iteration
            check_for_alert(driver)

            result = safe_exec(driver, READ_ALL)
            if not result:
                return

            face = result["face"]
            if FACE_WIN in face:
                check_for_alert(driver)
            if FACE_LOSE in face:
                do_reset(driver)
                break

            board = parse_board(result["board"])

            if sum(1 for v in board.values() if v == -1) > TOTAL_MINES:
                do_reset(driver)
                break

            safe, flags = solve(board)

            to_flag = [f"{r}_{c}" for r, c in flags if board.get((r, c)) != -1]
            if to_flag:
                safe_exec(driver, make_action_script([], to_flag))
                continue

            to_click = [f"{r}_{c}" for r, c in safe]
            if to_click:
                safe_exec(driver, make_action_script(to_click, []))
                continue

            blanks = [pos for pos, v in board.items() if v == 0]
            if blanks:
                r, c = random.choice(blanks)
                safe_exec(driver, make_action_script([f"{r}_{c}"], []))


if __name__ == "__main__":
    run()