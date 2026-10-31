# Pipeline run summary

| | |
|---|---|
| Host | ip-10-3-16-133.ap-south-1.compute.internal |
| OS | Linux 5.14.0-503.14.1.el9_5.x86_64 (x86_64) |
| Python | 3.12.9 at /home/s2025ae05220/workspace/2025ae05220MLOpsAssignment2/.venv/bin/python |
| Git commit | a426bfd |
| LLM provider | gemini |
| LLM model | gemini-3.5-flash-lite |
| API key | set (hidden) |
| Started | 2026-10-31T06:26:21+05:30 |
| pkg mlflow | 3.17.2 |
| pkg google-genai | 2.34.0 |
| pkg openai | 3.41.0 |
| pkg anthropic | 2.3.0 |
| pkg pandas | 3.1.0 |
| pkg numpy | 2.5.4 |
| pkg matplotlib | 3.11.2 |
| pkg nbconvert | 7.17.2 |

| Step | Description | Result | Time |
|---|---|---|---|
| lint | Static checks (ruff) | PASS | 0.6s |
| plan | Draw phase plan | PASS | 22.5s |
| notebook | Execute notebook: Tasks 1-3 (LLM calls + MLflow) | PASS | 253.1s |
| export | Export executed notebook to HTML | PASS | 9.7s |
| verify | Verify deliverables, MLflow registry/alias, secret scan | PASS | 9.9s |
