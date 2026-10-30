# Lab Runbook — executing and submitting from the lab

**Every submitted result is produced on the BITS MLOps lab VM** by following this runbook.
`scripts/run_pipeline.py` records the host name, OS, Python and package versions, LLM
provider/model and git commit of each run in `reports/run/run_summary.md` as proof of where
it was executed.

---

## 0. Prerequisites (check once)

```bash
python3 --version      # system python3 on the lab VM is 3.9 - too old; we use conda's 3.12 below
git --version
curl -s -o /dev/null -w "%{http_code}\n" https://generativelanguage.googleapis.com/   # any 3-digit code = reachable
```

You also need a **Gemini API key** (free tier): create it at <https://aistudio.google.com/apikey>
while signed in to your Google account. Treat it like a password.

## 1. Get the code

```bash
cd ~/workspace
git clone https://github.com/gsivaram/2025ae05220MLOpsAssignment2.git
cd 2025ae05220MLOpsAssignment2
```

Already cloned in an earlier session? `cd ~/workspace/2025ae05220MLOpsAssignment2 && git pull`.

## 2. Create the environment

Build the venv from conda's Python 3.12, then leave conda (the venv is self-contained):

```bash
conda activate base && python --version     # must be 3.12.x
python -m venv .venv
conda deactivate
source .venv/bin/activate && python --version   # still 3.12.x, prompt shows (.venv)
pip install --upgrade pip
pip install -r requirements.txt
```

Every new terminal: `cd ~/workspace/2025ae05220MLOpsAssignment2 && source .venv/bin/activate`.

Behind a proxy: add `--proxy http://host:port` to the `pip` commands and `export HTTPS_PROXY=http://host:port`
before running the notebook.

## 3. Provide the API key (never committed)

```bash
cp .env.example .env
nano .env                     # replace paste-your-key-here with your key, save (Ctrl+O, Enter, Ctrl+X)
chmod 600 .env                # readable only by you
git check-ignore .env         # must print ".env" -> git will never pick it up
```

`.env` lives inside `~/workspace`, so it survives the lab VM being recycled between sessions.
Alternative without a file: `read -s GEMINI_API_KEY && export GEMINI_API_KEY` (paste, Enter).

## 4. Run the full pipeline (one command)

```bash
python scripts/run_pipeline.py --fresh
```

`--fresh` empties the local MLflow store first, so the experiment and the Prompt Registry show
exactly one clean set of runs and prompt versions 1–3.

| Step | What it does | Time |
|---|---|---|
| lint | ruff static checks on `scripts/` | <1 s |
| plan | redraws `docs/phase_plan.png` | ~2 s |
| notebook | executes the notebook in place: Task 1 (5 calls), Task 2 (cost), Task 3 (register v1–v3, 15 calls, MLflow runs + evaluation, `production` alias) | ~3–5 min (6 s pause between calls for the free-tier rate limit) |
| export | writes `reports/EduAssist_LLMOps_Assignment2.html` | ~5 s |
| verify | checks both CSVs, the MLflow runs/metrics, prompt versions + alias, and scans all outputs for the API key | ~5 s |

Expected end: `VERIFY PASSED` then `PIPELINE PASSED`.

If a step fails, read `reports/run/<step>.log`, fix, then resume with
`python scripts/run_pipeline.py --from <step>`. HTTP 429 lines during the notebook step are
rate-limit retries and are handled automatically; a run only fails if a request still fails
after 5 attempts (then wait a minute and re-run with `--fresh`).

## 5. Take screenshots (save into `screenshots/`)

**Terminal evidence**

| File | What to capture |
|---|---|
| `lab_00_environment.png` | top of the runner output — Host / OS / Python / commit / provider / model / `API key set (hidden)` |
| `lab_01_pipeline_passed.png` | the verify checks, `VERIFY PASSED` and `PIPELINE PASSED` lines |

**MLflow UI** — start it from the repo root, then open <http://127.0.0.1:5000> in Firefox:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

| File | Where |
|---|---|
| `mlflow_01_experiment_runs.png` | **Experiments** → `eduassist_llmops_assignment` → Runs table. Add columns `avg_latency_seconds`, `avg_input_tokens`, `avg_output_tokens`, `avg_cost_per_request`, `valid_json` |
| `mlflow_02_metrics_compare.png` | tick `prompt_v1_basic`, `prompt_v2_structured`, `prompt_v3_json` → **Compare** → metrics table / bar charts of the five metrics |
| `mlflow_03_run_overview.png` | open `prompt_v3_json` → Overview: params (`prompt_uri`, model, prices), metrics, linked prompt version |
| `mlflow_04_evaluation.png` | same run → **Traces** / **Evaluations** tab: the five responses with `valid_json`, `schema_valid`, `keyword_coverage` assessments |
| `mlflow_05_prompt_registry.png` | **Prompts** → `eduassist-academic-qa` → version list v1, v2, v3 with commit messages |
| `mlflow_06_prompt_diff.png` | in the prompt page select version 2 and 3 → **Compare** (side-by-side diff). Optional second shot for v1 vs v2 |
| `mlflow_07_production_alias.png` | the promoted version showing alias **production** (and tag `status=production`) |
| `mlflow_08_promotion_run.png` *(optional)* | `promotion_decision` run → Artifacts → `plots/task3_prompt_comparison.png` |

Stop the UI with Ctrl+C.

## 6. Commit the lab results

```bash
git add -A
git status                    # .env must NOT be listed
git commit -m "Lab run: notebook outputs, CSVs, run summary and MLflow screenshots"
git push
```

This commits the executed notebook, `outputs/` (CSVs + figures), `reports/run/`, the HTML export
and the screenshots. `mlflow.db` / `mlruns/` are intentionally not committed — they are regenerated
by the notebook step. When prompted, username = your GitHub user, password = a **Personal Access
Token** (never your GitHub password).
