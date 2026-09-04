"""A k9s-style terminal UI for playing wordwrangler.us's daily word-square puzzle.

Each of the 5 rows starts with its letters scrambled. Reorder the letters
*within* a row (letters never move between rows) until every row and every
column spells a real word.
"""

from __future__ import annotations

import argparse
import asyncio
import time
import webbrowser
from datetime import date

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static, TextArea

from .api import (
    Puzzle,
    PuzzleFetchError,
    fetch_puzzle,
    fetch_puzzle_for_date,
    fetch_today_puzzle,
    load_wordlist,
    submit_feedback,
)

GRID_SIZE = 5
WORDWRANGLER_URL = "https://wordwrangler.us/"


class Cell(Static):
    """A single letter tile in the 5x5 grid."""

    def __init__(self, row: int, col: int) -> None:
        super().__init__("", id=f"cell-{row}-{col}")
        self.row = row
        self.col = col

    def on_click(self) -> None:
        self.app.handle_cell_activate(self.row, self.col)


class HelpScreen(ModalScreen):
    """A dismissible overlay listing every keybinding."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-box {
        width: auto;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 3;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("question_mark", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("enter", "close", "Close"),
        Binding("space", "close", "Close"),
    ]

    HELP_TEXT = """\
[b]WordWrangler — Keybindings[/b]

[b]Move[/b]
  Arrow keys / h j k l    Move cursor
  Click                   Select a cell

[b]Swap[/b]
  Enter / Space / click   Pick up a letter, then pick another
                          cell in the same row to swap

[b]Type a whole row[/b]
  i                       Start typing the row under the cursor
  (while typing) Enter    Commit early
  (while typing) Backspace  Delete last letter
  (while typing) Escape   Cancel

[b]Other[/b]
  r                       Reset current row
  shift+r                 Reset whole puzzle
  p                       Pause / resume (hides the board, freezes the timer)
  ?                       Toggle this help
  a                       About WordWrangler (then 'f' for feedback to Max)
  q                       Quit

[dim]press any of the keys above to close[/dim]"""

    def compose(self) -> ComposeResult:
        yield Static(self.HELP_TEXT, id="help-box")

    def action_close(self) -> None:
        self.app.pop_screen()


class AboutScreen(ModalScreen):
    """Replicates the web version's (i) info panel: a compact how-to-play blurb.

    Deliberately kept to a handful of lines — about the same footprint as
    the game grid itself — so it fits comfortably without needing a huge
    terminal or tiny font. The feedback form lives in a separate screen
    (FeedbackScreen), opened from here with 'f'.
    """

    CSS = """
    AboutScreen {
        align: center middle;
    }
    #about-box {
        width: 60;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("a", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("f", "open_feedback", "Feedback"),
    ]

    ABOUT_TEXT = (
        "[b]WordWrangler[/b] — a daily word-square puzzle by Max Wheeler "
        "([@click=app.open_wordwrangler]wordwrangler.us[/]). This is an unofficial terminal client.\n\n"
        "Swap letters within a row (never between rows) until every row AND every column "
        "spells a valid word. A cell turns light green when its row or column is valid, "
        "bold green when both are.\n\n"
        "[dim]f: send feedback to Max · esc/a: close[/dim]"
    )

    def compose(self) -> ComposeResult:
        with Vertical(id="about-box"):
            yield Static(self.ABOUT_TEXT)

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_open_feedback(self) -> None:
        self.app.push_screen(FeedbackScreen())


