"""Usage (from /opt/rica_s):
  python3 -m scripts.evaluate_resources [DIR ...]
"""

import argparse
import datetime
import glob
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from scripts.config import PROJECT_HOME, OUTPUT_ROOT
from scripts.tool_registry import display_name

EVAL_ROOT = f"{PROJECT_HOME}/evaluation"
OVERVIEW_DIR = f"{EVAL_ROOT}/resources_overview"

STAGES = ["Basecalling", "Filtering", "Classification", "Profiling", "Plotting", "Reporting"]
METADATA = "Metadata"
POST = "Post-run merge"
OTHER = "Other overhead"
IDLE = "Idle (no pipeline work)"

STAGE_COLORS = {
    "Basecalling": "#2a78d6",
    "Filtering": "#eb6834",
    "Classification": "#1baf7a",
    "Profiling": "#eda100",
    "Plotting": "#e87ba4",
    "Reporting": "#008300",
    METADATA: "#6250d6",
    POST: "#e34948",
    OTHER: "#c3c2b7",
    IDLE: "#e1e0d9",
}
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - \[([^\]]+)\] - (.*)$")
TIME_RE = re.compile(r"T> ([\d:.]+) \[h:\]m:s\.s\s*\n\s*M> (\d+) KB")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
METADATA_MSG = re.compile(r"getting metadata for|fetching (\w+) metadata")
POST_RUN_MSG = re.compile(r"Starting merge|Successfully merged|Plot saved|abricate CSV")


def ts(stamp):
    return datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S,%f")


