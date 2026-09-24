import pandas as pd
from flask import Flask, render_template, request, jsonify
from flask import abort, send_from_directory, url_for
from pathlib import Path
import docker
import os
import datetime
import time
import logging
# from ..config import c

from scripts.config import c, run_outdir, subrun_dirs, parse_run_info

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


def get_run_status(runid: str, parent: str = None):
    """Fetches the status from the run's .status file."""
    status = _read_status(Path(run_outdir(runid, parent)), runid)
    return status if status else "no run ID"


def get_log_text(runid: str, parent: str = None):
    """Fetches the log text for a single run directory."""
    log_file = Path(run_outdir(runid, parent)) / f"{runid}.log"

    if log_file.exists():
        # Logs are tool stdout, so a partially written multi-byte sequence in a
        # live log must not take the whole page down.
        return log_file.read_text(encoding='utf-8', errors='replace')
    return "no log found"


def _read_status(unit_dir: Path, unit_id: str):
    """Raw status string for one run directory, or None when absent.

    Distinct from get_run_status: the rollup needs to tell "missing" apart from
    an actual status value.
    """
    status_file = unit_dir / f"{unit_id}.status"
    if status_file.exists():
        return status_file.read_text(encoding='utf-8').strip()
    return None


def _has_own_artifacts(base: Path, runid: str):
    """True when a run directory holds artifacts directly, rather than only sub-runs.

    This is what lets pre-nesting flat run directories keep rendering.
    """
    if any((base / f"{runid}{ext}").exists()
           for ext in (".status", ".summary", ".log")):
        return True
    return any(base.glob("*.abricate.csv")) or any(base.glob("*.html"))


def discover_run_units(runid: str):
    """Directories holding artifacts for a run id, as ordered [{'id', 'dir'}].

    A nested run contributes its sub-runs. A flat run directory from before the
    nesting change contributes itself. Each directory is only ever globbed
    non-recursively, so a parent scan never picks up a sub-run's files.
    """
    base = Path(run_outdir(runid))
    if not base.is_dir():
        return []

    units = []
    if _has_own_artifacts(base, runid):
        units.append({"id": runid, "dir": base})
    for _index, name, path in subrun_dirs(runid):
        units.append({"id": name, "dir": Path(path)})
    return units


def resolve_unit_dir(runid: str, unit_id: str):
    """Validate unit_id as a run unit of runid and return its directory, else None."""
    if unit_id == runid:
        base = Path(run_outdir(runid))
        return base if base.is_dir() else None
    for _index, name, path in subrun_dirs(runid):
        if name == unit_id:
            return Path(path)
    return None


def _expected_subrun_count(runid: str):
    """How many sub-runs the .info calls for, or None when that is unknowable."""
    info = Path(run_outdir(runid)) / f"{runid}.info"
    if not info.exists():
        return None
    try:
        return len(parse_run_info(info)[2])
    except Exception:
        return None


def aggregate_run_status(runid: str):
    """Roll the sub-run statuses of a run up into one of the four UI strings."""
    base = Path(run_outdir(runid))
    if not base.is_dir():
        return "no run ID"

    subs = subrun_dirs(runid)

    if not subs:
        own = _read_status(base, runid)
        if own:
            return own
        # Submitted but the listener has not created a sub-run directory yet.
        # Reporting "no run ID" here would show a just-accepted run as an error.
        return "started" if (base / f"{runid}.info").exists() else "no run ID"

    statuses = [s for s in (_read_status(Path(path), name)
                            for _index, name, path in subs) if s]
    if not statuses:
        return "started"

    if "killed" in statuses:
        return "killed"

    # Sub-runs execute sequentially, so "every status found says finished" is
    # true in the gap between one sub-run finishing and the next one starting.
    # Compare against the pod5 count to avoid reporting a run done early.
    expected = _expected_subrun_count(runid)
    complete = expected is None or len(subs) >= expected
    if complete and all(s == "finished" for s in statuses):
        return "finished"
    return "started"


