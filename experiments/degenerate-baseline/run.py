#!/usr/bin/env python3
"""Degenerate-baseline experiment for "Merge Without Measure" (M1 option b).

Question: on LongMemEval's knowledge-update subset (78 questions, 2 evidence
sessions each), does the reference grader distinguish a store that correctly
invalidated the old fact from the degenerate policy "store both, rank the
newer first"?

Two conditions per question, identical reader and grader:
  invalidated : reader sees ONLY the newer evidence session
                (simulates a store that expired the superseded fact)
  store_both  : reader sees BOTH evidence sessions, newer FIRST
                (the degenerate policy the paper describes)

Reader and grader are both pinned snapshots (gpt-4o-2024-08-06, temperature 0).
The knowledge-update grader prompt is the VERBATIM template from LongMemEval
src/evaluation/evaluate_qa.py::get_anscheck_prompt (task == 'knowledge-update'),
re-fetched from github.com/xiaowu0162/LongMemEval @ main on 2026-08-16.

Outputs (committed as artifacts):
  results/answers_<condition>.jsonl   per-question reader answers + grader verdicts
  results/summary.json                accuracies + config + dates
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = Path(
    "/Volumes/SSD960GB/Projects/mnemoverse/mnemoverse-core/experiments/benchmarks/"
    "longmemeval/data/longmemeval_oracle.json"
)
ENV_FILES = [
    Path("/Volumes/SSD960GB/Projects/mnemoverse/mnemoverse-core/.env"),
    Path("/Volumes/SSD960GB/Projects/mnemoverse/mnemoverse-research-agent/.env"),
    Path("/Volumes/SSD960GB/Projects/mnemoverse/mnemoverse-chat/services/agents/.dev.vars"),
]

MODEL = "gpt-4o-2024-08-06"
CONCURRENCY = 6

GRADER_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, "
    "answer no. If the response contains some previous information along with an "
    "updated answer, the response should be considered as correct as long as the "
    "updated answer is the required answer.\n\n"
    "Question: {question}\n\n"
    "Correct Answer: {answer}\n\n"
    "Model Response: {response}\n\n"
    "Is the model response correct? Answer yes or no only."
)

READER_SYSTEM = (
    "You are a helpful assistant with access to the user's past conversation "
    "history. Answer the question based on the conversation history provided. "
    "Answer concisely."
)


def load_env_keys() -> list[str]:
    keys: list[str] = []
    env = os.getenv("OPENAI_API_KEY", "")
    if env:
        keys.append(env)
    for ef in ENV_FILES:
        if not ef.exists():
            continue
        for line in ef.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
                if k and k not in keys:
                    keys.append(k)
                break
    if not keys:
        sys.exit("OPENAI_API_KEY not found in env or known env files")
    return keys


def render_session(date: str, turns: list[dict]) -> str:
    lines = [f"[Conversation on {date}]"]
    for t in turns:
        role = t.get("role", "?").upper()
        lines.append(f"{role}: {t.get('content', '')}")
    return "\n".join(lines)


def build_conditions(q: dict) -> dict[str, str]:
    """Return {condition_name: rendered_history} for one KU question."""
    dates = q["haystack_dates"]
    sessions = q["haystack_sessions"]
    if len(sessions) != 2:
        raise ValueError(f"{q['question_id']}: expected 2 sessions, got {len(sessions)}")
    order = sorted(range(2), key=lambda i: dates[i])  # chronological
    older_i, newer_i = order[0], order[1]
    newer = render_session(dates[newer_i], sessions[newer_i])
    older = render_session(dates[older_i], sessions[older_i])
    return {
        # correct invalidation: superseded session is gone from the store
        "invalidated": newer,
        # degenerate policy: both kept, newer ranked first
        "store_both": newer + "\n\n" + older,
    }


async def chat(client, messages, sem) -> str:
    async with sem:
        r = await client.chat.completions.create(
            model=MODEL, temperature=0, messages=messages
        )
        return (r.choices[0].message.content or "").strip()


async def run_question(client, sem, q: dict, condition: str, history: str) -> dict:
    question = q["question"]
    qdate = q.get("question_date", "")
    reader_user = (
        f"{history}\n\n[Current date: {qdate}]\n\nQuestion: {question}"
    )
    answer_text = await chat(
        client,
        [
            {"role": "system", "content": READER_SYSTEM},
            {"role": "user", "content": reader_user},
        ],
        sem,
    )
    grader_prompt = GRADER_TEMPLATE.format(
        question=question, answer=q["answer"], response=answer_text
    )
    verdict_raw = await chat(client, [{"role": "user", "content": grader_prompt}], sem)
    verdict = verdict_raw.lower().startswith("yes")
    return {
        "question_id": q["question_id"],
        "condition": condition,
        "question": question,
        "gold_answer": q["answer"],
        "reader_answer": answer_text,
        "grader_raw": verdict_raw,
        "correct": verdict,
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="run only first N questions (smoke)")
    args = ap.parse_args()

    from openai import AsyncOpenAI  # deferred so --help works without the package

    data = json.load(open(ORACLE))
    ku = [q for q in data if q.get("question_type") == "knowledge-update"]
    if args.limit:
        ku = ku[: args.limit]
    print(f"knowledge-update questions: {len(ku)}", flush=True)

    # Probe keys until one has quota (a 1-token call), then use it for the run.
    keys = load_env_keys()
    client = None
    for i, k in enumerate(keys):
        probe = AsyncOpenAI(api_key=k)
        try:
            await probe.chat.completions.create(
                model=MODEL, max_tokens=1, messages=[{"role": "user", "content": "hi"}]
            )
            client = probe
            print(f"using key #{i + 1} of {len(keys)}", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"key #{i + 1}: {type(e).__name__}", flush=True)
    if client is None:
        sys.exit("no OpenAI key with available quota")
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = []
    for q in ku:
        for condition, history in build_conditions(q).items():
            tasks.append(run_question(client, sem, q, condition, history))
    results = await asyncio.gather(*tasks)

    outdir = HERE / "results"
    outdir.mkdir(exist_ok=True)
    by_cond: dict[str, list[dict]] = {}
    for r in results:
        by_cond.setdefault(r["condition"], []).append(r)

    summary: dict = {
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "temperature": 0,
        "n_questions": len(ku),
        "grader": "LongMemEval get_anscheck_prompt, knowledge-update branch, verbatim",
        "conditions": {},
    }
    for cond, rows in sorted(by_cond.items()):
        rows.sort(key=lambda r: r["question_id"])
        path = outdir / f"answers_{cond}.jsonl"
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        acc = sum(r["correct"] for r in rows) / len(rows)
        summary["conditions"][cond] = {
            "n": len(rows),
            "correct": sum(r["correct"] for r in rows),
            "accuracy": round(acc, 4),
        }
        print(f"{cond}: {sum(r['correct'] for r in rows)}/{len(rows)} = {acc:.3f}", flush=True)

    with open(outdir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("written:", outdir, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
