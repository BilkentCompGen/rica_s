"""
Run time per sub-run, per stage and per tool, read from the run log <runid>/<runid>.log.

Same markers as scripts/evaluate_resources.py, but split per sub-run ("run ID:" line)
and free of pandas/matplotlib so the web report can import it cheaply.
"""
import datetime
import re
from pathlib import Path

from scripts.tool_registry import display_name

LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - \[([^\]]+)\] - (.*)$")
STAGE_BEGIN_RE = re.compile(r"\[i\]> Begin of (\w+) stage", re.I)
STAGE_END_RE = re.compile(r"\[i\]> End of (\w+) stage", re.I)
TOOL_BEGIN_RE = re.compile(r"\[i\]> (rica_s_\S+) ===$")
TOOL_END_RE = re.compile(r"\[i\]> === (rica_s_\S+)$")

RUN_BEGIN = "Begin of sepsis detection"
RUN_END = "End of sepsis detection"
REPORT_END = "End of reporting stage"


def ts(stamp):
    return datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S,%f")


def fmt_s(seconds):
    if seconds is None:
        return "n/a"
    if seconds < 60:
        return f"{seconds:.1f} s"
    h, rem = divmod(int(round(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


def tool_label(container, stage):
    if container == "rica_s_bc_dorado":
        return "Dorado"
    if container == "rica_s_id_minimap2" and stage == "Filtering":
        return "minimap2 (human filter)"
    return display_name(container)


def read_lines(log_path: Path):
    lines = []
    with open(log_path, errors="replace") as fh:
        for raw in fh:
            m = LINE_RE.match(raw.rstrip("\n"))
            if m:
                lines.append((ts(m.group(1)), m.group(3).strip()))
    return lines


def subrun_timing(lines, stop):
    """Stages and tools of one sub-run block; stop closes whatever is still open."""
    stages, tools = {}, []
    open_stage = None
    for i, (when, msg) in enumerate(lines):
        mb, me = STAGE_BEGIN_RE.search(msg), STAGE_END_RE.search(msg)
        if mb:
            open_stage = mb.group(1).capitalize()
            stages[open_stage] = [when, None]
        elif me and me.group(1).capitalize() in stages:
            stages[me.group(1).capitalize()][1] = when
            open_stage = None

        tb, te = TOOL_BEGIN_RE.search(msg), TOOL_END_RE.search(msg)
        # dorado logs its start marker twice
        if tb and not (tools and tools[-1][0] == tb.group(1) and tools[-1][3] is None):
            tools.append([tb.group(1), open_stage, when, None])
        elif te and tools and tools[-1][0] == te.group(1):
            # exec_run streams; the tool is done when the next line is logged
            tools[-1][3] = lines[i + 1][0] if i + 1 < len(lines) else None

    def span(start, end):
        return ((end or stop) - start).total_seconds()

    return {
        "stages": [(name, span(s, e), e is None) for name, (s, e) in stages.items()],
        "tools": [(tool_label(c, st), span(s, e), e is None) for c, st, s, e in tools],
    }


def parse_run_log(log_path: Path, unit_ids, running=False):
    """{unit_id: timing} for every sub-run in unit_ids, plus "__run__" for the whole run."""
    if not log_path.exists():
        return {}
    lines = read_lines(log_path)
    if not lines:
        return {}

    stop = datetime.datetime.now() if running else lines[-1][0]
    wanted = set(unit_ids)

    # blocks start at "run ID: <sub_id>"
    starts = [(i, msg.split("run ID:", 1)[1].strip())
              for i, (_, msg) in enumerate(lines) if msg.startswith("run ID:")]
    result = {}
    for k, (i, sub_id) in enumerate(starts):
        if sub_id not in wanted:
            continue
        j = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        block = lines[i:j]
        end_i = next((n for n, (_, msg) in enumerate(block) if msg.endswith(REPORT_END)), None)
        block = block[:end_i + 1] if end_i is not None else block
        # an unfinished last block runs until now / the last line
        block_stop = block[-1][0] if end_i is not None or k + 1 < len(starts) else stop
        timing = subrun_timing(block, block_stop)
        timing["total_s"] = (block_stop - block[0][0]).total_seconds()
        timing["finished"] = end_i is not None
        timing["finished_at"] = block_stop
        timing["in_progress"] = not timing["finished"] and running
        result[sub_id] = timing

    begin = next((w for w, msg in lines if msg.endswith(RUN_BEGIN)), None)
    run_end = next((w for w, msg in lines if msg.endswith(RUN_END)), None)
    end = run_end or stop
    parts = []
    if begin:
        parts.append(("Container startup", (begin - lines[0][0]).total_seconds()))
    parts += [(sub_id, t["total_s"]) for sub_id, t in result.items()]
    # the merge runs only after the last sub-run finished its reporting stage
    if result and all(t["finished"] for t in result.values()):
        last_report = max(t["finished_at"] for t in result.values())
        parts.append(("Post-run merge", (end - last_report).total_seconds()))
    result["__run__"] = {
        "total_s": (end - lines[0][0]).total_seconds(),
        "parts": parts,
        "in_progress": running,
        "running": running,
    }
    for t in result.values():
        t["running"] = running
    return result


def fmt_min(seconds):
    """Every run time is shown in minutes so the rows compare at a glance."""
    if seconds is None:
        return "n/a"
    m = seconds / 60
    return f"{m:.1f} min" if m >= 1 else f"{m:.2f} min"


def _fmt(seconds, open_=False, running=True):
    if not open_:
        return fmt_min(seconds)
    return fmt_min(seconds) + (" (running)" if running else " (incomplete)")


# categorical slots, fixed order (light palette of the dataviz reference); the
# 8th slot is reserved for "Other" when a bar has more parts than colors
BAR_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#6250d6"]
OTHER_COLOR = "#8a8984"
# light fills take dark text, the others white
DARK_INK = {"#1baf7a", "#eda100", "#e87ba4"}
# a segment narrower than this share of the bar carries no inline label; the
# page also hides any label that does not fit its segment (fitTimeLabels)
LABEL_MIN_SHARE = 0.04


def stacked_bar(items):
    """
    items: [(name, seconds)] in display order.
    Returns (segments, swatches): segments for the stacked bar, each with its
    share of the bar, and {name: color} so the table rows double as the legend.
    """
    items = [(n, max(s or 0, 0)) for n, s in items]
    total = sum(s for _n, s in items)
    if total <= 0:
        return [], {}

    # more parts than colors: the largest keep a color, the rest fold into "Other"
    if len(items) > len(BAR_COLORS) + 1:
        keep = {n for n, _s in sorted(items, key=lambda x: -x[1])[:len(BAR_COLORS)]}
    else:
        keep = {n for n, _s in items}
    slots = iter(BAR_COLORS + [OTHER_COLOR])

    segments, swatches, other_s = [], {}, 0.0
    for name, sec in items:
        if name not in keep:
            other_s += sec
            continue
        color = next(slots)
        swatches[name] = color
        segments.append({"label": name, "seconds": sec, "color": color})
    if other_s or len(keep) < len(items):
        for name, _s in items:
            if name not in keep:
                swatches[name] = OTHER_COLOR
        segments.append({"label": "Other", "seconds": other_s, "color": OTHER_COLOR})

    for seg in segments:
        share = seg["seconds"] / total
        seg["pct"] = round(100 * share, 1)
        seg["minutes"] = fmt_min(seg["seconds"])
        seg["show_label"] = share >= LABEL_MIN_SHARE
        seg["ink"] = "#0b0b0b" if seg["color"] in DARK_INK else "#ffffff"
    return segments, swatches


def _group(title, items, running=True):
    """items: [(name, seconds, open)] -> a summary group with its stacked bar."""
    rows, bar_items = {}, []
    for n, s, o in items:
        # same name twice in a sub-run (should not happen) keeps both
        key = n if n not in rows else f"{n} ({len(rows)})"
        rows[key] = _fmt(s, o, running)
        bar_items.append((key, s))
    bar, swatches = stacked_bar(bar_items)
    return {"title": title, "rows": rows, "bar": bar, "swatches": swatches}


def time_section(unit_id, timing, run_wide=False):
    if run_wide:
        groups = [_group("By part", [(n, s, False) for n, s in timing["parts"]])]
    else:
        groups = []
        if timing["stages"]:
            groups.append(_group("By stage", timing["stages"], timing["running"]))
        if timing["tools"]:
            groups.append(_group("By tool", timing["tools"], timing["running"]))
    return {
        "header": f"[{unit_id}] Run time",
        "subrun": unit_id,
        "rows": {"Total": _fmt(timing["total_s"], timing["in_progress"])},
        "groups": groups,
    }
