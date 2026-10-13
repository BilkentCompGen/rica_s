"""The analysis tools the pipeline can run, and which of them are selectable.

A tool is a directory under scripts/ whose name is also its Docker container
name (and its compose container_name), so the filesystem is the authoritative
list of what is installed. Docker is only asked which of those containers
happen to be up right now.

Basecalling and the human-DNA filter are deliberately absent: they run on every
run and are not selectable.
"""

import os

from scripts.config import PROJECT_HOME

KIND_PREFIX = {"id": "rica_s_id_", "pr": "rica_s_pr_"}
KIND_TITLE = {"id": "Classification", "pr": "Profiling"}
KIND_ORDER = ("id", "pr")

# Presentation only. Anything missing falls back to the prefix-stripped
# directory name, so adding a tool never requires editing this.
DISPLAY_NAMES = {
    "rica_s_id_blast": "BLAST",
    "rica_s_id_bwa": "BWA",
    "rica_s_id_clark": "CLARK",
    "rica_s_id_cuclark": "CuCLARK",
    "rica_s_id_kraken2": "Kraken2",
    "rica_s_id_minimap2": "minimap2",
    "rica_s_id_ngmlr": "NGMLR",
    "rica_s_pr_abricate": "ABRicate",
    "rica_s_pr_l-easyarg": "L-easyARG",
}


def discover_tools(kind):
    """Installed container names of one kind, sorted.

    Sorted because os.listdir returns directory order, which is not stable
    between runs and would otherwise reorder the pipeline arbitrarily.
    """
    prefix = KIND_PREFIX[kind]
    scripts_dir = os.path.join(PROJECT_HOME, "scripts")
    return sorted(
        name for name in os.listdir(scripts_dir)
        if name.startswith(prefix)
        and os.path.isdir(os.path.join(scripts_dir, name))
    )


def all_tools():
    """Every selectable container name, across all kinds."""
    return [name for kind in KIND_ORDER for name in discover_tools(kind)]


def display_name(container_name):
    if container_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[container_name]
    for prefix in KIND_PREFIX.values():
        if container_name.startswith(prefix):
            return container_name[len(prefix):]
    return container_name


def running_container_names():
    """Names of running containers, or None when Docker cannot be queried.

    None is distinct from the empty set on purpose: "we don't know" must not be
    rendered as "nothing is running", which would grey out the whole form and
    let a transient Docker hiccup produce a run with no tools.

    docker is imported here rather than at module scope so the start page still
    renders if the SDK is missing.
    """
    try:
        import docker

        client = docker.from_env()
        return {container.name for container in client.containers.list()}
    except Exception:
        return None


def tool_groups():
    """(groups, docker_ok) for the start page.

    groups: [{"kind", "title", "tools": [{"name", "display", "running"}]}]
    """
    running = running_container_names()
    docker_ok = running is not None

    groups = []
    for kind in KIND_ORDER:
        groups.append({
            "kind": kind,
            "title": KIND_TITLE[kind],
            "tools": [{
                "name": name,
                "display": display_name(name),
                # Fail open: unknown Docker state shows everything as available.
                "running": True if running is None else name in running,
            } for name in discover_tools(kind)],
        })
    return groups, docker_ok


def selected_tools(kind, selection):
    """Container names of `kind` to actually run.

    selection is None for .info files written before the tool selector existed,
    and for the CLI entry point; None means "run everything", the old behavior.
    An empty list is a deliberate "run nothing" and is preserved as such.

    Everything in selection is intersected with what is installed, so a hand
    edited .info or a crafted POST can never reach containers.get() or the
    scripts/<name>/classify.sh path join.
    """
    available = discover_tools(kind)
    if selection is None:
        return available
    wanted = set(selection)
    return [name for name in available if name in wanted]