def process_csv_data(output_dir: Path, id_prefix: str = "csvDataTable", label: str = None):
    """Finds and formats AMR CSV files into HTML tables.

    id_prefix keeps table ids unique across an aggregated report; DataTables
    derives its wrapper element ids from the table id, so duplicates collide.
    """
    csv_data = []
    columns_to_keep = [
        'GENE', '%COVERAGE', '%IDENTITY', 'PRODUCT',
        'RESISTANCE', 'DATABASE', 'ACCESSION', '#FILE', 'SEQUENCE'
    ]

    # Sorted: Path.glob yields directory order, which is not stable across requests.
    for index, file_path in enumerate(sorted(output_dir.glob("*.abricate.csv"))):
        display = f"{label} / {file_path.name}" if label else file_path.name
        try:
            df = pd.read_csv(file_path, sep="\t")
            df = df[columns_to_keep]

            # Use <br> so the line breaks render correctly in the browser.
            # fillna/astype first: a column with no values at all is typed
            # float64 by read_csv, and .str on it raises.
            df['RESISTANCE'] = df['RESISTANCE'].fillna("").astype(str).str.replace(
                ';', '<br>', regex=False)
            df['PRODUCT'] = df['PRODUCT'].fillna("").astype(str).str.replace(
                ':', '<br>', regex=False)

            table_html = df.to_html(
                classes="display compact data-table",
                table_id=f"{id_prefix}_{index}",
                index=False,
                escape=False
            )

            csv_data.append({'filename': display,
                             'subrun': label,
                             'table_html': table_html})
        except Exception as e:
            csv_data.append({'filename': display,
                             'subrun': label,
                             'error': str(e)})

    return csv_data


def process_pathogen_htmls(runid: str, unit_id: str, output_dir: Path):
    """Lists pathogen plot files as URLs for the report to load lazily.

    These are standalone Plotly pages that each inline the whole plotly.js, at
    roughly 4.6 MB apiece. Embedding them in the page via srcdoc costs ~37 MB
    per sub-run before HTML escaping, so the report links to them instead and
    lets the browser fetch them on demand.
    """
    pathogen_data = []

    # Sort files and filter out the final report to prevent recursive loops
    html_files = sorted(output_dir.glob("*.html"))
    html_files = [f for f in html_files if "final_report." not in f.name]

    for file_path in html_files:
        pathogen_data.append({
            'filename': f"{unit_id} / {file_path.name}",
            'subrun': unit_id,
            'url': url_for('get_run_plot', runid=runid,
                           unit_id=unit_id, filename=file_path.name),
        })

    return pathogen_data


def to_real_path(display_path: str):
    """Map a host path as shown in the UI onto the mounted copy in this container."""
    if not display_path:
        display_path = '/'

    clean_display = os.path.normpath('/' + display_path.lstrip('/'))
    host_root = os.path.normpath(c.get("HOST_ROOT", "/"))

    if host_root == '/':
        return clean_display
    return os.path.normpath(os.path.join(host_root, clean_display.lstrip('/')))


def to_display_path(real_path: str):
    """Strip the mount prefix so the UI shows the path as it exists on the host."""
    real_path = os.path.normpath(real_path)
    host_root = os.path.normpath(c.get("HOST_ROOT", "/"))

    if host_root == '/':
        return real_path
    if real_path == host_root:
        return '/'
    if real_path.startswith(host_root + '/'):
        return real_path[len(host_root):]
    return '/'


@app.route('/api/folders')
def get_folders():
    host_root = os.path.normpath(c.get("HOST_ROOT", "/"))
    raw_path = request.args.get('path', '/')
    req_path = to_real_path(raw_path)

    # Fallback to host root if the requested path does not exist
    if not os.path.isdir(req_path):
        req_path = host_root

    try:
        # Prevent navigating above the mount root
        if req_path == host_root:
            parent = host_root
        else:
            parent = os.path.dirname(req_path)
            if not parent.startswith(host_root):
                parent = host_root

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
    cli = docker.DockerClient(
        base_url='tcp://'+c["DOCKER_HOST_IP"]+":"+c["DOCKER_HOST_PORT"])

    containers = cli.containers.list()

    # cont = containers[0]

    # # print([c.name for c in containers])

    stages = []
    # stages = [
    #     ["Stage 1: Sequencing", [c.name for c in containers if "sq_" in c.name]],
    #     ["Stage 2: Basecalling", [c.name for c in containers if "bc_" in c.name]],
    #     ["Stage 3: Identifying", [c.name for c in containers if "id_" in c.name]],
    #     ["Stage 4: Profiling", [c.name for c in containers if "pr_" in c.name]],
    #     ["Stage 5: Reporting", [c.name for c in containers if "rp_" in c.name]]
    # ]

    return render_template('start.html', stages=stages)


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
        "is_running": aggregate_run_status(runid)
    })


