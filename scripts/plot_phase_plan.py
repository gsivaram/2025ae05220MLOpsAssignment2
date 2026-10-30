"""Draw the phase-wise approach of Assignment 2 as a single figure (docs/phase_plan.png).

Usage (from the repo root):
    python scripts/plot_phase_plan.py

Each phase is one box: what is done, what it produces, the marks it carries and where
it runs. Arrows show the order; the dashed band marks the phases executed in the lab.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only - no display needed in the lab VM
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "phase_plan.png"

# (phase id, title, activities, outputs, marks label, accent colour)
PHASES = [
    ("Phase 0", "Setup & governance",
     ["Git repo + .gitignore", "Pinned requirements (Py 3.12)",
      "API key via .env / env var", "Questions + pricing config"],
     ["requirements.txt, .env.example", "docs/phase_plan.png"], "foundation", "#6b7280"),
    ("Phase 1", "Task 1 - LLM call & latency",
     ["Gemini API call per question", "perf_counter timing + status",
      "Retry / rate-limit handling", "mean/median/min/max/std"],
     ["Latency table + stats", "Slowest-request analysis"], "2 marks", "#2563eb"),
    ("Phase 2", "Task 2 - Tokens & cost",
     ["usage_metadata -> tokens", "Input / output cost formula",
      "Monthly projection x 10,000", "What-if cost optimisation"],
     ["latency_tokens_cost.csv", "Cost chart + recommendation"], "3 marks", "#0891b2"),
    ("Phase 3", "Task 3 - Prompt versioning",
     ["Register v1, v2, v3 (commit msgs)", "Run 3 x 5 questions, log runs",
      "valid_json scorer (MLflow eval)", "Compare -> alias 'production'"],
     ["prompt_evaluation_results.csv", "MLflow runs, registry, diff"], "5 marks", "#7c3aed"),
    ("Phase 4", "Lab execution & evidence",
     ["git pull on BITS lab VM", "run_pipeline.py (one command)", "verify_outputs.py checks", "MLflow UI screenshots"],
     ["reports/run/run_summary.md", "screenshots/*.png"], "proof of run", "#059669"),
    ("Phase 5", "Report & submission",
     ["Comparison + justification", "Report DOCX -> PDF", "README reproduction steps", "Submission ZIP"],
     ["Report PDF, README", "Submission ZIP"], "deliverables", "#d97706"),
]

BOX_W, BOX_H = 4.2, 4.6
GAP_X, GAP_Y = 0.9, 1.2
COLS = 3


def box_origin(i: int) -> tuple[float, float]:
    """Top-left corner of phase box i in a 3-column "snake" grid.

    Row 0 runs left-to-right (phases 0-2), row 1 right-to-left (phases 3-5), so that
    phases 1-4 - the ones executed in the lab - form one contiguous 2x2 block.
    """
    row, col = divmod(i, COLS)
    if row % 2:
        col = COLS - 1 - col
    return col * (BOX_W + GAP_X), -row * (BOX_H + GAP_Y)


def draw_phase(ax, i: int, phase) -> None:
    """Draw one phase card: coloured header, activity bullets, outputs, marks badge."""
    pid, title, acts, outs, marks, colour = phase
    x, y = box_origin(i)
    ax.add_patch(FancyBboxPatch((x, y - BOX_H), BOX_W, BOX_H, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc="white", ec=colour, lw=2))
    ax.add_patch(FancyBboxPatch((x, y - 0.95), BOX_W, 0.95, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=colour, ec=colour, lw=2))
    ax.text(x + 0.2, y - 0.33, pid, color="white", fontsize=10, fontweight="bold", va="center")
    ax.text(x + 0.2, y - 0.68, title, color="white", fontsize=11.5, fontweight="bold", va="center")
    ax.text(x + BOX_W - 0.2, y - 0.33, marks, color="white", fontsize=9, va="center", ha="right", style="italic")
    ty = y - 1.3
    for a in acts:
        ax.text(x + 0.25, ty, f"• {a}", fontsize=9, va="center", color="#111827")
        ty -= 0.42
    ty -= 0.12
    ax.text(x + 0.25, ty, "Outputs", fontsize=8.5, fontweight="bold", color=colour, va="center")
    ty -= 0.4
    for o in outs:
        ax.text(x + 0.25, ty, o, fontsize=8.5, family="monospace", va="center", color="#374151")
        ty -= 0.38


def draw_arrow(ax, i: int, j: int) -> None:
    """Arrow from phase i to phase j (right within a row, down-and-back between rows)."""
    xi, yi = box_origin(i)
    xj, yj = box_origin(j)
    if yi != yj:  # row change: straight down
        start, end = (xi + BOX_W / 2, yi - BOX_H), (xj + BOX_W / 2, yj)
    elif xj > xi:  # left-to-right
        start, end = (xi + BOX_W, yi - BOX_H / 2), (xj, yj - BOX_H / 2)
    else:  # right-to-left
        start, end = (xi, yi - BOX_H / 2), (xj + BOX_W, yj - BOX_H / 2)
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, lw=1.6, color="#9ca3af"))


def main() -> None:
    fig, ax = plt.subplots(figsize=(15, 11.2))
    for i, phase in enumerate(PHASES):
        draw_phase(ax, i, phase)
    for i in range(len(PHASES) - 1):
        draw_arrow(ax, i, i + 1)

    # Dashed band: phases 1-4 (columns 1-2, both rows) are executed on the BITS lab VM by scripts/run_pipeline.py
    x1, y1 = box_origin(1)
    band_w, band_h = 2 * BOX_W + GAP_X + 0.6, 2 * BOX_H + GAP_Y + 0.6
    ax.add_patch(FancyBboxPatch((x1 - 0.3, y1 - band_h + 0.3), band_w, band_h,
                                boxstyle="round,pad=0,rounding_size=0.3", fc="none", ec="#059669", lw=1.2, ls="--"))
    ax.text(x1 + 2 * BOX_W + GAP_X + 0.25, y1 + 0.45, "executed in the MLOps lab (run_pipeline.py)", ha="right",
            fontsize=9, color="#059669", style="italic")

    ax.set_title("EduAssist AI - LLMOps Assignment 2: phase-wise approach", fontsize=15, fontweight="bold",
                 loc="left", pad=18)
    ax.text(0, 1.0, "Each phase = one Git commit; Tasks 1-3 run in one notebook, executed and evidenced on the lab VM.",
            fontsize=10, color="#4b5563")
    ax.set_xlim(-0.4, COLS * BOX_W + (COLS - 1) * GAP_X + 0.4)
    ax.set_ylim(-2 * BOX_H - GAP_Y - 0.6, 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
