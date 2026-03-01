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
import threading

stop_flag = threading.Event()
DEBUG_PORT  = "127.0.0.1:9222"
FACE_WIN    = "facewin"
FACE_LOSE   = "facedead"

ROW_MIN = 1;  ROW_MAX = 70
COL_MIN = 1;  COL_MAX = 70
TOTAL_MINES = 600
ALL_IDS = [f"{r}_{c}" for r in range(ROW_MIN, ROW_MAX+1)
                        for c in range(COL_MIN, COL_MAX+1)]
TOTAL_TILES = len(ALL_IDS)  # 480

UNKNOWN  =  0
FLAGGED  = -1

READ_ALL = r"""
var face  = document.getElementById('face').className;
var tiles = document.querySelectorAll('div.square');
var board = {};
for (var i = 0; i < tiles.length; i++) {
    var t   = tiles[i];
    var id  = t.id;
    if (!id || !/^\d+_\d+$/.test(id)) continue;
    var cls = t.className;
    var type = null;
    if      (cls.indexOf('bombflagged')  !== -1) { type = -1; }
    else if (cls.indexOf('bombrevealed') !== -1) { type =  9; }
    else if (cls.indexOf('blank')        !== -1) { type =  0; }
    else if (cls.indexOf('open0')        !== -1) { type =  9; }
    else {
        for (var n = 1; n <= 8; n++) {
            if (cls.indexOf('open' + n) !== -1) { type = n; break; }
        }
        if (type === null && cls.indexOf('open') !== -1) { type = 9; }
    }
    if (type !== null) board[id] = type;
}
return { face: face, board: board };
"""

keyboard.add_hotkey("q", lambda: os._exit(0))


def get_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUG_PORT)
    #opts.binary_location = r"C://Users//ryvy2//AppData//Local//Programs//Opera GX//opera.exe"
    return webdriver.Chrome(
        #service=Service(ChromeDriverManager("143.0.7499.194").install()),
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )

# ───────────────── ALERT HANDLER (FROM CODEBASE 1) ─────────────────
def check_for_alert(driver):
    try:
        driver.switch_to.alert

        # wait until user dismisses alert manually
        while True:
            try:
                driver.switch_to.alert
                time.sleep(0.3)
            except NoAlertPresentException:
                print("✅ Alert handled — stopping bot.")
                stop_flag.set()
                return True

    except NoAlertPresentException:
        return False

def handle_win(driver, losses):
    print(f"\n🏆 WIN! (Losses: {losses})")
    print("Waiting for alert — dismiss manually.")

    check_for_alert(driver)


def click_script(tile_id, button=0):
    buttons = 1 if button == 0 else 2
    return (
        f"(function(){{var e=document.getElementById('{tile_id}');if(!e)return;"
        f"var r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;"
        f"e.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,button:{button},buttons:{buttons},clientX:x,clientY:y}}));"
        f"e.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,button:{button},buttons:0,clientX:x,clientY:y}}));}})();"
    )


def make_action_script(left_clicks, right_clicks):
    return "".join(
        [click_script(t, 2) for t in right_clicks] +
        [click_script(t, 0) for t in left_clicks]
    )


def safe_exec(driver, script):

    # --- PREVENT alert auto-dismiss ---
    if check_for_alert(driver):
        return None

    try:
        return driver.execute_script(script)

    except UnexpectedAlertPresentException:
        check_for_alert(driver)
        return None


def parse_board(raw):
    return {
        (int(k.split("_")[0]), int(k.split("_")[1])): int(v)
        for k, v in raw.items()
    }


def neighbors(r, c):
    return [
        (r+dr, c+dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr or dc)
        and ROW_MIN <= r+dr <= ROW_MAX
        and COL_MIN <= c+dc <= COL_MAX
    ]


