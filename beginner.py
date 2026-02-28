import time
import random
import threading
import re
import keyboard

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

# ───────────────────────── CONFIG ─────────────────────────
DEBUG_PORT      = "127.0.0.1:9222"
RESTART_DELAY   = 0.01
PLAYER_NAME     = "BOT"
SMILEY_ID       = "face"
FACE_WIN        = "facecool"
FACE_LOSE       = "facedead"
TILE_ID_PATTERN = re.compile(r"^\d+_\d+$")

# ───────────────────────── OPTIMIZATIONS ─────────────────────────
DRIVER_PATH = ChromeDriverManager().install()

RESET_SCRIPT = """
    var el = document.getElementById('face');
    var rect = el.getBoundingClientRect();
    var cx = rect.left + rect.width/2, cy = rect.top + rect.height/2;
    ['mousedown','mouseup','click'].forEach(t =>
        el.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, clientX:cx, clientY:cy}))
    );
"""

CLICK_SCRIPT = """
    var el = document.getElementById(arguments[0]);
    if (!el) return;
    var rect = el.getBoundingClientRect();
    var cx = rect.left + rect.width/2, cy = rect.top + rect.height/2;
    ['mousedown','mouseup','click'].forEach(t =>
        el.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, clientX:cx, clientY:cy}))
    );
"""

GET_TILES_SCRIPT = """
    return Array.from(document.querySelectorAll('div.square.blank'))
        .filter(t => {
            if (!/^\\d+_\\d+$/.test(t.id)) return false;
            var r = t.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        })
        .map(t => t.id);
"""

# ───────────────────────── KILL SWITCH ─────────────────────────
stop_flag = threading.Event()

def listen_for_quit():
    keyboard.wait("q")
    print("\n  [Q] Stopping...")
    stop_flag.set()

threading.Thread(target=listen_for_quit, daemon=True).start()

# ───────────────────────── STATS ─────────────────────────
stats = {"games": 0, "wins": 0, "losses": 0}

# ───────────────────────── DRIVER ─────────────────────────
def get_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", DEBUG_PORT)
    options.page_load_strategy = 'eager'
    return webdriver.Chrome(
        service=Service(DRIVER_PATH),
        options=options
    )

def switch_to_minesweeper_tab(driver):
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "minesweeperonline.com" in driver.current_url:
            return
    driver.get("https://minesweeperonline.com/#beginner")
    time.sleep(1)

# ───────────────────────── ALERT HANDLER ─────────────────────────
def check_for_alert(driver):
    try:
        driver.switch_to.alert

        # Wait until alert disappears
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

# ───────────────────────── GAME HELPERS ─────────────────────────
def get_game_state(driver):

    if check_for_alert(driver):
        return "stop"

    try:
        classes = driver.find_element(By.ID, SMILEY_ID).get_attribute("class")

        if FACE_WIN in classes:
            return "win"
        if FACE_LOSE in classes:
            return "lose"

    except UnexpectedAlertPresentException:
        check_for_alert(driver)
        return "stop"

def reset_game(driver):
    driver.execute_script(RESET_SCRIPT)

def get_unrevealed_tile_ids(driver):
    return driver.execute_script(GET_TILES_SCRIPT)

def click_tile(driver, tile_id):
    driver.execute_script(CLICK_SCRIPT, tile_id)

# ───────────────────────── MAIN LOOP ─────────────────────────
def run_bot():
    print("=" * 55)
    print("  MINESWEEPER BOT  |  Press Q to stop")
    print("=" * 55)

    driver = get_driver()
    switch_to_minesweeper_tab(driver)

    start_time = time.time()

    while not stop_flag.is_set():
        stats["games"] += 1
        game_clicks = 0

        reset_game(driver)

        while not stop_flag.is_set():
            state = get_game_state(driver)
            if state == "stop":
                break

            if state == "win":
                stats["wins"] += 1
                print(f"\n  ✅ WON game #{stats['games']}!")
                check_for_alert(driver)
                stop_flag.set()
                break

            if state == "lose":
                stats["losses"] += 1
                time.sleep(RESTART_DELAY)
                break

            tile_ids = get_unrevealed_tile_ids(driver)
            if not tile_ids:
                time.sleep(RESTART_DELAY)
                break

            click_tile(driver, random.choice(tile_ids))
            game_clicks += 1

        # Print games count every 500 games
        if stats["games"] % 500 == 0:
            elapsed = time.time() - start_time
            speed = stats["games"] / elapsed
            print(f"\r  Games: {stats['games']} | Speed: {speed:.1f} games/sec", end="", flush=True)

    elapsed = time.time() - start_time
    speed = stats["games"] / elapsed if elapsed > 0 else 0
    print(f"\n\n  ══ FINAL STATS ══")
    print(f"  Games : {stats['games']}")
    print(f"  Speed : {speed:.1f} games/sec")

    try:
        driver.quit()
    except Exception:
        pass

if __name__ == "__main__":
    run_bot()