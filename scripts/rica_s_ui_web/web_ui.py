import csv
from flask import Flask, render_template, request, jsonify
from flask import abort, send_from_directory, url_for
from pathlib import Path
import os
import logging
import zlib
# from ..config import c

from scripts.config import c, run_outdir, subrun_dirs, parse_run_info
from scripts.tool_registry import tool_groups, all_tools, display_name, DISPLAY_NAMES, KIND_PREFIX
from scripts.rica_s_ui_web.amr_results import AMR_COLUMNS, amr_sources, amr_counts
from scripts.rica_s_ui_web.run_times import parse_run_log, time_section
from scripts import run_state


logger = logging.getLogger(__name__)
app = Flask(__name__)


@app.context_processor
def inject_rica_s_home():
    return {"rica_s_home": c["RICA_S_HOME"]}


@app.context_processor
def inject_running_runs():
    # checked on every page render so the banner in base.html is always current
    return {"running_runs": running_runs()}


def running_runs():
    out = Path(c["OUT_DIR"])
    if not out.is_dir():
        return []
    return sorted(entry.name for entry in os.scandir(out)
                  if entry.is_dir() and run_status(entry.name) == "started")


def parse_summary_file(filepath: Path):
    """Reads the '---' separated text file and returns a list of dictionaries."""
    if not filepath.exists():
        return []

    parsed_data = []
    raw_text = filepath.read_text(encoding='utf-8')

    # Split the text by the "---" delimiter
    for section in raw_text.split("---"):
        section = section.strip()
        if not section:
            continue

        lines = section.split('\n')
        header = lines[0].strip()

        # Extract key-value pairs
        section_data = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                section_data[key.strip()] = value.strip()

        parsed_data.append({
            'header': header,
            'rows': section_data
        })

    return parsed_data


def read_status(run_dir: Path, unit_id: str):
    status_file = run_dir / f"{unit_id}.status"
    if status_file.exists():
        return status_file.read_text(encoding='utf-8').strip()
    return None


def read_log(run_dir: Path, unit_id: str):
    log_file = run_dir / f"{unit_id}.log"
    if log_file.exists():
        return log_file.read_text(encoding='utf-8', errors='replace')
    return "no log found"


def run_units(runid: str):
    base = Path(run_outdir(runid))
    if not base.is_dir():
        return []

    has_own = (any((base / f"{runid}{ext}").exists()
                   for ext in (".status", ".summary", ".log"))
               or any(base.glob("*.abricate.csv"))
               or any(base.glob("*.html")))

    units = [(runid, base)] if has_own else []
    return units + [(name, Path(path)) for _index, name, path in subrun_dirs(runid)]


def unit_read_files(runid: str):
    # sub-run <runid>_<i> processes the i-th pod5 file of the manifest
    info = Path(run_outdir(runid)) / f"{runid}.info"
    try:
        names = parse_run_info(info)[2] if info.exists() else []
    except Exception:
        names = []
    return {f"{runid}_{i}": name for i, name in enumerate(names)}


def find_unit_dir(runid: str, unit_id: str):
    return dict(run_units(runid)).get(unit_id)


def run_revision(runid: str):
    count = 0
    newest = 0.0
    for _unit_id, run_dir in run_units(runid):
        for entry in os.scandir(run_dir):
            if entry.is_file():
                count += 1
                newest = max(newest, entry.stat().st_mtime)
    return f"{count}:{newest:.0f}"


def run_status(runid: str):
    base = Path(run_outdir(runid))
    if not base.is_dir():
        return "no run ID"

    # "started" on disk but not being processed: the process running it died.
    # Runs with only an .info file are queued, not interrupted.
    own = read_status(base, runid)
    if own == "interrupted":
        return "interrupted"
    if own == "started" and run_state.listener_active:
        # the run-level status is authoritative while the pipeline is in this process;
        # it also covers the post-run merge, after every sub-run has finished
        return "started" if runid in run_state.active_runs else "interrupted"

    subs = subrun_dirs(runid)
    if not subs:
        return own or (
            "started" if (base / f"{runid}.info").exists() else "no run ID")

    # a sub-run without a status file is still being processed
    statuses = [read_status(Path(path), name) for _index, name, path in subs]
    if not any(statuses):
        return "started"
    for stopped in ("killed", "interrupted"):
        if stopped in statuses:
            return stopped

    info = base / f"{runid}.info"
    try:
        expected = len(parse_run_info(info)[2]) if info.exists() else None
    except Exception:
        expected = None

    complete = expected is None or len(subs) >= expected
    if complete and all(s == "finished" for s in statuses):
        return "finished"
    return "started"


