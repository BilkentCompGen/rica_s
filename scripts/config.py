import os
import re

PROJECT_HOME ="/opt/rica_s"
OUTPUT_ROOT = os.path.join(PROJECT_HOME, "output")

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


# Output layout
#
# A run is one directory. Each pod5 file of that run is processed as a sub-run
# named "<runid>_<index>", living inside the run's own directory:
#
#   output/<runid>/<runid>.info
#   output/<runid>/<runid>_0/
#   output/<runid>/<runid>_1/
#
# The parent is always passed explicitly. It cannot be recovered by stripping a
# trailing "_<digits>" from a sub-run id, because run ids are themselves
# timestamps ending in "_<digits>" (see templates/start.html).


def run_outdir(runid, parent=None):
    """Absolute output directory for a run. Sub-runs nest under their parent run.

    Passing parent == runid is the same as passing no parent, so a caller may
    forward its own parent argument unconditionally.
    """
    if parent and parent != runid:
        return os.path.join(OUTPUT_ROOT, parent, runid)
    return os.path.join(OUTPUT_ROOT, runid)


def subrun_dirs(runid):
    """Sub-runs of runid as an ordered list of (index, subrun_id, abs_path).

    Ordered numerically, so "_9" comes before "_10".
    """
    base = run_outdir(runid)
    if not os.path.isdir(base):
        return []

    # runid comes from a free-text form field, so it may contain regex
    # metacharacters. Anchoring on the known parent is what makes matching the
    # "_<index>" suffix unambiguous here.
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
    """Every "key<TAB>value" line of a <runid>.info file, as a dict.

    Parsed by key rather than by line position, so a missing or reordered field
    degrades to an absent key instead of an IndexError.
    """
    fields = {}
    with open(info_path, "r") as fd:
        for line in fd:
            if "\t" not in line:
                continue
            key, value = line.split("\t", 1)
            fields[key.strip()] = value.strip()
    return fields


def run_info_tuple(fields):
    """(runid, readpath, [pod5 names]) out of already-parsed fields."""
    names = sorted(
        n for n in (part.strip() for part in fields.get("pod5", "").split(",")) if n
    )
    return fields.get("runid", ""), fields.get("readpath", ""), names


def run_info_tools(fields):
    """Selected container names, or None when the file has no "tools" field.

    None means "run everything": that is what every .info written before the
    tool selector existed means. It is deliberately distinct from an empty
    list, which is a real "the user selected nothing". The distinction survives
    the round trip because "tools\t\n" still contains a tab, so the key lands
    in fields with an empty value, while an older file has no key at all.
    """
    if "tools" not in fields:
        return None
    return [t for t in (part.strip() for part in fields["tools"].split(",")) if t]


def parse_run_info(info_path):
    """Read a <runid>.info file into (runid, readpath, [pod5 names]).

    Kept at three values so existing callers that index or unpack it are
    unaffected; the tool selection is read separately via run_info_tools.
    """
    return run_info_tuple(read_run_info(info_path))
