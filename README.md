# etchr

**Status: experimental. Nothing is scored yet.**

etchr is a hand-labeled benchmark for one question: when an LLM memory store
writes a fact, does the conversation actually support it? Each case is a short
conversation plus a candidate memory, labeled `supported`, `unsupported` or
`contradicted` by a human, and grouped by failure type: misattribution,
hypotheticals, negation, sarcasm, quoting, over-generalization, temporal drift
and prompt injection. Write-time checkers are scored against those labels.

Prior work: MiniEval (MIT, linked from mem0 issue #7283) already implements a
write-time faithfulness gate for agent memory and is the planned first baseline.
etchr's aim is an independent, labeled test set, not another gate.

Known limitation: a support check alone cannot catch injected instructions,
because injected text *is* in the conversation. The `injection` cases exist to
measure that gap, not to claim it is solved.

## Use

```
uv sync
uv run etchr status          # how many cases are labeled
uv run etchr label           # label unlabeled cases one by one
uv run pytest
```

License: MIT.
