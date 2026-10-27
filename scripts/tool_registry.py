import os

from scripts.config import PROJECT_HOME

KIND_PREFIX = {"id": "rica_s_id_", "pr": "rica_s_pr_"}
KIND_TITLE = {"id": "Identifiers", "pr": "AMR gene detectors"}
KIND_SCRIPT = {"id": "classify.sh", "pr": "profile.sh"}
KIND_ORDER = ("id", "pr")

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


def container_states():
    # {container name: running?} for every container Docker knows, or None if Docker is unreachable
    try:
        import docker

        client = docker.from_env()
        return {c.name: c.status == "running" for c in client.containers.list(all=True)}
    except Exception:
        return None


def script_dirs():
    scripts_dir = f"{PROJECT_HOME}/scripts"
    return [name for name in os.listdir(scripts_dir) if os.path.isdir(f"{scripts_dir}/{name}")]


def has_script(kind, name):
    return os.path.isfile(f"{PROJECT_HOME}/scripts/{name}/{KIND_SCRIPT[kind]}")


def discover_tools(kind, states=None):
    # containers are the source of truth; without Docker fall back to the script folders
    names = script_dirs() if states is None else states
    return sorted(name for name in names if name.startswith(KIND_PREFIX[kind]))


def tool_state(kind, name, states):
    if not has_script(kind, name):
        return "no script"
    if states is not None and not states.get(name):
        return "not running"
    return ""


def available_tools(kind, states):
    return [name for name in discover_tools(kind, states) if not tool_state(kind, name, states)]


def all_tools():
    states = container_states()
    return [name for kind in KIND_ORDER for name in available_tools(kind, states)]


def display_name(container_name):
    if container_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[container_name]
    for prefix in KIND_PREFIX.values():
        if container_name.startswith(prefix):
            return container_name[len(prefix):]
    return container_name


def tool_groups():
    states = container_states()
    docker_ok = states is not None

    groups = []
    for kind in KIND_ORDER:
        tools = []
        for name in discover_tools(kind, states):
            state = tool_state(kind, name, states)
            tools.append({
                "name": name,
                "display": display_name(name),
                "available": not state,
                "state": state,
            })
        groups.append({"kind": kind, "title": KIND_TITLE[kind], "tools": tools})
    return groups, docker_ok


def selected_tools(kind, selection):
    available = available_tools(kind, container_states())
    if selection is None:
        return available
    wanted = set(selection)
    return [name for name in available if name in wanted]