@app.route('/report/<runid>')
def generate_report(runid):
    """One page aggregating every sub-run of a run.

    Sections are labelled with the sub-run they came from by prefixing the
    strings the template already prints, so report.html needs no changes here.
    """
    units = discover_run_units(runid)

    summary_data = []
    csv_data = []
    pathogen_data = []
    log_parts = []

    for index, unit in enumerate(units):
        unit_id = unit["id"]
        unit_dir = unit["dir"]

        # 1. Summary sections, tagged with their sub-run
        for section in parse_summary_file(unit_dir / f"{unit_id}.summary"):
            section['header'] = f"[{unit_id}] {section['header']}"
            section['subrun'] = unit_id
            summary_data.append(section)

        # 2. AMR tables. The id prefix is per unit so DataTables ids stay unique.
        csv_data += process_csv_data(
            unit_dir, id_prefix=f"csvDataTable_u{index}", label=unit_id)

        # 3. Pathogen plots, as lazily fetched URLs
        pathogen_data += process_pathogen_htmls(runid, unit_id, unit_dir)

        # 4. Log
        log_parts.append(
            f"===== sub-run {unit_id} =====\n"
            + get_log_text(unit_id, runid if unit_id != runid else None)
        )

    # Render Template
    return render_template(
        'report.html',
        runid=runid,
        subruns=[unit["id"] for unit in units],
        summary_data=summary_data,
        log_text="\n\n".join(log_parts) if log_parts else "no log found",
        csv_data=csv_data,
        pathogen_data=pathogen_data
    )


@app.route('/report/<runid>/plot/<unit_id>/<filename>')
def get_run_plot(runid, unit_id, filename):
    """Serves one pathogen plot file so the report can iframe it lazily."""
    unit_dir = resolve_unit_dir(runid, unit_id)
    if unit_dir is None:
        abort(404)

    # Only ever serve a plain .html file from directly inside the unit dir.
    if filename != os.path.basename(filename) or not filename.endswith(".html"):
        abort(404)
    if "final_report." in filename:
        abort(404)

    return send_from_directory(unit_dir, filename)


################
# begins new experiment

@app.route('/submitted', methods=['POST'])
def submitted_page():
    readpath = request.form.get('tb_readpath')
    runid = request.form.get('tb_runid')
    run_dir = Path(run_outdir(runid))
    info_path = run_dir / f"{runid}.info"
    r = get_run_status(runid)
    if r:
        try:
            # 2. Attempt the creation
            run_dir.mkdir(parents=True, exist_ok=True)
            with open(info_path, "w") as f:
                print(info_path)

                f.write("runid\t"+runid+"\n")
                f.write("readpath\t"+readpath+"\n")

                print(f"searching pod5s in {readpath}")
                # Get a list of ONLY the file names (e.g., 'sample_01.pod5')
                pod5_filenames = [path.name for path in Path(
                    readpath).glob("*.pod5")]
                print(f"Found {len(pod5_filenames)} POD5 files.")
                print(pod5_filenames)
                # This list decides how many sub-runs there are, so join it
                # directly rather than scrubbing a repr of the list.
                f.write("pod5\t" + ",".join(sorted(pod5_filenames)) + "\n")

            print("Success: Filesystem operations completed.")

        # 3. Catch specific errors (like lack of write access to /opt/)
        except PermissionError:
            print(f"CRITICAL ERROR: Permission denied. Cannot write to {run_dir}.")
            print("Are you running this script with the correct user privileges?")
        except OSError as e:
            print(f"CRITICAL ERROR: An OS error occurred: {e}")
    return render_template(
        'submitted.html',
        r=r,
        runid=runid,
        readpath=readpath
    )


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