def solve(board):
    safe  = set()
    flags = set()

    current_flags   = sum(1 for v in board.values() if v == FLAGGED)
    flags_remaining = TOTAL_MINES - current_flags

    constraints = []
    for (r, c), val in board.items():
        if val < 1 or val > 8:
            continue
        nbs         = neighbors(r, c)
        unknown_nbs = [nb for nb in nbs if board.get(nb) == UNKNOWN]
        flagged_cnt = sum(1 for nb in nbs if board.get(nb) == FLAGGED)
        remain      = val - flagged_cnt
        if remain < 0 or remain > len(unknown_nbs):
            continue
        constraints.append((frozenset(unknown_nbs), remain))

    derived = list(constraints)
    seen    = set(constraints)
    for a_cells, a_cnt in constraints:
        for b_cells, b_cnt in constraints:
            if a_cells and a_cells < b_cells:
                diff_cells = b_cells - a_cells
                diff_count = b_cnt - a_cnt
                if diff_count < 0 or diff_count > len(diff_cells):
                    continue
                nc = (diff_cells, diff_count)
                if nc not in seen:
                    seen.add(nc)
                    derived.append(nc)

    for cells, remain in derived:
        if not cells:
            continue
        if remain == len(cells):
            flags |= cells
        if remain == 0:
            safe  |= cells

    safe  = {c for c in safe  if board.get(c) == UNKNOWN}
    flags = {c for c in flags if board.get(c) == UNKNOWN}

    if len(flags) > flags_remaining:
        flags = set()

    if safe or flags:
        return safe, flags

    border = set()
    for (r, c), val in board.items():
        if 1 <= val <= 8:
            for nb in neighbors(r, c):
                if board.get(nb) == UNKNOWN:
                    border.add(nb)

    interior = [p for p, v in board.items() if v == UNKNOWN and p not in border]
    pool     = interior if interior else [p for p, v in board.items() if v == UNKNOWN]
    if pool:
        return {random.choice(pool)}, set()

    return set(), set()


def wait_for_stable(driver, timeout=2.0):
    deadline = time.time() + timeout
    prev = None
    while time.time() < deadline:
        if check_for_alert(driver):
            return None
        result = safe_exec(driver, READ_ALL)
        if not result:
            return result
        key = (result["face"], len(result["board"]))
        if key == prev:
            return result
        prev = key
        time.sleep(0.05)
    return result


def do_reset(driver):
    try:
        driver.find_element(By.ID, "face").click()
    except UnexpectedAlertPresentException:
        return
    for _ in range(100):
        try:
            result = safe_exec(driver, READ_ALL)
            if result:
                face   = result["face"]
                b      = parse_board(result["board"])
                flags  = sum(1 for v in b.values() if v == FLAGGED)
                blanks = sum(1 for v in b.values() if v == UNKNOWN)
                if (FACE_LOSE not in face and FACE_WIN not in face
                        and flags == 0 and blanks == TOTAL_TILES):
                    return
        except Exception:
            pass
        time.sleep(0.05)


def run():
    driver = get_driver()

    for h in driver.window_handles:
        driver.switch_to.window(h)
        if "minesweeperonline" in driver.current_url:
            break

    print(f"[STARTUP] Board : rows {ROW_MIN}-{ROW_MAX}, cols {COL_MIN}-{COL_MAX}")
    print(f"[STARTUP] Tiles : {TOTAL_TILES}  Mines: {TOTAL_MINES}")

    losses = 0

    while not stop_flag.is_set():
        try:
            face_class = driver.find_element(By.ID, "face").get_attribute("class")
        except UnexpectedAlertPresentException:
            check_for_alert(driver)
            break

        if FACE_WIN in face_class:
            handle_win(driver, losses)
        if FACE_LOSE in face_class:
            losses += 1
            print(f"💀 Loss #{losses}")
            do_reset(driver)
            continue

        start_id = random.choice(ALL_IDS)
        safe_exec(driver, click_script(start_id))

        result = wait_for_stable(driver)
        if not result:
            continue

        while True:
            face  = result["face"]
            board = parse_board(result["board"])

            if FACE_WIN in face:
                handle_win(driver, losses)

            if FACE_LOSE in face:
                break

            flag_count = sum(1 for v in board.values() if v == FLAGGED)
            if flag_count > TOTAL_MINES:
                do_reset(driver)
                break

            safe_cells, flag_cells = solve(board)
            to_flag  = [f"{r}_{c}" for r, c in flag_cells  if board.get((r,c)) == UNKNOWN]
            to_click = [f"{r}_{c}" for r, c in safe_cells  if board.get((r,c)) == UNKNOWN]

            if to_flag:
                safe_exec(driver, make_action_script([], to_flag))
            elif to_click:
                safe_exec(driver, make_action_script(to_click, []))
            else:
                pool = [p for p, v in board.items() if v == UNKNOWN]
                if not pool:
                    break
                r, c = random.choice(pool)
                safe_exec(driver, make_action_script([f"{r}_{c}"], []))

            result = wait_for_stable(driver)
            if not result:
                break
    driver.quit()

if __name__ == "__main__":
    run()