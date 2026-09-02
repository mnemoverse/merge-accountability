# Degenerate-baseline grading experiment

The one execution in the paper (Section: The degenerate baseline, executed): 78 LongMemEval
knowledge-update questions, oracle setting, two conditions (invalidated vs store-both-rank-newer),
reader and grader gpt-4o-2024-08-06 at temperature 0, grader prompt verbatim from the benchmark.

Result: invalidated 63/78 (80.8%), store-both 61/78 (78.2%); 22 discordant (12 vs 10),
exact McNemar two-sided p = 0.83.

Stratified by question class (`question_classes.csv`): on the 61 current-value questions
invalidated scores 59 vs 48, discordances 11:0 (p = 0.0010); on the 17 lookback questions
(those asking for the superseded value) invalidated scores 4 vs 13, discordances 1:10
(p = 0.0117). The aggregate null is a cancellation of two opposite, individually
significant effects. `leniency_flags.csv` re-examines all 156 graded answers for the
grader's lenient clause: it was load-bearing in at most 1 of 156.

Prompts and timestamps: both prompts live in `run.py`, the reader system prompt in
`READER_SYSTEM` and the grader template in `GRADER_TEMPLATE`; the reader's user message is
assembled in `run_question`. Session timestamps were shown to the reader in both conditions
by the same `render_session` helper, which prefixes every session with
`[Conversation on <date>]`, and both conditions append the same `[Current date: <date>]`
line before the question. The conditions differ only in how many sessions that helper
renders: `invalidated` passes the newer evidence session alone (one dated header),
`store_both` concatenates newer + older (two dated headers). The store-both reader
therefore has explicit dates as well as ordering as a recency cue, though it does not
reliably use them: on question `6071bd76` it reports the two values in presentation order,
contradicting the dates it was shown.

Provenance note: `run.py` writes its outputs to `results/`; the committed artifacts were
moved one level up into this directory after the run.

Files: run.py (harness), answers_*.jsonl (per-question reader answers + grader verdicts),
summary.json (config + dates), question_classes.csv (per-question class annotation with
both evidence values and both verdicts), leniency_flags.csv (per-answer leniency
adjudication). Re-grade with any judge you prefer; the reader answers are committed.
