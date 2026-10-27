import json

from etchr.cli import label, save_cases, status
from etchr.schema import Label, load_cases


def write_cases(path, n=2):
    lines = []
    for i in range(1, n + 1):
        lines.append(json.dumps({
            "id": f"negation-{i:03d}",
            "failure_type": "negation",
            "conversation": [
                {"turn_id": "t1", "speaker": "user", "text": "I don't eat meat."},
                {"turn_id": "t2", "speaker": "assistant", "text": "Noted."},
            ],
            "candidate_memory": "User eats meat.",
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scripted(answers):
    it = iter(answers)
    return lambda _prompt: next(it)


def test_label_saves_each_answer(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path)
    n = label(path, ask=scripted(["c", "t1", "clear negation", "u", "", ""]), out=lambda _: None)
    assert n == 2
    first, second = load_cases(path)
    assert first.label is Label.CONTRADICTED and first.evidence_turn_ids == ["t1"]
    assert first.notes == "clear negation"
    assert second.label is Label.UNSUPPORTED and second.evidence_turn_ids == []


def test_quit_keeps_earlier_labels(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path)
    label(path, ask=scripted(["c", "t1", "", "q"]), out=lambda _: None)
    first, second = load_cases(path)
    assert first.is_labeled and not second.is_labeled


def test_bad_input_reprompts(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path, n=1)
    # unknown key, unknown turn id, supported with no evidence, then a valid answer
    answers = ["x", "s", "t9", "s", "", "s", "t1", ""]
    label(path, ask=scripted(answers), out=lambda _: None)
    (case,) = load_cases(path)
    assert case.label is Label.SUPPORTED and case.evidence_turn_ids == ["t1"]


def test_skip_leaves_case_unlabeled(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path, n=1)
    assert label(path, ask=scripted(["k"]), out=lambda _: None) == 0
    assert not load_cases(path)[0].is_labeled


def test_relabel_run_skips_labeled(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path, n=1)
    label(path, ask=scripted(["u", "", ""]), out=lambda _: None)
    # Nothing left to ask; any prompt would raise StopIteration.
    assert label(path, ask=scripted([]), out=lambda _: None) == 0


def test_save_is_atomic_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "cases.jsonl"
    write_cases(path, n=1)
    before = path.read_text(encoding="utf-8")
    cases = load_cases(path)

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr("etchr.cli.os.replace", boom)
    try:
        save_cases(path, cases)
    except OSError:
        pass
    assert path.read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == ["cases.jsonl"]


def test_status_counts(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_cases(path)
    label(path, ask=scripted(["u", "", "", "q"]), out=lambda _: None)
    lines = []
    status(path, out=lines.append)
    assert lines == ["1/2 labeled", "  unsupported: 1"]