def fmt_s(seconds):
    if seconds is None or pd.isna(seconds):
        return "n/a"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f} s"
    h, rem = divmod(int(round(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


def fmt_gb(gb):
    return "n/a" if gb is None or pd.isna(gb) else f"{gb:.2f} GB"


def read_pipeline_runs(log_paths):
    runs = []
    for path in log_paths:
        block = None
        with open(path, errors="replace") as fh:
            for raw in fh:
                m = LINE_RE.match(raw.rstrip("\n"))
                if not m:
                    continue
                when, _, msg = ts(m.group(1)), m.group(2), m.group(3).strip()
                if msg.endswith("Begin of sepsis detection"):
                    block = {"source": path, "lines": []}
                    _store(runs, block)
                if block is not None:
                    block["lines"].append((when, msg))
    unique = {}
    for b in map(_summarize, runs):
        if b.get("run_id"):
            unique.setdefault((b["run_id"], b["begin"]), b)
    return list(unique.values())


def _store(runs, block):
    runs.append(block)


def _summarize(block):
    lines = block["lines"]
    run_id = next((msg.split("run ID:", 1)[1].strip() for _, msg in lines if msg.startswith("run ID:")), None)
    block["run_id"] = run_id
    if run_id is None:
        return block
    begin = lines[0][0]
    end_i = next((i for i, (_, msg) in enumerate(lines) if msg.endswith("End of sepsis detection")), None)

    stages, open_stage = {}, None
    tools, metadata = [], []
    for i, (when, msg) in enumerate(lines):
        mm = METADATA_MSG.search(msg)
        if mm and i + 1 < len(lines) and (end_i is None or i < end_i):
            what = f"{mm.group(1)} metadata" if mm.group(1) else "input pod5 metadata"
            metadata.append({"step": what, "start": when,
                             "time_s": (lines[i + 1][0] - when).total_seconds()})
        mb = re.search(r"\[i\]> Begin of (\w+) stage", msg, re.I)
        me = re.search(r"\[i\]> End of (\w+) stage", msg, re.I)
        if mb:
            open_stage = _stage_name(mb.group(1))
            stages[open_stage] = {"start": when, "end": None}
        elif me and _stage_name(me.group(1)) in stages:
            stages[_stage_name(me.group(1))]["end"] = when
            open_stage = None
        ms = re.match(r"\[i\]> (rica_s_\S+) ===$", msg)
        if ms and not (tools and tools[-1]["container"] == ms.group(1) and tools[-1]["end"] is None):
            tools.append({"container": ms.group(1), "stage": open_stage, "start": when, "end": None})
        mo = re.match(r"\[i\]> === (rica_s_\S+)$", msg)
        if mo and tools and tools[-1]["container"] == mo.group(1):
            tools[-1]["end"] = lines[i + 1][0] if i + 1 < len(lines) else None

    last = lines[-1][0]
    for st in stages.values():
        st["incomplete"] = st["end"] is None
        if st["end"] is None:
            later = [s["start"] for s in stages.values() if s["start"] > st["start"]]
            st["end"] = min(later) if later else last

    if end_i is not None:
        end = lines[end_i][0]
        post = [w for w, msg in lines[end_i + 1:] if POST_RUN_MSG.search(msg)]
        post_end = max(post) if post else None
    else:
        end, post_end = last, None

    covered = [(st["start"], st["end"]) for st in stages.values()] + \
              [(m["start"], m["start"] + datetime.timedelta(seconds=m["time_s"])) for m in metadata]
    stop = end_i if end_i is not None else len(lines) - 1
    gaps = []
    for (a, msg), (b, _) in zip(lines[:stop], lines[1:stop + 1]):
        mid = a + (b - a) / 2
        if (b - a).total_seconds() > 30 and not any(s <= mid <= e for s, e in covered):
            kind = "idle" if msg.endswith("End of reporting stage") else "unlogged"
            gaps.append({"after": msg, "start": a, "time_s": (b - a).total_seconds(), "kind": kind})

    block.update(
        gaps=gaps,
        begin=begin, end=end, complete=end_i is not None,
        total_s=(end - begin).total_seconds(),
        post_s=(post_end - end).total_seconds() if post_end else None,
        stages=stages, tools=tools, metadata=metadata,
    )
    return block


def _stage_name(word):
    word = word.lower()
    for st in STAGES:
        if st.lower() == word:
            return st
    return word.capitalize()


def parse_elapsed(text):
    parts = [float(p) for p in text.split(":")]
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def label_chunk(chunk):
    db = re.search(r"Using (?:nucl|prot) database (\S+):", chunk)
    if db:
        return "rica_s_pr_abricate", "Profiling", db.group(1)
    if "EasyARG" in chunk:
        return "rica_s_pr_l-easyarg", "Profiling", None
    if "basecaller" in chunk or "Simplex reads basecalled" in chunk:
        return "rica_s_bc_dorado", "Basecalling", None
    if re.search(r"CMD: minimap2 -a\b", chunk) or "human_v38" in chunk:
        return "rica_s_id_minimap2", "Filtering", None
    if "CuCLARK" in chunk:
        return "rica_s_id_cuclark", "Classification", None
    if "CLARK version" in chunk:
        return "rica_s_id_clark", "Classification", None
    if "bwa mem" in chunk or "bwa_idx_load" in chunk:
        return "rica_s_id_bwa", "Classification", None
    if "sequences classified" in chunk or "Loading database information" in chunk:
        return "rica_s_id_kraken2", "Classification", None
    if "CMD: minimap2" in chunk:
        return "rica_s_id_minimap2", "Classification", None
    if "ngmlr" in chunk:
        return "rica_s_id_ngmlr", "Classification", None
    return "rica_s_id_blast", "Classification", None


def read_tool_measurements(path):
    with open(path, errors="replace") as fh:
        text = ANSI_RE.sub("", fh.read())
    segments = [s for s in text.split("RICA_S") if TIME_RE.search(s)]
    if not segments:
        return []
    text = segments[-1]
    rows, prev = [], 0
    for m in TIME_RE.finditer(text):
        chunk = text[prev:m.start()]
        container, stage, sub = label_chunk(chunk)
        status = re.search(r"Command exited with non-zero status (\d+)", chunk)
        rows.append({
            "container": container, "stage": stage, "sub": sub,
            "time_s": parse_elapsed(m.group(1)),
            "rss_gb": int(m.group(2)) / 1024 ** 2,
            "exit": int(status.group(1)) if status else 0,
        })
        prev = m.end()
    return rows


def tool_label(container, stage):
    name = display_name(container)
    if container == "rica_s_bc_dorado":
        return "Dorado"
    if container == "rica_s_id_minimap2" and stage == "Filtering":
        return "minimap2 (human filter)"
    return name


def pick_primary(runs):
    return max(runs, key=lambda r: (len(r["tools"]), len(r["stages"]), r["begin"])) if runs else None


def build_tables(run, measurements):
    stage_rows = []
    if run:
        for st, span in sorted(run["stages"].items(), key=lambda kv: kv[1]["start"]):
            stage_rows.append({"stage": st, "start": span["start"], "end": span["end"],
                               "time_s": (span["end"] - span["start"]).total_seconds(),
                               "incomplete": span["incomplete"]})
    if run and run["metadata"]:
        meta = run["metadata"]
        stage_rows.append({"stage": METADATA, "start": meta[0]["start"], "end": None,
                           "time_s": sum(m["time_s"] for m in meta), "incomplete": False})
    stages = pd.DataFrame(stage_rows, columns=["stage", "start", "end", "time_s", "incomplete"])

    wall = {}
    if run:
        for t in run["tools"]:
            key = (t["container"], t["stage"])
            dur = (t["end"] - t["start"]).total_seconds() if t["end"] else None
            wall[key] = dur
    meas = pd.DataFrame(measurements, columns=["container", "stage", "sub", "time_s", "rss_gb", "exit"])
    agg = {}
    if not meas.empty:
        for (container, stage), g in meas.groupby(["container", "stage"], sort=False):
            agg[(container, stage)] = {"time_s": g["time_s"].sum(), "rss_gb": g["rss_gb"].max(),
                                       "exit": int(g["exit"].max()), "n": len(g)}
    order = list(dict.fromkeys(list(wall) + list(agg)))
    tool_rows = []
    for container, stage in order:
        a = agg.get((container, stage), {})
        tool_rows.append({
            "stage": stage, "tool": tool_label(container, stage), "container": container,
            "wall_s": wall.get((container, stage)),
            "time_s": a.get("time_s"), "peak_rss_gb": a.get("rss_gb"),
            "exit_status": a.get("exit"), "timed_calls": a.get("n", 0),
        })
    tools = pd.DataFrame(tool_rows, columns=["stage", "tool", "container", "wall_s", "time_s",
                                             "peak_rss_gb", "exit_status", "timed_calls"])
    tools["used_s"] = tools["wall_s"].where(tools["wall_s"].notna(), tools["time_s"])

    if not stages.empty:
        peak = tools.groupby("stage")["peak_rss_gb"].max()
        stages["peak_rss_gb"] = stages["stage"].map(peak)
        stages["n_tools"] = stages["stage"].map(tools.groupby("stage").size()).fillna(0).astype(int)
    elif not tools.empty:
        g = tools.groupby("stage", sort=False)
        stages = pd.DataFrame({"stage": list(g.groups), "start": None, "end": None,
                               "time_s": g["used_s"].sum().values, "incomplete": False,
                               "peak_rss_gb": g["peak_rss_gb"].max().values,
                               "n_tools": g.size().values})

    dbs = meas[meas["sub"].notna()][["sub", "time_s", "rss_gb", "exit"]].rename(
        columns={"sub": "database", "rss_gb": "peak_rss_gb", "exit": "exit_status"})
    return stages, tools, dbs


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _legend(ax, stages_present):
    handles = [plt.Rectangle((0, 0), 1, 1, color=STAGE_COLORS.get(s, MUTED)) for s in stages_present]
    if len(handles) > 1:
        ax.legend(handles, stages_present, title="Stage", frameon=False, fontsize=8,
                  title_fontsize=8, loc="lower right", labelcolor=INK_2)


def hbar(df, value, label_fn, title, subtitle, xlabel, path, color_col="stage", legend=True):
    df = df[df[value].notna()].sort_values(value)
    if df.empty:
        return False
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(df) + 1.6), facecolor=SURFACE)
    _style(ax)
    colors = [STAGE_COLORS.get(s, MUTED) for s in df[color_col]]
    bars = ax.barh(df["label"], df[value], color=colors, height=0.62,
                   edgecolor=SURFACE, linewidth=2)
    vmax = df[value].max()
    for bar, v in zip(bars, df[value]):
        ax.text(bar.get_width() + vmax * 0.01, bar.get_y() + bar.get_height() / 2, label_fn(v),
                va="center", ha="left", fontsize=8.5, color=INK_2)
    ax.set_xlim(0, vmax * 1.18)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    ax.set_title(subtitle, loc="left", fontsize=9, color=INK_2)
    if legend:
        _legend(ax, list(dict.fromkeys(df[color_col][::-1])))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return True


def plot_dir(name, outdir, stages, tools, total_s):
    made = []
    if not stages.empty:
        st = stages.assign(label=stages["stage"])
        sub = f"Total run time {fmt_s(total_s)}" if total_s else "Sum of timed tools (no pipeline log)"
        if hbar(st, "time_s", fmt_s, f"{name} - time per stage", sub, "wall-clock time (s)",
                f"{outdir}/resources_time_per_stage.png", legend=False):
            made.append("resources_time_per_stage.png")
    if not tools.empty:
        tl = tools.assign(label=tools["tool"])
        if hbar(tl, "used_s", fmt_s, f"{name} - time per tool",
                "Wall-clock time of each tool container (pipeline log; /usr/bin/time if absent)",
                "time (s)", f"{outdir}/resources_time_per_tool.png"):
            made.append("resources_time_per_tool.png")
        if hbar(tl, "peak_rss_gb", lambda v: f"{v:.2f} GB", f"{name} - peak memory per tool",
                "Max resident set size of the largest process (/usr/bin/time %M); GPU memory not included",
                "peak RSS (GB)", f"{outdir}/resources_memory_per_tool.png"):
            made.append("resources_memory_per_tool.png")
    return made


def plot_overview(summary, path_time, path_mem):
    df = summary[summary["total_s"].notna() | summary["peak_rss_gb"].notna()]
    if df.empty:
        return []
    made = []
    stage_cols = [s for s in STAGES + [METADATA, OTHER, IDLE] if s in df.columns and df[s].fillna(0).sum() > 0]
    td = df[df["total_s"].notna() & (df["n_tools"] > 0)].sort_values("total_s")
    if not td.empty:
        fig, ax = plt.subplots(figsize=(10, 0.42 * len(td) + 2), facecolor=SURFACE)
        _style(ax)
        left = pd.Series(0.0, index=td.index)
        for s in stage_cols:
            vals = td[s].fillna(0) / 60
            ax.barh(td["directory"], vals, left=left, color=STAGE_COLORS[s], height=0.62,
                    edgecolor=SURFACE, linewidth=2, label=s, hatch="///" if s == IDLE else None)
            left += vals
        for y, (tot, d) in enumerate(zip(td["total_s"], td["directory"])):
            ax.text(left.iloc[y] + left.max() * 0.01, y, fmt_s(tot), va="center", fontsize=8.5, color=INK_2)
        ax.set_xlim(0, left.max() * 1.15)
        ax.set_xlabel("wall-clock time (min)", color=MUTED, fontsize=9)
        fig.suptitle("Run time per output directory, split by stage", x=0.01, ha="left",
                     fontsize=12, color=INK, fontweight="bold")
        ax.set_title("Most complete run per directory; label = total. Plot-only re-runs omitted.",
                     loc="left", fontsize=9, color=INK_2)
        ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK_2)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fig.savefig(path_time, dpi=150, facecolor=SURFACE)
        plt.close(fig)
        made.append(os.path.basename(path_time))
    md = df[df["peak_rss_gb"].notna()].assign(label=lambda d: d["directory"], stage=lambda d: d["peak_stage"])
    if hbar(md, "peak_rss_gb", lambda v: f"{v:.2f} GB", "Peak memory per output directory",
            "Largest single-tool peak RSS in the run; colored by the stage it occurred in",
            "peak RSS (GB)", path_mem):
        made.append(os.path.basename(path_mem))
    return made


