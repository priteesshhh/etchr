# Decisions

## Benchmark first, not a checker
MiniEval (MIT) already ships a write-time gate (STORE / REJECT / REVIEW). Its test
corpus is small and it is not run against real stores. etchr's contribution is the
labeled set; checkers, including MiniEval, are baselines scored on it.

## Labels: supported / unsupported / contradicted
`supported` and `contradicted` must cite evidence turns, because they are claims
about specific text. `unsupported` may cite none. Unlabeled cases (`label: null`)
are valid on disk and excluded from scoring.

## Free-text candidate memories, not triples
mem0 stores free text. Forcing subject/predicate/value would add an extraction
step with its own errors. Revisit only if a detector needs structure.

## Humans label, models do not
Labels are written by a person via `etchr label`. An LLM-written gold set would make
LLM-judge scores circular.

## Python 3.12 pinned locally, >=3.11 supported
Store SDKs (mem0, Graphiti) lag the newest Python. CI tests 3.11 and 3.12.
