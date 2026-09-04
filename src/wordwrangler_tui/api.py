"""Client for WordWrangler's (unauthenticated) public Firestore REST API.

wordwrangler.us is a static React app; it reads the daily puzzle straight out
of Firestore with a public API key and validates guesses client-side against
a plain word list. There's no official API, but the same reads it performs
are public, so we just replay them here.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FIRESTORE_BASE = (
    "https://firestore.googleapis.com/v1/projects/descramble-game/databases/(default)/documents"
)
API_KEY = "AIzaSyBgSPN5kEcmByhKWHHBKOS9ToTRhSUNcDA"
WORDLIST_URL = "https://wordwrangler.us/words_five.txt"
CACHE_DIR = Path.home() / ".cache" / "wordwrangler-tui"
BUNDLED_WORDLIST = Path(__file__).parent / "words_five.txt"

USER_AGENT = "wordwrangler-tui (https://github.com/msabramo/wordwrangler-tui)"

# The earliest date with a dailyPuzzle assignment (found by binary-searching
# the Firestore endpoint) — WordWrangler's actual launch date. Puzzles also
# exist for a handful of days beyond "today" (pre-generated ahead of time),
# but that window isn't a stable contract, so we only advertise up to today.
LAUNCH_DATE = date(2026, 4, 27)


class PuzzleFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Puzzle:
    puzzle_id: int
    rows: list[str]  # 5 scrambled 5-letter strings, one per grid row


def _get_json(path: str) -> dict | None:
    """Fetch a Firestore document. Returns None if it doesn't exist (404)."""
    url = f"{FIRESTORE_BASE}/{path}?key={API_KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise PuzzleFetchError(f"Couldn't reach Firestore: {exc}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PuzzleFetchError(f"Couldn't reach Firestore: {exc}") from exc


def _date_range_message(day: str) -> str:
    return (
        f"No puzzle for {day}. WordWrangler's daily puzzles run from "
        f"{LAUNCH_DATE.isoformat()} through today ({date.today().isoformat()})."
    )


def fetch_puzzle_id_for_date(day: str) -> int:
    doc = _get_json(f"dailyPuzzle/{day}")
    fields = doc.get("fields") if doc else None
    if not fields:
        raise PuzzleFetchError(_date_range_message(day))
    return int(fields["puzzleId"]["integerValue"])


def fetch_puzzle(puzzle_id: int) -> Puzzle:
    doc = _get_json(f"puzzles/{puzzle_id}")
    fields = doc.get("fields") if doc else None
    if not fields:
        raise PuzzleFetchError(f"No puzzle found with id {puzzle_id}.")
    values = fields["scrambled"]["arrayValue"]["values"]
    rows = [v["stringValue"] for v in values]
    return Puzzle(puzzle_id=puzzle_id, rows=rows)


def fetch_today_puzzle() -> Puzzle:
    today = date.today().isoformat()
    puzzle_id = fetch_puzzle_id_for_date(today)
    return fetch_puzzle(puzzle_id)


def fetch_puzzle_for_date(day: str) -> Puzzle:
    puzzle_id = fetch_puzzle_id_for_date(day)
    return fetch_puzzle(puzzle_id)


def load_wordlist() -> set[str]:
    """Fetch the site's live 5-letter word list, caching a local copy for offline use."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "words_five.txt"
    try:
        req = urllib.request.Request(WORDLIST_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            cache_file.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError):
        pass  # fall back to whatever's cached (or bundled) below

    for source in (cache_file, BUNDLED_WORDLIST):
        if source.exists():
            return {
                w.strip().lower() for w in source.read_text().splitlines() if w.strip()
            }
    raise PuzzleFetchError("No word list available (fetch failed and no cache/bundle found).")