def md_table(df, cols, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(f(r[c]) if callable(f) else str(r[c]) for c, f in cols) + " |")
    return "\n".join(out)


def write_report(name, outdir, logs, runs, run, stages, tools, dbs, plots, other_files):
    L = [f"# Resource usage - `{name}`", "",
         f"_Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by `scripts/evaluate_resources.py`._", ""]
    L += ["## Logs searched", ""]
    if not logs:
        L.append("- none: this directory contains no .log files")
    for p in logs:
        L.append(f"- `{os.path.relpath(p, PROJECT_HOME)}` ({os.path.getsize(p):,} bytes)")
    if other_files:
        L.append(f"- runs of this directory were also found in: "
                 + ", ".join(f"`{os.path.relpath(p, PROJECT_HOME)}`" for p in other_files))
    L.append("")

    if run is None and tools.empty:
        L += ["## Result", "",
              "No timing or memory data was found for this directory: its logs contain no run "
              "of it and no `/usr/bin/time` measurements.", ""]
        return "\n".join(L)

    if run:
        L += ["## Summary", "",
              f"- Run analyzed: `{run['run_id']}` started {run['begin']:%Y-%m-%d %H:%M:%S}"
              + ("" if run["complete"] else " (**did not reach 'End of sepsis detection'**)"),
              f"- Total time (begin -> end of sepsis detection): **{fmt_s(run['total_s'])}**"]
        idle = sum(g["time_s"] for g in run["gaps"] if g["kind"] == "idle")
        if idle:
            L.append(f"- Active time, excluding {fmt_s(idle)} of idle gaps (see below): "
                     f"**{fmt_s(run['total_s'] - idle)}**")
        if run.get("post_s"):
            L.append(f"- Post-run merge of TSV/ABRicate results and overview plot: {fmt_s(run['post_s'])}")
    else:
        L += ["## Summary", "", "- No pipeline-log run found; figures below come from the tool log only."]
    if tools["peak_rss_gb"].notna().any():
        top = tools.loc[tools["peak_rss_gb"].idxmax()]
        L.append(f"- Peak memory: **{fmt_gb(top['peak_rss_gb'])}** ({top['tool']}, {top['stage']})")
    if not tools.empty and tools["used_s"].notna().any():
        slow = tools.loc[tools["used_s"].idxmax()]
        L.append(f"- Slowest tool: **{slow['tool']}** ({fmt_s(slow['used_s'])})")
    if run and not run["tools"]:
        L.append("- Note: every run found for this directory only re-ran plotting and reporting; "
                 "the stages that run tools were skipped because their outputs already existed, "
                 "so no per-tool time or memory is available.")
    elif run and tools["time_s"].isna().any():
        missing = ", ".join(tools.loc[tools["time_s"].isna(), "tool"])
        L.append(f"- Note: the tool log has no `/usr/bin/time` entry for {missing}, so those "
                 "tools have wall time only and no memory figure.")
    failed = tools[tools["exit_status"].fillna(0) > 0]
    for _, r in failed.iterrows():
        L.append(f"- Warning: {r['tool']} exited with status {int(r['exit_status'])}, "
                 "so its time does not reflect a full run.")
    L.append("")

    if len(runs) > 1:
        L += ["## All runs found for this directory", "",
              "The analysis uses the run that executed the most tools; the others were mostly "
              "re-runs that skipped stages whose outputs already existed.", "",
              md_table(pd.DataFrame(runs), [
                  ("run_id", str), ("begin", lambda v: f"{v:%Y-%m-%d %H:%M:%S}"),
                  ("total_s", fmt_s), ("n_tools", str), ("stages", str),
                  ("source", lambda v: f"`{os.path.basename(v)}`")],
                  ["run ID", "began", "total", "tools run", "stages run", "found in"]), ""]

    if not stages.empty:
        L += ["## Time and memory per stage", "",
              md_table(stages, [("stage", str), ("time_s", fmt_s),
                                ("time_s", lambda v: f"{100 * v / run['total_s']:.1f}%" if run and run["total_s"] else "n/a"),
                                ("peak_rss_gb", fmt_gb), ("n_tools", str)],
                       ["stage", "time", "% of total", "peak RSS", "timed tools"]), ""]
        if run:
            other = run["total_s"] - stages["time_s"].sum()
            if run["metadata"]:
                L += ["`Metadata` is the time spent extracting input/intermediate file metadata "
                      "between stages:", ""]
                L += [f"- {m['step']}: {fmt_s(m['time_s'])}" for m in run["metadata"]] + [""]
            L += [f"Remaining overhead not covered by any stage: {fmt_s(other)}. "
                  "Plotting, reporting and metadata steps run in the pipeline's own Python "
                  "process, so they have no memory measurement.", ""]
            unlogged = [g for g in run["gaps"] if g["kind"] == "unlogged"]
            idle = [g for g in run["gaps"] if g["kind"] == "idle"]
            if unlogged:
                L += ["Gaps longer than 30 s that no stage, tool or metadata message covers. They are "
                      "real work the log does not name; after basecalling this is the FASTQ "
                      "statistics step, which older pipeline versions ran without a log message:", ""]
                L += [f"- {fmt_s(g['time_s'])} starting {g['start']:%H:%M:%S}, after "
                      f"\"{g['after'][:90]}\"" for g in unlogged] + [""]
            if idle:
                L += ["Idle gaps: the pipeline code does no work between the end of reporting and "
                      "\"End of sepsis detection\", so this time is most likely the process being "
                      "blocked or the machine suspended. It is excluded from the active time:", ""]
                L += [f"- {fmt_s(g['time_s'])} starting {g['start']:%H:%M:%S}, after "
                      f"\"{g['after'][:90]}\"" for g in idle] + [""]

    if not tools.empty:
        L += ["## Time and memory per tool", "",
              md_table(tools, [("stage", str), ("tool", str), ("wall_s", fmt_s), ("time_s", fmt_s),
                               ("peak_rss_gb", fmt_gb), ("exit_status", lambda v: "n/a" if pd.isna(v) else str(int(v)))],
                       ["stage", "tool", "wall time (pipeline log)", "/usr/bin/time elapsed", "peak RSS", "exit"]),
              "",
              "- **Wall time** spans the tool's container call in the pipeline log, which includes "
              "container start-up and its script's pre- and post-processing (for example, the "
              "SAM-to-FASTA conversion after the human filter).",
              "- **/usr/bin/time elapsed** covers only the wrapped command; for ABRicate it is "
              "the sum over its databases.",
              "- **Peak RSS** is `/usr/bin/time %M`: the max resident memory of the largest single "
              "process, not the sum over processes. GPU memory (Dorado, CuCLARK) is not included.", ""]

    if not dbs.empty:
        L += ["### ABRicate per database", "",
              md_table(dbs, [("database", str), ("time_s", fmt_s), ("peak_rss_gb", fmt_gb)],
                       ["database", "elapsed", "peak RSS"]), ""]

    if plots:
        L += ["## Plots", ""] + [f"![{p}]({p})" for p in plots] + [""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="*", help="output directories to report (default: all)")
    args = ap.parse_args(argv)

    all_dirs = sorted(d for d in os.listdir(OUTPUT_ROOT) if os.path.isdir(f"{OUTPUT_ROOT}/{d}"))
    dirs = args.dirs or all_dirs

    pipeline_logs = sorted(glob.glob(f"{OUTPUT_ROOT}/*/*.log"))
    all_runs = read_pipeline_runs(pipeline_logs)
    by_dir = {}
    for r in all_runs:
        by_dir.setdefault(re.sub(r"_\d+$", "", r["run_id"]), []).append(r)

    summary_rows, all_tools = [], []
    for name in dirs:
        base = f"{OUTPUT_ROOT}/{name}"
        logs = sorted(glob.glob(f"{base}/*.log") + glob.glob(f"{base}/*/*.log"))
        tool_logs = [p for p in logs if os.path.dirname(p) != base]
        runs = sorted(by_dir.get(name, []), key=lambda r: r["begin"])
        run = pick_primary(runs)
        measurements = [m for p in tool_logs for m in read_tool_measurements(p)]
        stages, tools, dbs = build_tables(run, measurements)

        outdir = f"{EVAL_ROOT}/{name}"
        os.makedirs(outdir, exist_ok=True)
        plots = plot_dir(name, outdir, stages, tools, run["total_s"] if run else None)

        run_rows = [{"run_id": r["run_id"], "begin": r["begin"], "end": r["end"], "total_s": r["total_s"],
                     "complete": r["complete"], "n_tools": len(r["tools"]),
                     "stages": ", ".join(r["stages"]) or "-", "source": r["source"]} for r in runs]
        other_files = sorted({r["source"] for r in runs} - set(logs))

        if run_rows:
            pd.DataFrame(run_rows).to_csv(f"{outdir}/resources_runs.tsv", sep="\t", index=False, float_format="%.3f")
        if not stages.empty:
            stages.to_csv(f"{outdir}/resources_stages.tsv", sep="\t", index=False, float_format="%.3f")
        if not tools.empty:
            tools.to_csv(f"{outdir}/resources_tools.tsv", sep="\t", index=False, float_format="%.3f")
            all_tools.append(tools.assign(directory=name))
        if not dbs.empty:
            dbs.to_csv(f"{outdir}/resources_abricate_db.tsv", sep="\t", index=False, float_format="%.3f")
        with open(f"{outdir}/resources_report.md", "w") as fh:
            fh.write(write_report(name, outdir, logs, run_rows, run, stages, tools, dbs, plots, other_files))

        row = {"directory": name, "run_id": run["run_id"] if run else None,
               "total_s": run["total_s"] if run else None,
               "idle_s": sum(g["time_s"] for g in run["gaps"] if g["kind"] == "idle") if run else None,
               "complete": run["complete"] if run else None,
               "n_runs": len(runs), "n_tools": len(tools)}
        for _, s in stages.iterrows():
            row[s["stage"]] = s["time_s"]
        if run:
            row[POST] = run.get("post_s")
            row[IDLE] = row["idle_s"]
            row[OTHER] = run["total_s"] - stages["time_s"].sum() - row["idle_s"]
        if tools["peak_rss_gb"].notna().any():
            top = tools.loc[tools["peak_rss_gb"].idxmax()]
            row.update(peak_rss_gb=top["peak_rss_gb"], peak_tool=top["tool"], peak_stage=top["stage"])
        summary_rows.append(row)
        print(f"{name:32s} runs={len(runs):2d} tools={len(tools):2d} timed={len(measurements):2d} "
              f"total={fmt_s(row['total_s'])} plots={len(plots)}")

    if not args.dirs:
        os.makedirs(OVERVIEW_DIR, exist_ok=True)
        cols = ["directory", "run_id", "total_s", "idle_s", "complete", "n_runs", "n_tools"] + \
               [c for c in STAGES + [METADATA, POST, OTHER, IDLE] if any(c in r for r in summary_rows)] + \
               ["peak_rss_gb", "peak_tool", "peak_stage"]
        summary = pd.DataFrame(summary_rows).reindex(columns=cols)
        summary.to_csv(f"{OVERVIEW_DIR}/resources_summary.tsv", sep="\t", index=False, float_format="%.3f")
        if all_tools:
            pd.concat(all_tools).to_csv(f"{OVERVIEW_DIR}/resources_tools_all.tsv", sep="\t", index=False, float_format="%.3f")
        made = plot_overview(summary, f"{OVERVIEW_DIR}/resources_time_per_directory.png",
                             f"{OVERVIEW_DIR}/resources_memory_per_directory.png")
        print("overview:", ", ".join(made))
    return 0


if __name__ == "__main__":
    sys.exit(main())
