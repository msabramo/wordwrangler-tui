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

| Key | Action |
|---|---|
| Arrow keys / `h` `j` `k` `l` | Move cursor |
| Enter / Space / click | Pick up a letter, then pick another cell in the same row to swap |
| `i` | Type the whole row at once (fast path once you know the anagram) |
| `r` | Reset the current row to its original scramble |
| Shift+`r` | Reset the whole puzzle |
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
