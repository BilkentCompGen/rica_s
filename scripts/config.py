import os
import re

PROJECT_HOME ="/opt/rica_s"
OUTPUT_ROOT = f"{PROJECT_HOME}/output"

c = {
    "PROJECT_HOME": PROJECT_HOME,
    "DL_DIR": PROJECT_HOME,
    "OUT_DIR": OUTPUT_ROOT,
    "BASE_URL": "http://donut.cs.bilkent.edu.tr/rica_s",
    "FLASK_PORT":5000,
    "DOCKER_HOST_IP":"172.20.0.1",
    "DOCKER_HOST_PORT":"667",
    "HOST_ROOT":"/"
}


def run_outdir(runid, parent=None):
    if parent and parent != runid:
        return f"{OUTPUT_ROOT}/{parent}/{runid}"
    return f"{OUTPUT_ROOT}/{runid}"


def subrun_dirs(runid):
    base = run_outdir(runid)
    if not os.path.isdir(base):
        return []

    pattern = re.compile(r"^" + re.escape(runid) + r"_(\d+)$")

    found = []
    for entry in os.scandir(base):
        if not entry.is_dir():
            continue
        m = pattern.match(entry.name)
        if m:
            found.append((int(m.group(1)), entry.name, entry.path))

    found.sort(key=lambda t: (t[0], t[1]))
    return found


def read_run_info(info_path):
    fields = {}
    with open(info_path, "r") as fd:
        for line in fd:
            if "\t" not in line:
                continue
            key, value = line.split("\t", 1)
            fields[key.strip()] = value.strip()
    return fields


def run_info_tuple(fields):
    names = sorted(
        n for n in (part.strip() for part in fields.get("pod5", "").split(",")) if n
    )
    return fields.get("runid", ""), fields.get("readpath", ""), names


def run_info_tools(fields):
    if "tools" not in fields:
        return None
    return [t for t in (part.strip() for part in fields["tools"].split(",")) if t]


def parse_run_info(info_path):
    return run_info_tuple(read_run_info(info_path))
