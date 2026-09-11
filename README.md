# wordwrangler-tui

A k9s-style terminal UI for playing [wordwrangler.us](https://wordwrangler.us)'s
daily word-square puzzle without a browser.

[☕ Buy me a coffee](https://buymeacoffee.com/msabramo) if you enjoy this.

![Solved](docs/screenshots/Screenshot%202026-09-04%20at%202.34.34%E2%80%AFPM.png)

Each row starts with its 5 letters scrambled. Reorder the letters *within* a
row (letters never move between rows) until every row and every column spells
a real word.

No official API exists — this replays the site's own public Firestore reads
(`dailyPuzzle/{date}` → `puzzles/{id}`) and validates against the same
`words_five.txt` word list the site ships to the browser.

## Install

Managed with [uv](https://docs.astral.sh/uv/). To install the `wordwrangler`
command (editable, so local edits take effect immediately, no reinstall
needed):

```sh
uv tool install --editable .
```

For local development instead (no global command):

```sh
uv sync
```

### Docker

No Python setup needed — just Docker:

```sh
docker run -it --rm ghcr.io/msabramo/wordwrangler-tui
```

Or build it yourself:

```sh
docker build -t wordwrangler-tui .
docker run -it --rm wordwrangler-tui
```

Pass the same flags as the CLI, e.g. `docker run -it --rm ghcr.io/msabramo/wordwrangler-tui --date 2026-09-01`.

## Play

```sh
wordwrangler                  # today's puzzle
wordwrangler --date 2026-09-01
wordwrangler --id 10102
```

(Or, without the installed command: `uv run wordwrangler`.)

`--date` accepts anything from **2026-04-27** (WordWrangler's launch date,
found by binary-searching the Firestore endpoint) through today. Pass a date
outside that range and it tells you so instead of a raw HTTP error.

## Controls

Click a letter, then click another letter in the same row to swap them —
this is closest to how the official web version plays (drag/click tiles
around within a row).

The TUI also supports keyboard control: arrow keys move the cursor, and
Enter or Space picks up/swaps a letter the same way a click does.

Vim users can navigate with `h` `j` `k` `l` in place of the arrow keys.

For the fastest path once you already know the anagram, press `i` and type
all 5 letters of the row at once instead of swapping tile-by-tile.

| Key | Action |
|---|---|
| Click | Pick a letter, then click another cell in the same row to swap |
| Arrow keys | Move cursor |
| Enter / Space | Pick up a letter, then move and press again to swap |
| `h` `j` `k` `l` | Move cursor (vim-style alternative to arrow keys) |
| `i` | Type the whole row at once (fast path once you know the anagram) |
| `r` | Reset the current row to its original scramble |
| Shift+`r` | Reset the whole puzzle |
| `p` | Pause/resume — hides the board and freezes the timer |
| `?` | Show/hide the full keybindings help screen |
| `a` | About WordWrangler (then `f` to send feedback to Max) |
| `q` | Quit |

### Pause/resume

`p` replicates the official web version's pause feature: it hides every
letter (and any row/column coloring, so it can't leak solve progress),
freezes the timer, and blocks all board actions. Pressing `p` again reveals
the board and resumes the timer from exactly where it left off — the paused
time itself doesn't count toward your solve time.

### About & feedback

`a` opens a compact about/how-to-play panel (an unofficial equivalent of the
website's ⓘ button). From there, `f` opens a feedback form; sending it
performs a real write to WordWrangler's public `feedback` Firestore
collection — the same one the official site's own form uses — so it reaches
Max Wheeler, the game's creator, directly.

### Typing a whole row

Press `i` to start typing the row under the cursor. Type all 5 letters in the
order you want them; it commits automatically once you've typed 5, or press
Enter early / Backspace to correct / Esc to cancel. The typed letters must be
an exact rearrangement of that row's given tiles — mistype the letters (wrong
multiset) and it clears the buffer with an error so you can retry.

Cells light up green when their row and/or column already spell a valid
word; both green means that row/column pair is solved. The puzzle is
complete when every row and column is green.

## Screenshots

(Screenshots use `wordwrangler --date 2026-04-27` — WordWrangler's very first
puzzle — so nothing here spoils a current one.)

![Initial state](docs/screenshots/Screenshot%202026-09-04%20at%202.27.19%E2%80%AFPM.png)

Initial state after `wordwrangler --date 2026-04-27`: puzzle #9, cursor on
the first cell, nothing solved yet.

![Swap mode](docs/screenshots/Screenshot%202026-09-04%20at%202.28.07%E2%80%AFPM.png)

Swap mode: Enter (or a click) picks up a letter — the filled tile — then
moving to another cell in the same row and pressing Enter again swaps them.

![Fast typing mode](docs/screenshots/Screenshot%202026-09-04%20at%202.28.58%E2%80%AFPM.png)

Fast typing mode (`i`): type all 5 letters of a row at once instead of
swapping tile-by-tile. Here `RAN__` is mid-entry, with placeholders for the
letters not yet typed.

![Live validation](docs/screenshots/Screenshot%202026-09-04%20at%202.32.17%E2%80%AFPM.png)

Live validation as you go: rows 1–3 (TWIST / RANCH / UTTER) are already
valid words, and column 2 happens to spell WATER, so those intersecting
cells get the deeper "both valid" highlight. Rows 4–5 are still scrambled.

![Close, but not solved](docs/screenshots/Screenshot%202026-09-04%20at%202.33.57%E2%80%AFPM.png)

Close, but not solved: four of five rows are solved (TWIST / RANCH / UTTER /
SCENE). The last row's letters are all present but in the wrong order —
"TRHWE" isn't a word; it needs to read THREW.

![Solved](docs/screenshots/Screenshot%202026-09-04%20at%202.34.34%E2%80%AFPM.png)

Solved! Every row and column is a real word — TWIST / RANCH / UTTER / SCENE
/ THREW — and the status bar celebrates with the elapsed solve time.

![Keybindings help screen](docs/screenshots/Screenshot%202026-09-04%20at%202.34.55%E2%80%AFPM.png)

The full keybindings help screen (`?`), including bindings that aren't
shown in the bottom legend, like the typing-mode-only Enter/Backspace/Esc.

![About screen](docs/screenshots/Screenshot%202026-09-04%20at%202.35.16%E2%80%AFPM.png)

The About screen (`a`) — an unofficial equivalent of the website's ⓘ
button — with a clickable link to wordwrangler.us and a compact
how-to-play summary.

![Feedback screen](docs/screenshots/Screenshot%202026-09-04%20at%202.36.40%E2%80%AFPM.png)

The feedback screen (`f` from About). Sending this performs a real write to
WordWrangler's public `feedback` Firestore collection, reaching Max Wheeler
directly — same as using the official site's own feedback form.
