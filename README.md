# Minesweeper PRObot

A Minesweeper bot built with Python and Selenium, capable of winning all difficulty levels.

---


## Setup (Launching the Browser with Remote Debugging)

The bots attach to an already running browser via Chrome DevTools Protocol (CDP). You must launch your browser manually with the debugging port open before running any bot.

### Google Chrome

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug-profile"
```

### Opera GX

```bash
"C:\Users\<YourUsername>\AppData\Local\Programs\Opera GX\opera.exe" --remote-debugging-port=9222 --user-data-dir="C:\opera-debug-profile"
```

---

## KILL SWITCH (very important else the computer might get hijacked!)

Press **`Q`** at any time in the terminal to stop the bot immediately.

---

## How Each Bot Works

### Beginner Bot

A high-speed random clicker designed to brute-force wins through sheer volume of games. It:
- Attaches to the browser via CDP
- Reads all unrevealed (blank) tiles via a single JavaScript query
- Picks a random tile and clicks it using injected `MouseEvent` dispatches
- Detects win/loss via the smiley face element's CSS class (`facecool` = win, `facedead` = loss)
- Resets instantly on loss and loops
- Prints speed stats (games/sec) every 500 games

This bot has no logic at all! It was only a curious experiment with random luck and to setup the basic workflow (1 win in 600-7000 attempts, may take 2-3 minutes)

---

### Intermediate Bot

A constraint-based solver that plays logically. It:

- Right-clicks to flag mines, left-clicks to reveal safe tiles
- Works on only 2 rules (rule 1 to identify the safe spaces and rule 2 to detect the bombs)
- Rule 1: If the number of flags around a tile is same as the number on the tile, all surrounding tiles are definitely safe.
- Rule 2: If the number of tiles around a tile is same as the number on that tile, then all those surrounding tiles are definitely bombs and we flag them.
- Falls back to a random blank tile guess only when no logical move is available

---

### Expert / Custom Bot (both run on the same logic)

The most advanced solver, built for large boards. Extends the intermediate solver with:
- **Subset constraint inference** — for every pair of constraints `A ⊂ B`, derives a new constraint on `B − A` to unlock deductions the basic solver misses
- **Border vs. interior distinction** — when guessing, prefers interior tiles (not adjacent to any numbered clue) since they're statistically less likely to be mines
- **Stable-state polling** — after every action, polls the board until it stops changing before deciding the next move, preventing race conditions on slow renders
- **Robust alert & reset handling** — tracks win/loss across a `stop_flag` and performs clean board resets by verifying tile and flag counts

---

## Result!
 <img width="1919" height="1018" alt="Screenshot 2026-03-01 064906" src="https://github.com/user-attachments/assets/5d2f0614-acc7-49b2-b5af-7b130cbeb22f" />

(but the site uses advanced bot detection and so the high scores won't stick around haha)


---

## Notes

- The bots interact with the page entirely via **injected JavaScript MouseEvents** — no pixel-based clicking, making them fast and resolution-independent
- All board reads happen in a **single `execute_script` call** per frame for efficiency
- The `keyboard` library listens globally — pressing `Q` works even if the terminal isn't focused (on Windows)
- P.S. made just for fun and learning purposes :)

---
