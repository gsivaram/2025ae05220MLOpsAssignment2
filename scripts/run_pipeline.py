"""Run the whole assignment from a clean checkout and record proof of execution.

Usage (from the repo root, with the virtual environment active and GEMINI_API_KEY set):
    python scripts/run_pipeline.py --fresh          # final run: start from an empty MLflow store
    python scripts/run_pipeline.py                  # all steps, keep existing MLflow runs
    python scripts/run_pipeline.py --from export    # resume from a step
    python scripts/run_pipeline.py --only verify    # one step

Each step's output is streamed to the console and saved to reports/run/<step>.log;
reports/run/run_summary.md records host, OS, Python, package versions, provider/model,
timings and pass/fail for every step. The run stops at the first failing step.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "reports" / "run"
PY = sys.executable
NOTEBOOK = "notebooks/EduAssist_LLMOps_Assignment2.ipynb"

STEPS: list[tuple[str, str, list[str]]] = [
    ("lint", "Static checks (ruff)", [PY, "-m", "ruff", "check", "scripts"]),
    ("plan", "Draw phase plan", [PY, "scripts/plot_phase_plan.py"]),
    ("notebook", "Execute notebook: Tasks 1-3 (LLM calls + MLflow)",
     [PY, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
      "--ExecutePreprocessor.timeout=1800", NOTEBOOK]),
    ("export", "Export executed notebook to HTML",
     [PY, "-m", "jupyter", "nbconvert", "--to", "html", "--output-dir", "reports", NOTEBOOK]),
    ("verify", "Verify deliverables, MLflow registry/alias, secret scan", [PY, "scripts/verify_outputs.py"]),
]
STEP_NAMES = [s[0] for s in STEPS]
PACKAGES = ["mlflow", "google-genai", "openai", "anthropic", "pandas", "numpy", "matplotlib", "nbconvert"]
KEY_VARS = {"gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"], "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"], "ollama": []}


def load_env_file() -> None:
    """Load .env (git-ignored) so the key check and child processes see the same variables."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


def environment() -> dict[str, str]:
    """Host, OS, interpreter, git commit, LLM configuration and package versions of this run."""
    def version(pkg: str) -> str:
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return "not installed"

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    provider = os.getenv("LLM_PROVIDER", "gemini")
    return {
        "Host": socket.gethostname(),
        "OS": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "Python": f"{platform.python_version()} at {PY}",
        "Git commit": commit,
        "LLM provider": provider,
        "LLM model": os.getenv("LLM_MODEL", "gemini-3.5-flash-lite" if provider == "gemini" else "(provider default)"),
        "API key": "set (hidden)" if any(os.getenv(k) for k in KEY_VARS.get(provider, [])) else "not set",
        "Started": datetime.now().astimezone().isoformat(timespec="seconds"),
        **{f"pkg {p}": version(p) for p in PACKAGES},
    }


def run_step(name: str, title: str, cmd: list[str]) -> tuple[bool, float]:
    """Run one step, tee its output to reports/run/<name>.log, return (passed, seconds)."""
    print(f"\n{'=' * 78}\n>> [{name}] {title}\n  $ {' '.join(Path(c).name if c == PY else c for c in cmd)}\n{'=' * 78}",
          flush=True)
    log_path = RUN_DIR / f"{name}.log"
    t0 = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log:
        # UTF-8 everywhere, and this interpreter's bin dir first on PATH so the Jupyter
        # kernel resolves to the same virtual environment (not the system python3).
        child_env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "MLFLOW_DISABLE_AGENT_HINT": "1",
                     "PATH": os.pathsep.join([str(Path(PY).parent), os.environ.get("PATH", "")])}
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", env=child_env)
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        proc.wait()
    elapsed = time.perf_counter() - t0
    ok = proc.returncode == 0
    status = "passed" if ok else f"FAILED (exit {proc.returncode})"
    print(f"{'[OK]' if ok else '[FAIL]'} [{name}] {status} in {elapsed:.1f}s - log: {log_path.relative_to(ROOT)}",
          flush=True)
    return ok, elapsed


def write_summary(env: dict[str, str], results: list[tuple[str, str, bool, float]]) -> Path:
    """Write reports/run/run_summary.md - the execution evidence for the report."""
    lines = ["# Pipeline run summary", "", "| | |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in env.items()]
    lines += ["", "| Step | Description | Result | Time |", "|---|---|---|---|"]
    lines += [f"| {n} | {t} | {'PASS' if ok else '**FAIL**'} | {s:.1f}s |" for n, t, ok, s in results]
    path = RUN_DIR / "run_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def reset_mlflow_store() -> None:
    """--fresh: remove the local MLflow store so the experiment shows exactly one set of runs."""
    for target in (ROOT / "mlflow.db", ROOT / "mlruns"):
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    print("MLflow store reset (mlflow.db, mlruns/)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--from", dest="start", choices=STEP_NAMES, help="start at this step")
    group.add_argument("--only", choices=STEP_NAMES, help="run just this step")
    parser.add_argument("--fresh", action="store_true", help="delete mlflow.db and mlruns/ before running")
    args = parser.parse_args()

    if sys.version_info < (3, 10):  # noqa: UP036 - friendly message for old lab interpreters
        print(f"Python 3.10+ required, found {platform.python_version()}", file=sys.stderr)
        return 2

    load_env_file()
    steps = STEPS
    if args.only:
        steps = [s for s in STEPS if s[0] == args.only]
    elif args.start:
        steps = STEPS[STEP_NAMES.index(args.start):]

    env = environment()
    if any(s[0] == "notebook" for s in steps) and env["API key"] == "not set" and env["LLM provider"] != "ollama":
        print(f"No API key for provider '{env['LLM provider']}'. Put it in .env (cp .env.example .env) "
              "or export GEMINI_API_KEY=... and re-run.", file=sys.stderr)
        return 2
    if args.fresh:
        reset_mlflow_store()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    print("Environment:\n" + "\n".join(f"  {k:<18} {v}" for k, v in env.items()))

    results = []
    for name, title, cmd in steps:
        ok, elapsed = run_step(name, title, cmd)
        results.append((name, title, ok, elapsed))
        if not ok:
            break

    summary = write_summary(env, results)
    failed = [r for r in results if not r[2]]
    print(f"\n{'=' * 78}")
    print(f"{'PIPELINE FAILED at step ' + failed[0][0] if failed else 'PIPELINE PASSED'} - "
          f"summary: {summary.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