AMR_SEPARATORS = {'RESISTANCE': ';', 'PRODUCT': ':'}

AMR_TABLE_COLUMNS = ['TOOL'] + AMR_COLUMNS


# parsed AMR results per unit dir, reused until one of its result files changes.
# L-EasyARG MGE output can hold tens of thousands of hits, so parsing it on every
# report load (and every live refresh) is too slow.
AMR_CACHE = {}
AMR_CACHE_SIZE = 8


def amr_signature(output_dir: Path, sources):
    signature = []
    for _tool, name, _load in sources:
        try:
            st = (output_dir / name).stat()
            signature.append((name, st.st_mtime_ns, st.st_size))
        except OSError:
            signature.append((name, None, None))
    return tuple(signature)


def load_amr(output_dir: Path):
    """{tagged: [(tool, row)], files: [(tool, name)], errors, version} of one unit dir."""
    sources = amr_sources(output_dir)
    key = str(output_dir)
    signature = amr_signature(output_dir, sources)
    cached = AMR_CACHE.get(key)
    if cached and cached[0] == signature:
        return cached[1]

    tagged, files, errors = [], [], []
    for tool, name, load in sources:
        files.append((tool, name))
        try:
            tagged += [(tool, row) for row in load()]
        except Exception as e:
            errors.append(f"{name}: {e}")

    amr = {
        'tagged': tagged,
        'files': files,
        'errors': errors,
        # changes with the files, so the rows URL changes and the browser refetches
        'version': f"{zlib.crc32(repr(signature).encode()):08x}",
    }
    AMR_CACHE.pop(key, None)
    AMR_CACHE[key] = (signature, amr)
    while len(AMR_CACHE) > AMR_CACHE_SIZE:
        AMR_CACHE.pop(next(iter(AMR_CACHE)))
    return amr


def amr_table_rows(amr):
    # every cell is a list of lines; the page shows them one per line
    return [[[tool]] + [split_cell(value, AMR_SEPARATORS.get(column))
                        for column, value in zip(AMR_COLUMNS, row)]
            for tool, row in amr['tagged']]


def process_csv_data(amr, runid: str, unit_id: str,
                     id_prefix: str = "csvDataTable", label: str = None):
    # one table per unit, mixing every AMR tool's rows; TOOL says which docker found it.
    # The rows are not in the page: DataTables fetches them from get_amr_rows.
    if not amr['files']:
        return []

    files = ", ".join(name for _tool, name in amr['files'])
    return [{
        'filename': f"{label} / {files}" if label else files,
        'subrun': label,
        'table_id': f"{id_prefix}_0",
        'columns': AMR_TABLE_COLUMNS,
        'row_count': len(amr['tagged']),
        'url': url_for('get_amr_rows', runid=runid, unit_id=unit_id, v=amr['version']),
        'errors': amr['errors'],
    }]


def split_cell(value: str, separator: str = None):
    return value.split(separator) if separator else [value]


# number of distinct sub-run colors defined in report.html (.tone-0 ... .tone-5)
SUBRUN_TONES = 6


def plot_tool(filename: str):
    # per-tool plots are named <reads>.<tool output>.html, e.g. x.fasta.kraken2.report.html
    prefix = KIND_PREFIX["id"]
    for name in DISPLAY_NAMES:
        if name.startswith(prefix) and f".{name[len(prefix):]}" in filename:
            return display_name(name)
    return filename


