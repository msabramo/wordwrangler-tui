# wordwrangler-tui

A k9s-style terminal UI for playing [wordwrangler.us](https://wordwrangler.us)'s
daily word-square puzzle without a browser.

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

## Play

```sh
wordwrangler                  # today's puzzle
wordwrangler --date 2026-09-01
wordwrangler --id 10102
```

(Or, without the installed command: `uv run wordwrangler`.)

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
| `?` | Show/hide the full keybindings help screen |
| `q` | Quit |

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

![Fresh puzzle loaded](docs/screenshots/Screenshot%202026-09-04%20at%2012.45.56%E2%80%AFPM.png)

A fresh puzzle (#10102) loaded straight from wordwrangler.us's live daily
puzzle, cursor on the first cell, nothing solved yet.

![Pick-up/swap mode](docs/screenshots/Screenshot%202026-09-04%20at%2012.46.07%E2%80%AFPM.png)

Swap mode: Enter (or a click) picks up a letter — the filled tile — then
moving to another cell in the same row and pressing Enter again swaps them.

![Typing a whole row](docs/screenshots/Screenshot%202026-09-04%20at%2012.46.21%E2%80%AFPM.png)

Fast typing mode (`i`): type all 5 letters of a row at once instead of
swapping tile-by-tile. Here `WRE__` is mid-entry, with placeholders for the
letters not yet typed.

![Partial progress with live validation](docs/screenshots/Screenshot%202026-09-04%20at%2012.46.41%E2%80%AFPM.png)

Live validation as you go: row 1 (STREW) is fully solved — row and column
both valid, shown in reversed green — while row 2 is mid-solve. Individual
cells turn green the instant their row or column becomes a real word.

![All rows solved but not yet aligned](docs/screenshots/Screenshot%202026-09-04%20at%2012.47.15%E2%80%AFPM.png)

Close, but not solved: every row already spells a valid word, but rows 3–5
aren't aligned with their columns yet (row 3 here is "ANGER," a valid word
that happens to be the wrong permutation for the columns to work — it needs
to be "RANGE" instead).

![Puzzle solved](docs/screenshots/Screenshot%202026-09-04%20at%2012.47.22%E2%80%AFPM.png)

Solved! Every row and column is a real word — STREW / CRUDE / RANGE / ACTED
/ MESSY — and the status bar celebrates with the elapsed solve time.
