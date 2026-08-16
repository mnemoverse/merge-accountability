# Degenerate-baseline grading experiment

The one execution in the paper (Section: The degenerate baseline, executed): 78 LongMemEval
knowledge-update questions, oracle setting, two conditions (invalidated vs store-both-rank-newer),
reader and grader gpt-4o-2024-08-06 at temperature 0, grader prompt verbatim from the benchmark.

Result: invalidated 63/78 (80.8%), store-both 61/78 (78.2%); 22 discordant (12 vs 10),
exact McNemar two-sided p = 0.83.

Files: run.py (harness), answers_*.jsonl (per-question reader answers + grader verdicts),
summary.json (config + dates). Re-grade with any judge you prefer; the reader answers are committed.