def process_pathogen_plots(runid: str, unit_id: str, output_dir: Path, run_wide: bool = False):
    plots = []

    for page in sorted(output_dir.glob("*.html")):
        if "final_report." in page.name:
            continue

        png = page.with_suffix(".png")
        aggregate = run_wide or page.stem == f"{unit_id}_aggregate"

        plots.append({
            'filename': f"{unit_id} / {page.name}",
            'subrun': unit_id,
            'kind': 'aggregate' if aggregate else 'detail',
            'title': plot_tool(page.name) if not aggregate else (
                "All sub-runs combined" if run_wide else "All tools combined"),
            'url': url_for('get_run_plot', runid=runid, unit_id=unit_id, filename=page.name),
            'png': url_for('get_run_plot', runid=runid, unit_id=unit_id, filename=png.name)
            # if png.exists() else None,
        })

    return plots


def host_root():
    return os.path.normpath(c.get("HOST_ROOT", "/"))


def to_real_path(display_path: str):
    clean = os.path.normpath("/" + (display_path or "/").lstrip("/"))
    root = host_root()
    return clean if root == "/" else os.path.normpath(root + clean)


def to_display_path(real_path: str):
    real_path = os.path.normpath(real_path)
    root = host_root()

    if root == "/":
        return real_path
    if real_path == root:
        return "/"
    return real_path[len(root):] if real_path.startswith(root + "/") else "/"


@app.route('/api/folders')
def get_folders():
    root = host_root()
    req_path = to_real_path(request.args.get('path', '/'))

    # Fallback to host root if the requested path does not exist
    if not os.path.isdir(req_path):
        req_path = root

    try:
        # Prevent navigating above the mount root
        if req_path == root:
            parent = root
        else:
            parent = os.path.dirname(req_path)
            if not parent.startswith(root):
                parent = root

        folders = [f.name for f in os.scandir(req_path) if f.is_dir()]

        return jsonify({
            "current": to_display_path(req_path),
            "parent": to_display_path(parent),
            "folders": sorted(folders)
        })
    except PermissionError:
        return jsonify({"error": "Permission Denied"})


# Routes

@app.route('/')
def root():
    groups, docker_ok = tool_groups()
    return render_template('start.html', tool_groups=groups, docker_ok=docker_ok)


@app.route('/status')
def status_page():
    return render_template('status.html')


@app.route('/check_status', methods=['GET'])
def api_check_status():
    runid = request.args.get('runid')
    if not runid:
        return jsonify({"error": "No Run ID provided"}), 400

    return jsonify({
        "runid": runid,
        "is_running": run_status(runid),
        "revision": run_revision(runid)
    })


@app.route('/report/<runid>')
def generate_report(runid):
    units = run_units(runid)
    has_subruns = any(unit_id != runid for unit_id, _dir in units)
    read_files = unit_read_files(runid)

    unit_info = []
    tone = 0
    for unit_id, _dir in units:
        run_wide = has_subruns and unit_id == runid
        unit_info.append({
            'id': unit_id,
            'read': read_files.get(unit_id),
            'run_wide': run_wide,
            'tone': None if run_wide else tone % SUBRUN_TONES,
        })
        if not run_wide:
            tone += 1

    summary_data = []
    csv_data = []
    pathogen_data = []
    log_parts = []

    status = run_status(runid)
    timings = parse_run_log(Path(run_outdir(runid)) / f"{runid}.log",
                            [unit_id for unit_id, _dir in units],
                            running=status == "started")
    amr_by_unit = {unit_id: load_amr(run_dir) for unit_id, run_dir in units}

    for index, (unit_id, run_dir) in enumerate(units):
        run_wide = has_subruns and unit_id == runid
        for section in parse_summary_file(run_dir / f"{unit_id}.summary"):
            section['header'] = f"[{unit_id}] {section['header']}"
            section['subrun'] = unit_id
            summary_data.append(section)

        # the whole run counts every sub-run's hits together
        amr_units = [u for u, _dir in units if u != runid] if run_wide else [unit_id]
        amr_files = [f for u in amr_units for f in amr_by_unit[u]['files']]
        if amr_files:
            summary_data.append({
                'header': f"[{unit_id}] AMR / mobile elements",
                'subrun': unit_id,
                'rows': amr_counts([r for u in amr_units for r in amr_by_unit[u]['tagged']],
                                   amr_files),
            })

        timing = timings.get("__run__" if run_wide else unit_id)
        if timing:
            summary_data.append(time_section(unit_id, timing, run_wide=run_wide))

        csv_data += process_csv_data(
            amr_by_unit[unit_id], runid, unit_id,
            id_prefix=f"csvDataTable_u{index}", label=unit_id)

        pathogen_data += process_pathogen_plots(
            runid, unit_id, run_dir, run_wide=has_subruns and unit_id == runid)

        log_parts.append(f"===== sub-run {unit_id} =====\n"
                         + read_log(run_dir, unit_id))

    # Render Template
    return render_template(
        'report.html',
        runid=runid,
        status=status,
        revision=run_revision(runid),
        subruns=[unit_id for unit_id, _dir in units],
        units=unit_info,
        summary_data=summary_data,
        log_text="\n\n".join(log_parts) if log_parts else "no log found",
        csv_data=csv_data,
        pathogen_data=pathogen_data
    )


