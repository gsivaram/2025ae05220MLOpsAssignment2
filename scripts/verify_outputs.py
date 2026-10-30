"""Check every Assignment 2 deliverable produced by the notebook, and that no secret leaked.

Usage (from the repo root, after the notebook has run):
    python scripts/verify_outputs.py

Checks
  * outputs/latency_tokens_cost.csv      - 5 successful requests, latency/token/cost columns, cost formula
  * outputs/prompt_evaluation_results.csv - v1..v3 with the 5 required metrics, exactly one recommended
  * MLflow experiment eduassist_llmops_assignment - one run per prompt version with the 5 required metrics
  * Prompt Registry - versions 1-3 with commit messages; alias `production` -> the recommended version
  * Secret scan - the API key value appears in no output, notebook, report or MLflow artifact file
Exits non-zero on the first failed group so run_pipeline.py stops.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
EXPERIMENT = "eduassist_llmops_assignment"
PROMPT_NAME = "eduassist-academic-qa"
REQUIRED_METRICS = [
    "avg_latency_seconds", "avg_input_tokens", "avg_output_tokens", "avg_cost_per_request", "valid_json",
]

failures: list[str] = []


def check(ok: bool, message: str) -> None:
    """Print one PASS/FAIL line and remember failures."""
    print(f"  [{'PASS' if ok else 'FAIL'}] {message}")
    if not ok:
        failures.append(message)


def check_latency_csv() -> None:
    """Task 1 + 2 deliverable: per-request latency, tokens and cost."""
    print("latency_tokens_cost.csv")
    df = pd.read_csv(OUT / "latency_tokens_cost.csv")
    need = ["question_id", "prompt_version", "model", "start_time", "end_time", "latency_seconds", "status",
            "input_tokens", "output_tokens", "total_tokens", "input_cost_usd", "output_cost_usd", "total_cost_usd"]
    check(all(c in df.columns for c in need), "has all latency / token / cost columns")
    check(len(df) == 5 and (df["status"] == "success").all(), "5 requests, all successful")
    check((df["latency_seconds"] > 0).all() and (df["input_tokens"] > 0).all() and (df["output_tokens"] > 0).all(),
          "latency and token counts are positive")
    check(((df["input_cost_usd"] + df["output_cost_usd"] - df["total_cost_usd"]).abs() < 1e-12).all(),
          "total cost = input cost + output cost")


def check_results_csv() -> str:
    """Task 3 deliverable: comparison table. Returns the recommended label."""
    print("prompt_evaluation_results.csv")
    df = pd.read_csv(OUT / "prompt_evaluation_results.csv")
    check(list(df["prompt_version"]) == ["v1", "v2", "v3"], "rows v1, v2, v3")
    check(all(m in df.columns for m in REQUIRED_METRICS), "has the 5 required metrics")
    check((df["recommended"] == "Yes").sum() == 1, "exactly one version recommended")
    check(df["valid_json"].between(0, 1).all(), "valid_json is a rate in [0, 1]")
    return str(df.loc[df["recommended"] == "Yes", "prompt_version"].iloc[0])


def check_mlflow(best_label: str) -> None:
    """Experiment runs, prompt versions and the production alias in the MLflow store."""
    import mlflow

    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{ROOT / 'mlflow.db'}"))
    print("MLflow experiment")
    exp = mlflow.get_experiment_by_name(EXPERIMENT)
    check(exp is not None, f"experiment '{EXPERIMENT}' exists")
    if exp is None:
        return
    runs = mlflow.search_runs([exp.experiment_id], output_format="pandas")
    for label in ["v1", "v2", "v3"]:
        r = runs[runs["tags.prompt_label"] == label] if "tags.prompt_label" in runs else runs.iloc[0:0]
        check(len(r) >= 1 and all(f"metrics.{m}" in r and r[f"metrics.{m}"].notna().iloc[0] for m in REQUIRED_METRICS),
              f"run for prompt {label} with the 5 required metrics")
    check((runs.get("tags.stage") == "promotion").any(), "promotion_decision run logged")

    print("Prompt Registry")
    versions = []
    for v in range(1, 50):
        pv = mlflow.genai.load_prompt(PROMPT_NAME, version=v, allow_missing=True, link_to_model=False)
        if pv is None:
            break
        versions.append(pv)
    check(len(versions) >= 3, f"'{PROMPT_NAME}' has versions 1-3 (found {len(versions)})")
    check(all(pv.commit_message for pv in versions), "every version has a commit message")
    prod = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@production", allow_missing=True, link_to_model=False)
    labels = {pv.version: pv.tags.get("label") for pv in versions}
    check(prod is not None and labels.get(prod.version) == best_label,
          f"alias production -> recommended version ({best_label})")


def check_no_secret() -> None:
    """The API key value must not appear in any file that could be submitted or committed."""
    print("Secret scan")
    load_dotenv(ROOT / ".env", override=False)
    keys = [os.environ[k] for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
            if len(os.environ.get(k, "")) >= 12]
    if not keys:
        check(True, "no API key in the environment - nothing to scan for")
        return
    folders = ("outputs", "notebooks", "reports", "mlruns", "screenshots", "docs")
    scan = [p for d in folders for p in (ROOT / d).rglob("*") if p.is_file() and p.stat().st_size < 20_000_000]
    scan += [ROOT / f for f in ("README.md", "LAB_RUNBOOK.md") if (ROOT / f).exists()]
    leaked = [str(p.relative_to(ROOT)) for p in scan if any(k.encode() in p.read_bytes() for k in keys)]
    check(not leaked, f"API key not found in {len(scan)} files" + (f" - LEAKED in {leaked}" if leaked else ""))


def main() -> int:
    check_latency_csv()
    best = check_results_csv()
    check_mlflow(best)
    check_no_secret()
    print(f"\n{'VERIFY PASSED' if not failures else f'VERIFY FAILED ({len(failures)} checks)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
