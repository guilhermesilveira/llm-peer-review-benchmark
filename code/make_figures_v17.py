"""Figures for manuscript v17 (15 Oct 2026; changes from v14: corrected human m4 value via data_original/results.json,
and the Fig. 2d human line now marks the approximate human detection rate, 27.0%, reconstructed from the published
per-error percentages, instead of the score share of 23.5%).

Original v14 notes: all text 7 pt or larger (most 8 pt), memory-probe figure with a number in every dot,
simple design schematic (Fig. 1a), colour-blind-safe red-yellow-teal heatmap scale (Fig. 1c, 2b).

Figure 1 = 2004 test papers: (a) design, (b) % of inserted errors found per model, (c) detection per error type.
Figure 2 = trials published in 2026: (a) % found, (b) detection per error type, (c) error-seeded vs unmodified
           manuscripts, (d) sensitivity vs specificity.
Supplementary Fig. 1 = memory probes of Haiku 4.5, Sonnet 5, Opus 5 and Fable 5 (2004 test papers).
Supplementary Fig. 2 = major errors found per review by manuscript (both sets of papers).
Supplementary Fig. 3 = (a) estimated cost and (b) review length against errors found (2026 trials).
(Numbered in the order in which the manuscript cites them.)

Panels b, c (and Fig. 2c) share one row order: human reviewers first, then the models from the fewest to the most
items found in the set of papers shown. Colour marks only the kind of model (dark blue = proprietary, brick red =
open-weight, grey = human reviewers); the two hues pass colour-vision-deficiency checks.

Reads  data/results.json, data_original/results.json, data/results_v2.json, data/cost_estimates_v8.json
Writes figures/Figure1_v14, Figure2_v14, SupplFigure1_v14, SupplFigure2_v14, SupplFigure3_v14 (.png and .pdf)
Run: python3 code/make_figures_v14.py
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
from adjustText import adjust_text

ROOT = os.environ.get("BMJ_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get("BMJ_FIG_OUT", os.path.join(ROOT, "figures"))
os.makedirs(OUT, exist_ok=True)
V = "v17"

R2 = json.load(open(os.path.join(ROOT, "data", "results.json")))            # 2026 trials
R1 = json.load(open(os.path.join(ROOT, "data_original", "results.json")))   # 2004 test papers
V2 = json.load(open(os.path.join(ROOT, "data", "results_v2.json")))
CE = json.load(open(os.path.join(ROOT, "data", "cost_estimates_v8.json")))

ERR_IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "m1", "m2", "m3", "m4", "m5"]
ERR_SHORT = {"M1": "Poor justification", "M2": "Biased allocation", "M3": "No sample size calculation",
             "M4": "Outcome measure validity", "M5": "Not intention-to-treat", "M6": "Poor response rate",
             "M7": "Unjustified conclusions", "M8": "Abstract vs results", "M9": "Inconsistent denominators",
             "m1": "No ethics approval", "m2": "Non-enrolment unexplained", "m3": "Text vs table",
             "m4": "Comparison reversed", "m5": "Hawthorne effect"}
MODELS = ["haiku", "sonnet", "opus", "fable", "gpt54mini", "gpt54", "gpt55",
          "opus55", "gpt61sol", "gpt6luna", "gemini38fl", "kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"]
OPEN = {"kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"}
NAME = {"human": "Human reviewers 2008", "haiku": "Haiku 4.5", "sonnet": "Sonnet 5", "opus": "Opus 5", "fable": "Fable 5",
        "gpt54mini": "GPT-5.4 mini", "gpt54": "GPT-5.4", "gpt55": "GPT-5.5", "opus55": "Opus 5.5", "gpt61sol": "GPT-6.1 Sol",
        "gpt6luna": "GPT-6 Luna", "gemini38fl": "Gemini 3.8 Flash", "kimik3": "Kimi K3", "dsv4pro": "DeepSeek V4 Pro",
        "qwen38_27b": "Qwen3.8-27B", "gptoss120b": "gpt-oss-120b"}
BLUE, RED, GREY = "#2F5597", "#C9452C", "#8A8A8A"
INK, INK2, RULE = "#1A1A1A", "#4D4D4D", "#D9D9D9"
# Heatmap scale: red (low) -> pale yellow (middle) -> green-teal (high).
# A pure red-to-green scale cannot be read by red-green colour-blind readers (0 and 100 look the same);
# ending in teal keeps 0 and 100 clearly apart under deuteranomaly and protanomaly (checked in CAM02-UCS).
CMAP = LinearSegmentedColormap.from_list("red_yellow_teal", ["#A50026", "#F46D43", "#FEE8A0", "#6CC3A0", "#11756B"])


def text_on(v):
    """Dark ink on light cells, white on dark cells (by relative luminance of the cell colour)."""
    r, g, b, _ = CMAP(v / 100)
    lum = 0.2126 * r ** 2.2 + 0.7152 * g ** 2.2 + 0.0722 * b ** 2.2
    return "white" if lum < 0.22 else INK


def col(g):
    return GREY if g == "human" else (RED if g in OPEN else BLUE)


S1, X1 = R1["summary"], V2["exp1"]
S2, C2, X2 = R2["summary"], R2["controls"], V2["exp2"]
ORDER1 = sorted(MODELS, key=lambda m: S1[m]["major_mean"] + S1[m]["minor_mean"])
ORDER2 = sorted(MODELS, key=lambda m: S2[m]["major_mean"] + S2[m]["minor_mean"])

HUM = V2["human_untrained_control"]
HUM_MAJ, HUM_MIN = HUM["major_weighted"], HUM["minor_weighted"]          # 2.40, 0.89
HUM_MAJ_RANGE = (min(v["major"] for v in HUM["per_paper"].values()), max(v["major"] for v in HUM["per_paper"].values()))
HUM_MIN_RANGE = (min(v["minor"] for v in HUM["per_paper"].values()), max(v["minor"] for v in HUM["per_paper"].values()))
HUM_TOT = HUM_MAJ + HUM_MIN                                                # 3.29 of 14
HUM_SCORE_PCT = HUM_TOT / 14 * 100                                         # 23.5, share of score points
# v17: Fig. 2d compares binary detection, so the human line uses the published per-error detection percentages
# (Schroter 2008 Table 5, untrained controls), weighted by reviewers per paper: about 27.0%.
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import analyze as _A
_N = [173, 162, 156]
HUM_SENS_ALL = sum(np.dot(_A.HUMAN_PER_ERROR[e], _N) for e in ERR_IDS) / (14 * sum(_N))   # 27.0
H1 = R1["human_per_paper_error_pct"]
HUM_PER_ERR = {e: np.mean([H1[p][e] for p in ("1", "2", "3")]) for e in ERR_IDS}

plt.rcParams.update({"font.family": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"], "font.size": 8,
                     "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 8, "legend.fontsize": 7.5,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.5,
                     "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
                     "xtick.direction": "out", "ytick.direction": "out", "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": INK, "figure.dpi": 100,
                     "legend.frameon": False, "legend.handletextpad": 0.4, "axes.titlesize": 8})

KIND_HANDLES = [Line2D([], [], marker="o", ls="", color=BLUE, ms=5, label="proprietary model"),
                Line2D([], [], marker="o", ls="", color=RED, ms=5, label="open-weight model"),
                Line2D([], [], marker="o", ls="", color=GREY, ms=5, label="human reviewers")]


def panel_label(ax, s, dx=-0.08, dy=1.01):
    ax.text(dx, dy, s, transform=ax.transAxes, fontsize=10, fontweight="bold", va="bottom", ha="left")


def save(fig, name):
    # never clip dots or error bars at the edge of an axes
    for a in fig.axes:
        for art in list(a.lines) + list(a.collections):
            art.set_clip_on(False)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}_{V}.{ext}"), dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def row_axes(ax, groups, labels=True):
    """Common y axis for the row-based panels: one row per group, first group at the top."""
    n = len(groups)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_yticks(range(n))
    ax.set_yticklabels([NAME[g] for g in groups] if labels else [""] * n)
    ax.tick_params(axis="y", length=0)
    ax.axhline(0.5, color=RULE, lw=0.6, ls=(0, (2, 2)))            # separates the human row from the models


def dot_panel(ax, X, order, labels=True):
    """% of major (filled) and minor (open) inserted errors found, one row per group."""
    groups = ["human"] + order
    row_axes(ax, groups, labels)
    for i, g in enumerate(groups):
        c = col(g)
        if g == "human":
            maj, mlo, mhi = HUM_MAJ / 9 * 100, HUM_MAJ_RANGE[0] / 9 * 100, HUM_MAJ_RANGE[1] / 9 * 100
            mi, ilo, ihi = HUM_MIN / 5 * 100, HUM_MIN_RANGE[0] / 5 * 100, HUM_MIN_RANGE[1] / 5 * 100
        else:
            r = X[g]
            maj, (mlo, mhi) = r["major_mean"] / 9 * 100, [v / 9 * 100 for v in r["major_ci_clustered"]]
            mi, (ilo, ihi) = r["minor_mean"] / 5 * 100, [v / 5 * 100 for v in r["minor_ci_clustered"]]
        ax.plot([mlo, mhi], [i - 0.16, i - 0.16], color=c, lw=0.7, solid_capstyle="butt", zorder=2)
        ax.plot([ilo, ihi], [i + 0.16, i + 0.16], color=c, lw=0.7, solid_capstyle="butt", zorder=2)
        ax.scatter(maj, i - 0.17, s=22, color=c, edgecolors="white", linewidths=0.6, zorder=4)
        ax.scatter(mi, i + 0.17, s=22, facecolors="white", edgecolors=c, linewidths=0.9, zorder=4)
    ax.set_xlim(-2.5, 102.5); ax.set_xticks([0, 25, 50, 75, 100]); ax.spines["bottom"].set_bounds(0, 100)
    ax.set_xlabel("Inserted errors found (%)")
    ax.grid(axis="x", color=RULE, lw=0.4, zorder=0)
    ax.spines["left"].set_visible(False)
    h = [Line2D([], [], marker="o", ls="", color=INK2, mec="white", ms=5, label="major errors (of 9)"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=INK2, ms=5, label="minor errors (of 5)")]
    leg = ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, columnspacing=1.0, borderaxespad=0)
    ax.add_artist(leg)
    ax.legend(handles=KIND_HANDLES[:2], loc="lower left", bbox_to_anchor=(0.0, 0.0), borderaxespad=0.5,
              labelspacing=0.35, fontsize=7.5)


def heat_panel(fig, ax, S, order, labels=False, cbar=None):
    """Detection of each error (mean judge score over reviews, %), one row per group."""
    groups = ["human"] + order
    M = np.array([[HUM_PER_ERR[e]] + [S[g]["per_error_pct"][e] for g in order] for e in ERR_IDS]).T
    im = ax.imshow(M, cmap=CMAP, vmin=0, vmax=100, aspect="auto", interpolation="nearest")
    row_axes(ax, groups, labels)
    ax.set_xticks(range(len(ERR_IDS)))
    ax.set_xticklabels([ERR_SHORT[e] for e in ERR_IDS], rotation=45, ha="right", rotation_mode="anchor", fontsize=7.5)
    ax.tick_params(axis="x", length=0)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color=text_on(v))
    ax.set_xticks(np.arange(-0.5, len(ERR_IDS), 1), minor=True); ax.set_yticks(np.arange(-0.5, len(groups), 1), minor=True)
    ax.grid(which="minor", color="white", lw=0.5); ax.tick_params(which="minor", length=0)
    ax.axvline(8.5, color="white", lw=1.6)
    ax.axhline(0.5, color="white", lw=1.6)
    ax.text(4, -0.95, "major errors", ha="center", va="bottom", fontsize=7.5, color=INK2)
    ax.text(11.5, -0.95, "minor errors", ha="center", va="bottom", fontsize=7.5, color=INK2)
    for s in ax.spines.values():
        s.set_visible(False)
    if cbar is not None:
        cb = fig.colorbar(im, cax=cbar, ticks=[0, 50, 100])
        cb.set_label("Detection (%)", fontsize=7.5); cb.ax.tick_params(labelsize=7, width=0.5, length=2)
        cb.outline.set_linewidth(0.5)
    return im


def dumbbell_panel(ax, S, C, order, labels=False):
    """Summed judge score per review: error-seeded (filled) and unmodified (open) manuscripts, one row per model."""
    groups = ["human"] + order
    row_axes(ax, groups, labels)
    for i, g in enumerate(groups):
        c = col(g)
        if g == "human":
            ax.scatter(HUM_TOT, i, s=17, color=c, edgecolors="white", linewidths=0.6, zorder=4)
            ax.text(HUM_TOT + 0.45, i, f"{HUM_TOT:.1f}", va="center", fontsize=4.8, color=INK2)
            continue
        seeded = S[g]["major_mean"] + S[g]["minor_mean"]; clean = C[g]["major_mean"] + C[g]["minor_mean"]
        ax.plot([clean, seeded], [i, i], color=c, lw=1.0, alpha=0.5, zorder=2)
        ax.scatter(seeded, i, s=17, color=c, edgecolors="white", linewidths=0.6, zorder=4)
        ax.scatter(clean, i, s=17, facecolors="white", edgecolors=c, linewidths=0.9, zorder=4)
        ax.text(seeded + 0.45, i, f"{seeded:.1f}", va="center", fontsize=4.8, color=INK2)
        ax.text(clean - 0.45, i, f"{clean:.1f}", va="center", ha="right", fontsize=4.8, color=INK2)
    ax.set_xlim(-1.5, 15.5); ax.set_xticks([0, 7, 14])
    ax.set_xlabel("Summed judge score\nper review (of 14)")
    ax.grid(axis="x", color=RULE, lw=0.4, zorder=0)
    ax.spines["left"].set_visible(False)
    h = [Line2D([], [], marker="o", ls="", color=INK2, mec="white", ms=4.2, label="error-seeded (12 reviews)"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=INK2, ms=4.2, label="unmodified (3 reviews)")]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=1, borderaxespad=0, labelspacing=0.2)


def error_type_panel(ax, S, C):
    """Per error type: how often it was flagged when inserted (filled) and on the unmodified trials (open),
    mean judge score in percent pooled over the 15 models. Rows ordered by the unmodified rate."""
    ins = {e: np.mean([S[m]["per_error_pct"][e] for m in MODELS]) for e in ERR_IDS}
    un = {e: np.mean([C[m]["per_error_pct"][e] for m in MODELS]) for e in ERR_IDS}
    order = sorted(ERR_IDS, key=lambda e: (-un[e], -ins[e]))
    n = len(order)
    ax.set_ylim(n - 0.5, -0.5); ax.set_yticks(range(n)); ax.set_yticklabels([ERR_SHORT[e] for e in order])
    ax.tick_params(axis="y", length=0)
    for i, e in enumerate(order):
        ax.plot([un[e], ins[e]], [i, i], color="#A6A6A6", lw=1.0, zorder=2)
        ax.scatter(ins[e], i, s=22, color=INK, edgecolors="white", linewidths=0.6, zorder=4)
        ax.scatter(un[e], i, s=22, facecolors="white", edgecolors=INK, linewidths=0.9, zorder=4)
    ax.set_xlim(-2.5, 102.5); ax.set_xticks([0, 25, 50, 75, 100]); ax.spines["bottom"].set_bounds(0, 100)
    ax.set_xlabel("Error type flagged (%)")
    ax.grid(axis="x", color=RULE, lw=0.4, zorder=0)
    ax.spines["left"].set_visible(False)
    h = [Line2D([], [], marker="o", ls="", color=INK, mec="white", ms=5, label="error inserted (180 reviews)"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=5, label="unmodified trial (45 reviews)")]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=1, borderaxespad=0, labelspacing=0.2)
    return ins, un, order


# ================================================================ Figure 1: 2004 test papers
fig = plt.figure(figsize=(7.2, 7.6))
gs = fig.add_gridspec(2, 2, width_ratios=[0.95, 1.55], height_ratios=[0.72, 3.0], hspace=0.22, wspace=0.05)

ax_a = fig.add_subplot(gs[0, :]); ax_a.set_axis_off()
STEPS = [("Test papers", "3 test papers (2004)\n3 trials published in 2026\nsame 14 errors inserted\nunmodified 2026 controls"),
         ("Blind review", "15 language models\n4 runs per manuscript\nno tools or web access"),
         ("Blinded scoring", "2 judge models\nfixed answer key"),
         ("Outcome", "errors found vs\nhuman reviewers;\nsensitivity and specificity")]


def draw_schematic(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    w, gap = 0.205, 0.06
    x_start = (1 - (4 * w + 3 * gap)) / 2
    for k, (head, body) in enumerate(STEPS):
        x0 = x_start + k * (w + gap)
        ax.add_patch(FancyBboxPatch((x0, 0.04), w, 0.92, boxstyle="round,pad=0,rounding_size=0.012",
                                    fc="white", ec=INK, lw=0.8))
        ax.text(x0 + w / 2, 0.83, head, ha="center", va="center", fontsize=9, fontweight="bold")
        ax.text(x0 + w / 2, 0.37, body, ha="center", va="center", fontsize=8, linespacing=1.4, color=INK)
        if k < 3:
            ax.add_patch(FancyArrowPatch((x0 + w + 0.008, 0.5), (x0 + w + gap - 0.008, 0.5), arrowstyle="-|>",
                                         mutation_scale=9, lw=0.9, color=INK, shrinkA=0, shrinkB=0))


ax_b = fig.add_subplot(gs[1, 0]); panel_label(ax_b, "b", dx=-0.62, dy=1.035)
dot_panel(ax_b, X1, ORDER1)
ax_c = fig.add_subplot(gs[1, 1]); panel_label(ax_c, "c", dx=-0.03, dy=1.035)
fig.canvas.draw()
b = ax_c.get_position()
cax1 = fig.add_axes([b.x1 + 0.012, b.y0 + 0.30 * b.height, 0.010, 0.40 * b.height])
heat_panel(fig, ax_c, S1, ORDER1, cbar=cax1)
fig.canvas.draw()
rend = fig.canvas.get_renderer()
left = ax_b.get_tightbbox(rend).transformed(fig.transFigure.inverted()).x0
right = cax1.get_tightbbox(rend).transformed(fig.transFigure.inverted()).x1
pa = ax_a.get_position()
ax_a.set_position([left, pa.y0, right - left, pa.height])
draw_schematic(ax_a)
pb = ax_b.get_position()
fig.text(pb.x0 - 0.62 * pb.width, pa.y1 - 0.004, "a", fontsize=10, fontweight="bold", va="bottom", ha="left")
save(fig, "Figure1")

# ================================================================ Figure 2: trials published in 2026
# Top row as in Fig. 1 (a dots, b heatmap with its colour bar); bottom row c (error-seeded vs unmodified) next to d.
fig = plt.figure(figsize=(7.2, 9.7))
outer = fig.add_gridspec(2, 1, height_ratios=[3.0, 2.45], hspace=0.30)
top = outer[0].subgridspec(1, 2, width_ratios=[0.95, 1.55], wspace=0.05)
bot = outer[1].subgridspec(1, 2, width_ratios=[0.95, 1.55], wspace=0.30)

ax_a = fig.add_subplot(top[0, 0]); panel_label(ax_a, "a", dx=-0.62, dy=1.035)
dot_panel(ax_a, X2, ORDER2)
ax_b = fig.add_subplot(top[0, 1]); panel_label(ax_b, "b", dx=-0.03, dy=1.035)
fig.canvas.draw()
pb = ax_b.get_position()
heat_panel(fig, ax_b, S2, ORDER2, cbar=fig.add_axes([pb.x1 + 0.012, pb.y0 + 0.30 * pb.height, 0.010, 0.40 * pb.height]))

ax_c = fig.add_subplot(bot[0, 0]); panel_label(ax_c, "c", dx=-0.62, dy=1.10)
error_type_panel(ax_c, S2, C2)

# (d) sensitivity vs specificity; labels placed by hand (offsets in data units)
ax = fig.add_subplot(bot[0, 1])
ax.set_box_aspect(0.86); ax.set_anchor("W")
# Label positions (x, y in data units) chosen by hand for the crowded cluster; a thin leader line joins a label
# to its point whenever the label sits away from it.
LAB = {"haiku": (38.0, 84.0, "right"), "gemini38fl": (38.0, 91.5, "right"), "gptoss120b": (38.0, 99.0, "right"),
       "gpt54mini": (38.0, 76.5, "right"), "qwen38_27b": (60.7, 106.0, "center"), "sonnet": (71.0, 101.0, "center"),
       "kimik3": (84.0, 94.5, "left"), "opus": (96.5, 85.0, "left"), "fable": (96.5, 77.0, "left"), "opus55": (96.5, 68.5, "left"),
       "gpt54": (60.0, 66.0, "center"), "gpt6luna": (84.0, 66.0, "center"), "dsv4pro": (68.0, 58.0, "center"),
       "gpt61sol": (97.0, 58.0, "center"), "gpt55": (80.0, 50.0, "center")}
for mod in ORDER2:
    r = X2[mod]; x, y = r["sens_all"], r["spec_all"]
    xl, xh = r["sens_all_ci"]; yl, yh = r["spec_all_ci"]
    ax.plot([xl, xh], [y, y], color=col(mod), lw=0.45, alpha=0.3, zorder=2)
    ax.plot([x, x], [yl, yh], color=col(mod), lw=0.45, alpha=0.3, zorder=2)
    ax.scatter(x, y, s=26, color=col(mod), edgecolors="white", linewidths=0.6, zorder=4)
    tx, ty, ha = LAB[mod]
    ax.annotate(NAME[mod], xy=(x, y), xytext=(tx, ty), fontsize=7, color=INK, ha=ha, va="center", zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.6),
                arrowprops=dict(arrowstyle="-", color="#9A9A9A", lw=0.4, shrinkA=1.5, shrinkB=2.5))
ax.axvline(HUM_SENS_ALL, color=GREY, lw=0.8, ls=(0, (3, 2)), zorder=1)
ax.text(HUM_SENS_ALL + 1.5, 3, "human reviewers\n2008 (untrained)", fontsize=7, color=INK2, va="bottom", ha="left")
ax.set_xlabel("Inserted errors found (% of 14 error types)")
ax.set_ylabel("Error types not flagged on\nunmodified manuscripts (%)")
ax.set_xlim(0, 104); ax.set_ylim(0, 112)
ax.set_xticks([0, 25, 50, 75, 100]); ax.set_yticks([0, 25, 50, 75, 100])
ax.spines["bottom"].set_bounds(0, 100); ax.spines["left"].set_bounds(0, 100)
ax.grid(color=RULE, lw=0.4, zorder=0)
ax.legend(handles=KIND_HANDLES[:2], loc="lower right", bbox_to_anchor=(0.995, 0.02))
panel_label(ax, "d", dx=-0.20, dy=1.0)
save(fig, "Figure2")

# ================================================================ Supplementary Figure 2: by manuscript
fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.6), gridspec_kw={"wspace": 0.6})
MK = {"1": "o", "2": "s", "3": "^"}
for ax, S, order, names, ttl, lab in (
        (axes[0], S1, ORDER1, {"1": "paper 1 (discharge summaries)", "2": "paper 2 (computer record)", "3": "paper 3 (patient-held records)"}, "2004 test papers", "a"),
        (axes[1], S2, ORDER2, {"1": "stroke trial", "2": "arthritis trial", "3": "heart failure trial"}, "2026 trials", "b")):
    for i, g in enumerate(order):
        vals = [S[g]["by_paper"][p]["major"] for p in ("1", "2", "3")]
        ax.plot([min(vals), max(vals)], [i, i], color=col(g), lw=0.8, alpha=0.5, zorder=2)
        for p, v in zip(("1", "2", "3"), vals):
            ax.scatter(v, i, marker=MK[p], s=22, color=col(g), edgecolors="white", linewidths=0.5, zorder=3)
    ax.set_ylim(len(order) - 0.5, -0.5); ax.set_yticks(range(len(order))); ax.set_yticklabels([NAME[g] for g in order])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 9.3); ax.set_xticks([0, 3, 6, 9]); ax.set_xlabel("Major errors found per review (of 9)")
    ax.grid(axis="x", color=RULE, lw=0.4, zorder=0); ax.spines["left"].set_visible(False)
    ax.set_title(ttl, loc="left", pad=6)
    panel_label(ax, lab, dx=-0.62, dy=1.02)
    hh = [Line2D([], [], marker=MK[p], ls="", color=INK2, mec="white", ms=5, label=names[p]) for p in ("1", "2", "3")]
    ax.legend(handles=hh, loc="lower left", borderaxespad=0.4, labelspacing=0.25, fontsize=7)
save(fig, "SupplFigure2")

# ================================================================ Supplementary Figure 3: cost and length vs detection
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), gridspec_kw={"wspace": 0.35})
rows = R2["rows"]
means = {m: (np.mean([r["words"] for r in rows if r["model"] == m]), np.mean([sum(r["scores"].values()) for r in rows if r["model"] == m])) for m in MODELS}
for ax, lab, xs, xlabel in ((axes[0], "a", {m: CE[m]["cost"] for m in MODELS}, "Estimated cost per review (US dollars, list prices)"),
                            (axes[1], "b", {m: means[m][0] for m in MODELS}, "Review length (words)")):
    texts = []
    for m in ORDER2:
        y = means[m][1]
        ax.scatter(xs[m], y, s=26, color=col(m), edgecolors="white", linewidths=0.6, zorder=4)
        texts.append(ax.text(xs[m], y, NAME[m], fontsize=7, zorder=5))
    ax.axhline(HUM_TOT, color=GREY, lw=0.8, ls=(0, (3, 2)), zorder=1)
    ax.set_ylabel("Errors found per review (of 14)"); ax.set_ylim(0, 14.5); ax.set_yticks([0, 7, 14])
    ax.set_xlabel(xlabel)
    ax.grid(color=RULE, lw=0.4, zorder=0)
    panel_label(ax, lab, dx=-0.2, dy=1.02)
    if xlabel.startswith("Review length"):
        ax.set_xlim(0, 7000); ax.set_xticks([0, 2000, 4000, 6000])
        ax.text(6900, HUM_TOT + 0.4, "human reviewers 2008", fontsize=7, color=INK2, ha="right")
        ax.legend(handles=KIND_HANDLES[:2], loc="lower right", fontsize=7)
    else:
        ax.set_xscale("log"); ax.set_xlim(0.003, 5)
        ax.set_xticks([0.01, 0.1, 1]); ax.set_xticklabels(["$0.01", "$0.10", "$1"])
        ax.text(0.0032, HUM_TOT + 0.4, "human reviewers 2008 (5 to 8.5 h per review)", fontsize=7, color=INK2, ha="left")
    adjust_text(texts, ax=ax, expand=(1.25, 1.6), arrowprops=dict(arrowstyle="-", color="#999999", lw=0.4))
save(fig, "SupplFigure3")
# ================================================================ Supplementary Figure 1: memory probes
# Haiku 4.5, Sonnet 5, Opus 5 and Fable 5 on the 2004 test papers. Coded by hand from
# data_original/contamination_probes/*.md. Every dot carries a number on the heatmap scale of Figs 1c and 2b.
# Recall probe (no manuscript): yes = 100, partly = 50, no = 0. Recognition probe (one test paper shown): the model's
# self-rated confidence (%) that it had seen the study before (a stated range as its mean); a thick outline marks the
# papers whose source trial the model named. Answer key: no model recalled one (0).
PROBE_MODELS = ["haiku", "sonnet", "fable", "opus"]          # fewest to most errors found on the 2004 test papers
PROBE_COLS = ["Named the test papers", "Listed the 14 errors", "Recalled design and main result",
              "Recognized paper 1", "Recognized paper 2", "Recognized paper 3", "Recalled an answer key"]
PROBE = {"haiku":  [0, 0, 0, 25, 35, 15, 0],
         "sonnet": [0, 0, 50, 48, 15, 15, 0],      # paper 1: 45 to 50%; papers 2 and 3: about 15%
         "fable":  [0, 0, 100, 85, 18, 80, 0],     # paper 2: 15 to 20%
         "opus":   [0, 0, 100, 63, 13, 60, 0]}     # paper 1: 60 to 65%; paper 2: 10 to 15%
NAMED = {"haiku": [], "sonnet": [3], "fable": [3, 5], "opus": [3, 5]}   # column index of a correctly named source trial
fig, ax = plt.subplots(figsize=(5.6, 3.1))
xs = [0, 1, 2, 3.4, 4.4, 5.4, 6.4]; n = len(PROBE_MODELS)
for i, m in enumerate(PROBE_MODELS):
    for k, (x, v) in enumerate(zip(xs, PROBE[m])):
        named = k in NAMED[m]
        ax.scatter(x, i, s=330, color=CMAP(v / 100), edgecolors=INK, linewidths=2.0 if named else 0.5, zorder=3)
        ax.text(x, i, f"{v:.0f}", ha="center", va="center", fontsize=8, fontweight="bold" if named else "normal",
                color=text_on(v), zorder=4)
ax.set_xlim(-0.5, 6.9); ax.set_ylim(n - 0.5, -1.0)
ax.set_yticks(range(n)); ax.set_yticklabels([NAME[m] for m in PROBE_MODELS], fontsize=8); ax.tick_params(axis="y", length=0)
ax.set_xticks(xs); ax.set_xticklabels(PROBE_COLS, rotation=35, ha="right", rotation_mode="anchor", fontsize=8)
ax.tick_params(axis="x", length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.axvline(2.7, color=RULE, lw=0.8)
ax.text(1, -0.85, "Without the manuscript", ha="center", va="center", fontsize=8, color=INK2)
ax.text(4.9, -0.85, "With the manuscript", ha="center", va="center", fontsize=8, color=INK2)
cax = fig.add_axes([0.93, 0.42, 0.018, 0.36])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 100)), cax=cax, ticks=[0, 50, 100])
cb.ax.set_yticklabels(["0  no", "50  partly", "100  yes"]); cb.ax.tick_params(labelsize=7, width=0.5, length=2)
cb.outline.set_linewidth(0.5)
cb.ax.set_title("Recalled (%)", fontsize=7.5, pad=4, loc="left")
h = [Line2D([], [], marker="o", ls="", mfc="white", mec=INK, mew=2.0, ms=9, label="named the source trial")]
ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0.0, -0.62), fontsize=7.5, handletextpad=0.4, borderaxespad=0)
save(fig, "SupplFigure1")
print("wrote", OUT)