class FeedbackScreen(ModalScreen):
    """Feedback form — writes a real doc to WordWrangler's public `feedback`
    Firestore collection, the same one the official site's own form uses.
    Reaches Max Wheeler, the game's creator, not us.
    """

    CSS = """
    FeedbackScreen {
        align: center middle;
    }
    #feedback-box {
        width: 60;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #feedback-box TextArea {
        height: 5;
        margin-top: 1;
        border: round $surface;
    }
    #feedback-box Input {
        margin-top: 1;
    }
    #feedback-status {
        margin-top: 1;
        height: 1;
    }
    #feedback-buttons {
        margin-top: 1;
        height: auto;
        align: left middle;
    }
    #feedback-buttons Button {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="feedback-box"):
            yield Static("[b]Send feedback to Max[/b]")
            yield TextArea(id="feedback-text")
            yield Input(placeholder="Email (optional)", id="feedback-email")
            yield Static("", id="feedback-status")
            with Horizontal(id="feedback-buttons"):
                yield Button("Send", id="send-feedback", variant="primary")
                yield Button("Cancel", id="cancel-feedback")

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-feedback":
            self.app.pop_screen()
        elif event.button.id == "send-feedback":
            self.send_feedback()

    def send_feedback(self) -> None:
        text = self.query_one("#feedback-text", TextArea).text.strip()
        status = self.query_one("#feedback-status", Static)
        if not text:
            status.update("[$warning]Type something first.[/]")
            return
        email = self.query_one("#feedback-email", Input).value
        self.query_one("#send-feedback", Button).disabled = True
        status.update("Sending…")
        self.run_worker(self._do_submit(text, email), exclusive=True)

    async def _do_submit(self, text: str, email: str) -> None:
        status = self.query_one("#feedback-status", Static)
        send_button = self.query_one("#send-feedback", Button)
        try:
            await asyncio.to_thread(submit_feedback, text, email or None)
        except Exception as exc:
            status.update(f"[red]Failed to send: {exc}[/red]")
            send_button.disabled = False
        else:
            status.update("Thanks — sent to Max!")
            self.query_one("#feedback-text", TextArea).text = ""
            self.query_one("#feedback-email", Input).value = ""
            send_button.disabled = False


class WordWranglerApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        padding: 1 0 0 0;
    }
    #subtitle {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    #board {
        layout: grid;
        grid-size: 5 5;
        grid-columns: 5;
        grid-rows: 3;
        grid-gutter: 1 2;
        width: auto;
        height: auto;
        padding: 1 2;
    }
    Cell {
        content-align: center middle;
        text-style: bold;
        border: round $surface;
    }
    Cell.cursor {
        border: round $accent;
    }
    Cell.selected {
        background: $warning 30%;
        border: round $warning;
    }
    Cell.typing {
        background: $accent 30%;
        border: round $accent;
    }
    Cell.paused {
        color: $text-muted;
        border: round $surface;
    }
    Cell.row-valid, Cell.col-valid {
        color: $success;
    }
    Cell.both-valid {
        color: $success;
        text-style: bold reverse;
    }
    #status {
        width: 100%;
        content-align: center middle;
        padding: 1;
    }
    #legend {
        dock: bottom;
        width: 100%;
        height: auto;
        content-align: center middle;
        color: $footer-foreground;
        background: $footer-background;
        padding: 0 1;
    }
    """

    # A plain wrapping line instead of Textual's built-in Footer: Footer is a
    # single-line horizontal *scrollable* bar, not a flow layout — it can't
    # wrap, so a narrow terminal would just hide/scroll bindings instead of
    # reflowing them. This wraps onto as many lines as the width needs.
    LEGEND_TEXT = (
        "↑↓←→/hjkl move · ⏎/space swap · i type row · r reset row · "
        "shift+r reset all · p pause · a about · ? help · q quit"
    )

    BINDINGS = [
        Binding("up", "move_cursor('up')", "Up"),
        Binding("down", "move_cursor('down')", "Down"),
        Binding("left", "move_cursor('left')", "Left"),
        Binding("right", "move_cursor('right')", "Right"),
        Binding("k", "move_cursor('up')", "Up", show=False),
        Binding("j", "move_cursor('down')", "Down", show=False),
        Binding("h", "move_cursor('left')", "Left", show=False),
        Binding("l", "move_cursor('right')", "Right", show=False),
        Binding("enter,space", "activate", "Select/Swap"),
        Binding("i", "start_typing", "Type row"),
        Binding("r", "reset_row", "Reset row"),
        Binding("shift+r", "reset_all", "Reset all"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("question_mark", "toggle_help", "Help"),
        Binding("a", "show_about", "About"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, puzzle: Puzzle, wordlist: set[str]) -> None:
        super().__init__()
        self.puzzle = puzzle
        self.wordlist = wordlist
        self.original_rows = [list(r) for r in puzzle.rows]
        self.grid = [list(r) for r in puzzle.rows]
        self.cursor = (0, 0)
        self.selected: tuple[int, int] | None = None
        self.start_time: float | None = None
        self.elapsed = 0.0
        self.solved = False
        self.typing_row: int | None = None
        self.type_buffer = ""
        self.error_message: str | None = None
        self.paused = False
        self.paused_at: float | None = None

    def format_title(self) -> str:
        title = f"WordWrangler #{self.puzzle.puzzle_id}"
        if self.puzzle.date:
            d = date.fromisoformat(self.puzzle.date)
            title += f" — {d:%A, %B} {d.day}, {d:%Y}"
        return title

    def compose(self) -> ComposeResult:
        yield Static(self.format_title(), id="title")
        yield Static(
            "unofficial client for [@click=app.open_wordwrangler]wordwrangler.us[/]",
            id="subtitle",
        )
        yield Container(id="board")
        yield Static("", id="status")
        yield Static(self.LEGEND_TEXT, id="legend")

    def on_mount(self) -> None:
        board = self.query_one("#board", Container)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                board.mount(Cell(r, c))
        self.refresh_board()
        self.set_interval(1, self.tick)

    def tick(self) -> None:
        if self.start_time is not None and not self.solved and not self.paused:
            self.elapsed = time.monotonic() - self.start_time
            self.update_status()

    def row_word(self, r: int) -> str:
        return "".join(self.grid[r])

    def col_word(self, c: int) -> str:
        return "".join(self.grid[r][c] for r in range(GRID_SIZE))

    def row_valid(self, r: int) -> bool:
        return self.row_word(r).lower() in self.wordlist

    def col_valid(self, c: int) -> bool:
        return self.col_word(c).lower() in self.wordlist

    def refresh_board(self) -> None:
        row_valid = [self.row_valid(r) for r in range(GRID_SIZE)]
        col_valid = [self.col_valid(c) for c in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.query_one(f"#cell-{r}-{c}", Cell)
                if self.paused:
                    # Hide letters (and any row/col validity coloring, which
                    # would otherwise leak solve progress) while paused —
                    # matches the web version flipping tiles to their blank
                    # backs.
                    cell.update("▒")
                    cell.set_classes("paused")
                    continue
                if self.typing_row == r:
                    letter = self.type_buffer[c].upper() if c < len(self.type_buffer) else "_"
                else:
                    letter = self.grid[r][c].upper()
                cell.update(letter)
                classes = []
                if self.typing_row == r:
                    classes.append("typing")
                if (r, c) == self.cursor:
                    classes.append("cursor")
                if self.selected == (r, c):
                    classes.append("selected")
                if row_valid[r] and col_valid[c]:
                    classes.append("both-valid")
                elif row_valid[r]:
                    classes.append("row-valid")
                elif col_valid[c]:
                    classes.append("col-valid")
                cell.set_classes(" ".join(classes))
        self.solved = all(row_valid) and all(col_valid)
        self.update_status()

    def update_status(self) -> None:
        status = self.query_one("#status", Static)
        if self.paused:
            mins, secs = divmod(int(self.elapsed), 60)
            status.update(f"{mins:02d}:{secs:02d} — PAUSED ⏸   (press p to resume · ? for help)")
            return
        if self.typing_row is not None:
            buf = self.type_buffer.upper().ljust(GRID_SIZE, "_")
            line = f"Typing row {self.typing_row + 1}: {buf}   (enter: commit · backspace: delete · esc: cancel)"
            if self.error_message:
                line += f"   ⚠ {self.error_message}"
            status.update(line)
            return
        mins, secs = divmod(int(self.elapsed), 60)
        state = "SOLVED! \U0001f389" if self.solved else "in progress"
        status.update(f"{mins:02d}:{secs:02d} — {state}   (press ? for help)")

    def action_move_cursor(self, direction: str) -> None:
        if self.paused:
            return
        r, c = self.cursor
        if direction == "up":
            r = (r - 1) % GRID_SIZE
        elif direction == "down":
            r = (r + 1) % GRID_SIZE
        elif direction == "left":
            c = (c - 1) % GRID_SIZE
        elif direction == "right":
            c = (c + 1) % GRID_SIZE
        self.cursor = (r, c)
        self.refresh_board()

    def action_activate(self) -> None:
        self.handle_cell_activate(*self.cursor)

    def handle_cell_activate(self, r: int, c: int) -> None:
        if self.solved or self.paused or self.typing_row is not None:
            return
        self.cursor = (r, c)
        if self.start_time is None:
            self.start_time = time.monotonic()
        if self.selected is None:
            self.selected = (r, c)
        elif self.selected == (r, c):
            self.selected = None
        elif self.selected[0] == r:
            sc = self.selected[1]
            self.grid[r][c], self.grid[r][sc] = self.grid[r][sc], self.grid[r][c]
            self.selected = None
        else:
            # Letters can't move between rows; treat this as re-picking instead.
            self.selected = (r, c)
        self.refresh_board()

    def action_start_typing(self) -> None:
        if self.solved or self.paused:
            return
        r, _ = self.cursor
        self.typing_row = r
        self.type_buffer = ""
        self.error_message = None
        self.selected = None
        self.refresh_board()

    def on_key(self, event: events.Key) -> None:
        # While typing a row, every keystroke belongs to the type buffer —
        # letters like 'r' and 'q' must not fall through to their bindings.
        if self.typing_row is None:
            return
        event.stop()
        event.prevent_default()

        if event.key == "escape":
            self.typing_row = None
            self.type_buffer = ""
            self.error_message = None
            self.refresh_board()
        elif event.key == "backspace":
            self.type_buffer = self.type_buffer[:-1]
            self.error_message = None
            self.refresh_board()
        elif event.key == "enter":
            self.commit_typed_row()
        elif event.character and event.character.isalpha() and len(self.type_buffer) < GRID_SIZE:
            if self.start_time is None:
                self.start_time = time.monotonic()
            self.type_buffer += event.character.lower()
            self.error_message = None
            if len(self.type_buffer) == GRID_SIZE:
                self.commit_typed_row()
            else:
                self.refresh_board()

    def commit_typed_row(self) -> None:
        r = self.typing_row
        if r is None:
            return
        original = self.original_rows[r]
        if len(self.type_buffer) == GRID_SIZE and sorted(self.type_buffer) == sorted(original):
            self.grid[r] = list(self.type_buffer)
            self.typing_row = None
            self.type_buffer = ""
            self.error_message = None
        else:
            self.error_message = (
                f"'{self.type_buffer.upper()}' isn't a rearrangement of row {r + 1} "
                f"({''.join(original).upper()}) — try again"
            )
            self.type_buffer = ""
        self.refresh_board()

    def action_reset_row(self) -> None:
        if self.paused:
            return
        r, _ = self.cursor
        self.grid[r] = list(self.original_rows[r])
        self.selected = None
        self.refresh_board()

    def action_toggle_pause(self) -> None:
        if self.solved or self.start_time is None:
            return  # nothing to pause before the puzzle has started
        if self.paused:
            # Resume: shift start_time forward by however long we were
            # paused, so elapsed time picks up exactly where it left off —
            # mirrors the web version's startedAt/pausedAt reconciliation.
            now = time.monotonic()
            self.start_time += now - self.paused_at
            self.paused = False
            self.paused_at = None
        else:
            self.paused = True
            self.paused_at = time.monotonic()
            self.selected = None
            self.typing_row = None
            self.type_buffer = ""
            self.error_message = None
        self.refresh_board()

    def action_toggle_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_show_about(self) -> None:
        self.push_screen(AboutScreen())

    def action_open_wordwrangler(self) -> None:
        webbrowser.open(WORDWRANGLER_URL)

    def action_reset_all(self) -> None:
        if self.paused:
            return
        self.grid = [list(r) for r in self.original_rows]
        self.selected = None
        self.start_time = None
        self.elapsed = 0.0
        self.refresh_board()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play WordWrangler (wordwrangler.us) from the terminal.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--date", help="Play the daily puzzle for this date (YYYY-MM-DD). Default: today.")
    group.add_argument("--id", type=int, help="Play a specific puzzle by its numeric id.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.id is not None:
            puzzle = fetch_puzzle(args.id)
        elif args.date:
            puzzle = fetch_puzzle_for_date(args.date)
        else:
            puzzle = fetch_today_puzzle()
        wordlist = load_wordlist()
    except PuzzleFetchError as exc:
        raise SystemExit(f"error: {exc}")

    WordWranglerApp(puzzle, wordlist).run()


if __name__ == "__main__":
    main()
