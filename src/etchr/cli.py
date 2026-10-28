"""Command line: ``etchr status`` and ``etchr label``.

``label`` walks the unlabeled cases one at a time and saves after each
answer, so quitting midway never loses work.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from etchr.schema import Case, Label, load_cases

DEFAULT_CASES = Path("data/cases.jsonl")



def save_cases(path: Path, cases: list[Case]) -> None:
    """Write cases atomically: temp file in the same folder, then replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for case in cases:
                fh.write(case.model_dump_json() + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def status(path: Path, out: Callable[[str], None] = print) -> None:
    cases = load_cases(path)
    labeled = [c for c in cases if c.is_labeled]
    out(f"{len(labeled)}/{len(cases)} labeled")
    for label, n in sorted(Counter(c.label.value for c in labeled).items()):
        out(f"  {label}: {n}")


_ANSWERS = {"1": Label.SUPPORTED, "2": Label.CONTRADICTED, "3": Label.UNSUPPORTED}

_QUESTION = (
    "Is the memory true, based ONLY on what the user said?\n"
    "  1 = yes, the user said it\n"
    "  2 = no, the user said the opposite\n"
    "  3 = the user never said it\n"
    "  s = not sure, skip    q = save and quit\n"
    "> "
)


def _render(case: Case, n: int, total: int, out: Callable[[str], None]) -> None:
    out("")
    out(f"--- case {n} of {total} ({case.id}) ---")
    out("Conversation:")
    for line_no, turn in enumerate(case.conversation, start=1):
        out(f"  line {line_no}  {turn.speaker.upper()}: {turn.text}")
    out("")
    out(f"Memory the app wants to save:  \"{case.candidate_memory}\"")
    out("")


def _pick_evidence(case: Case, ask: Callable[[str], str], out: Callable[[str], None]) -> list[str] | None:
    """Return the turn ids that prove the answer. None means the user cancelled."""
    turns = case.conversation
    if len(turns) == 1:
        return [turns[0].turn_id]
    while True:
        raw = ask(f"Which line shows it? (1-{len(turns)}, or b to go back): ").strip().lower()
        if raw == "b":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(turns):
            return [turns[int(raw) - 1].turn_id]
        out(f"  Type a line number from 1 to {len(turns)}.")


def label(path: Path, ask: Callable[[str], str] = input, out: Callable[[str], None] = print) -> int:
    """Interactively label unlabeled cases. Returns how many were labeled."""
    cases = load_cases(path)
    todo = [i for i, c in enumerate(cases) if not c.is_labeled]
    done = 0
    for n, i in enumerate(todo, start=1):
        case = cases[i]
        _render(case, n, len(todo), out)
        while True:
            key = ask(_QUESTION).strip().lower()
            if key == "q":
                out(f"Saved. Labeled {done} this session.")
                return done
            if key == "s":
                break
            if key not in _ANSWERS:
                out("  Type 1, 2, 3, s or q.")
                continue
            chosen = _ANSWERS[key]
            evidence: list[str] = []
            if chosen is not Label.UNSUPPORTED:
                picked = _pick_evidence(case, ask, out)
                if picked is None:
                    continue
                evidence = picked
            cases[i] = Case.model_validate(
                case.model_dump() | {"label": chosen.value, "evidence_turn_ids": evidence}
            )
            save_cases(path, cases)
            done += 1
            out(f"  Saved: {chosen.value}")
            break
    out(f"Done. Labeled {done} this session.")
    return done


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="etchr")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "label"):
        p = sub.add_parser(name)
        p.add_argument("path", nargs="?", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args(argv)
    if args.command == "status":
        status(args.path)
    else:
        label(args.path)


if __name__ == "__main__":
    main()
