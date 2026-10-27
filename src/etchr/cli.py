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

_LABEL_KEYS = {"s": Label.SUPPORTED, "u": Label.UNSUPPORTED, "c": Label.CONTRADICTED}


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


def _render(case: Case, out: Callable[[str], None]) -> None:
    out("")
    out(f"== {case.id} ({case.failure_type.value}) ==")
    for turn in case.conversation:
        out(f"  [{turn.turn_id}] {turn.speaker}: {turn.text}")
    out(f"  CANDIDATE MEMORY: {case.candidate_memory}")


def label(path: Path, ask: Callable[[str], str] = input, out: Callable[[str], None] = print) -> int:
    """Interactively label unlabeled cases. Returns how many were labeled."""
    cases = load_cases(path)
    done = 0
    for i, case in enumerate(cases):
        if case.is_labeled:
            continue
        _render(case, out)
        while True:
            key = ask("label [s]upported [u]nsupported [c]ontradicted, [k] skip, [q] quit: ").strip().lower()
            if key == "q":
                out(f"Saved. Labeled {done} this session.")
                return done
            if key == "k":
                break
            if key not in _LABEL_KEYS:
                out("  Type s, u, c, k or q.")
                continue
            chosen = _LABEL_KEYS[key]
            valid_ids = {t.turn_id for t in case.conversation}
            evidence = [e for e in ask("evidence turn ids, space-separated (blank for none): ").split() if e]
            bad = [e for e in evidence if e not in valid_ids]
            if bad:
                out(f"  Unknown turn ids {bad}. Try again.")
                continue
            if chosen is not Label.UNSUPPORTED and not evidence:
                out(f"  '{chosen.value}' needs at least one evidence turn. Try again.")
                continue
            note = ask("note (optional): ").strip()
            cases[i] = case.model_copy(update={"label": chosen, "evidence_turn_ids": evidence, "notes": note})
            Case.model_validate(cases[i].model_dump())  # model_copy skips validation
            save_cases(path, cases)
            done += 1
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