@app.route('/report/<runid>/plot/<unit_id>/<filename>')
def get_run_plot(runid, unit_id, filename):
    run_dir = find_unit_dir(runid, unit_id)
    if run_dir is None:
        abort(404)

    if filename != os.path.basename(filename) or not filename.endswith((".png", ".html")):
        abort(404)
    if "final_report." in filename:
        abort(404)

    return send_from_directory(run_dir, filename)


@app.route('/report/<runid>/amr/<unit_id>')
def get_amr_rows(runid, unit_id):
    run_dir = find_unit_dir(runid, unit_id)
    if run_dir is None:
        abort(404)

    response = jsonify({"data": amr_table_rows(load_amr(run_dir))})
    # the URL carries the files' version (?v=), so a changed result gets a new URL
    if request.args.get('v'):
        response.cache_control.private = True
        response.cache_control.max_age = 3600
    return response


################
# begins new experiment

@app.route('/submitted', methods=['POST'])
def submitted_page():
    readpath = request.form.get('tb_readpath')
    runid = request.form.get('tb_runid')
    run_dir = Path(run_outdir(runid))
    info_path = run_dir / f"{runid}.info"

    tools_line = ""
    if request.form.get('tools_submitted') == '1':
        installed = set(all_tools())
        selected = [t for t in request.form.getlist('tools') if t in installed]
        if not selected:
            groups, docker_ok = tool_groups()
            return render_template(
                'start.html', tool_groups=groups, docker_ok=docker_ok,
                error="Select at least one analysis tool before submitting.",
                readpath=readpath, runid=runid), 400
        tools_line = f"tools\t{','.join(selected)}\n"

    try:
        run_dir.mkdir(parents=True, exist_ok=True)

        pod5_filenames = sorted(p.name for p in Path(readpath).glob("*.pod5"))
        logger.info(f"searching pod5s in {readpath}")
        logger.info(
            f"Found {len(pod5_filenames)} POD5 files: {pod5_filenames}")

        info_path.write_text(
            f"runid\t{runid}\n"
            f"readpath\t{readpath}\n"
            f"pod5\t{','.join(pod5_filenames)}\n"
            + tools_line
        )
        print(f"Success: wrote {info_path}")

    except PermissionError:
        logger.info(
            f"CRITICAL ERROR: Permission denied. Cannot write to {run_dir}.")
    except OSError as e:
        logger.info(f"CRITICAL ERROR: An OS error occurred: {e}")

    return render_template('submitted.html', runid=runid, readpath=readpath)


def start_web_ui():
    # 1. Create a file handler to define where the logs should be saved
    log_file_handler = logging.FileHandler('flask_server.log')

    # 2. Grab the specific logger Werkzeug uses for HTTP request output
    werkzeug_logger = logging.getLogger('werkzeug')

    # 3. Attach the file handler to the Werkzeug logger
    werkzeug_logger.addHandler(log_file_handler)

    # Optional: If you want to stop it from ALSO printing to the terminal console
    werkzeug_logger.propagate = False

    app.run(host='0.0.0.0', port=c["FLASK_PORT"],
            debug=True, use_reloader=False)


#
