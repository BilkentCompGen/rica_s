import csv
from flask import Flask, render_template, request, jsonify
from flask import abort, send_from_directory, url_for
from pathlib import Path
import os
import logging
# from ..config import c

from scripts.config import c, run_outdir, subrun_dirs, parse_run_info
from scripts.tool_registry import tool_groups, all_tools


logger = logging.getLogger(__name__)
app = Flask(__name__)


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

    subs = subrun_dirs(runid)
    if not subs:
        return read_status(base, runid) or (
            "started" if (base / f"{runid}.info").exists() else "no run ID")

    statuses = [s for s in (read_status(Path(path), name)
                            for _index, name, path in subs) if s]
    if not statuses:
        return "started"
    if "killed" in statuses:
        return "killed"

    info = base / f"{runid}.info"
    try:
        expected = len(parse_run_info(info)[2]) if info.exists() else None
    except Exception:
        expected = None

    complete = expected is None or len(subs) >= expected
    if complete and all(s == "finished" for s in statuses):
        return "finished"
    return "started"


AMR_COLUMNS = [
    'GENE', '%COVERAGE', '%IDENTITY', 'PRODUCT',
    'RESISTANCE', 'DATABASE', 'ACCESSION', '#FILE', 'SEQUENCE'
]

AMR_SEPARATORS = {'RESISTANCE': ';', 'PRODUCT': ':'}


def process_csv_data(output_dir: Path, id_prefix: str = "csvDataTable", label: str = None):
    tables = []

    for index, file_path in enumerate(sorted(output_dir.glob("*.abricate.csv"))):
        table = {
            'filename': f"{label} / {file_path.name}" if label else file_path.name,
            'subrun': label,
            'table_id': f"{id_prefix}_{index}",
            'columns': AMR_COLUMNS,
        }

        try:
            with open(file_path, newline='', encoding='utf-8') as handle:
                reader = csv.DictReader(handle, delimiter='\t')

                missing = [c for c in AMR_COLUMNS
                           if c not in (reader.fieldnames or [])]
                if missing:
                    raise KeyError("missing columns: " + ", ".join(missing))

                table['rows'] = [
                    [split_cell(row.get(column) or "", AMR_SEPARATORS.get(column))
                     for column in AMR_COLUMNS]
                    for row in reader
                ]
        except Exception as e:
            table['error'] = str(e)

        tables.append(table)

    return tables


def split_cell(value: str, separator: str = None):
    return value.split(separator) if separator else [value]


def process_pathogen_plots(runid: str, unit_id: str, output_dir: Path):
    plots = []

    for page in sorted(output_dir.glob("*.html")):
        if "final_report." in page.name:
            continue

        png = page.with_suffix(".png")

        plots.append({
            'filename': f"{unit_id} / {page.name}",
            'subrun': unit_id,
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

    summary_data = []
    csv_data = []
    pathogen_data = []
    log_parts = []

    for index, (unit_id, run_dir) in enumerate(units):
        for section in parse_summary_file(run_dir / f"{unit_id}.summary"):
            section['header'] = f"[{unit_id}] {section['header']}"
            section['subrun'] = unit_id
            summary_data.append(section)

        csv_data += process_csv_data(
            run_dir, id_prefix=f"csvDataTable_u{index}", label=unit_id)

        pathogen_data += process_pathogen_plots(runid, unit_id, run_dir)

        log_parts.append(f"===== sub-run {unit_id} =====\n"
                         + read_log(run_dir, unit_id))

    # Render Template
    return render_template(
        'report.html',
        runid=runid,
        status=run_status(runid),
        revision=run_revision(runid),
        subruns=[unit_id for unit_id, _dir in units],
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
        logger.info(f"Found {len(pod5_filenames)} POD5 files: {pod5_filenames}")

        info_path.write_text(
            f"runid\t{runid}\n"
            f"readpath\t{readpath}\n"
            f"pod5\t{','.join(pod5_filenames)}\n"
            + tools_line
        )
        print(f"Success: wrote {info_path}")

    except PermissionError:
        logger.info(f"CRITICAL ERROR: Permission denied. Cannot write to {run_dir}.")
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
