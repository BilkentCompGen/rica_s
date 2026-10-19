import os

from scripts.config import PROJECT_HOME

KIND_PREFIX = {"id": "rica_s_id_", "pr": "rica_s_pr_"}
KIND_TITLE = {"id": "Classification", "pr": "Profiling"}
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


def discover_tools(kind):
    prefix = KIND_PREFIX[kind]
    scripts_dir = f"{PROJECT_HOME}/scripts"
    return sorted(
        name for name in os.listdir(scripts_dir)
        if name.startswith(prefix)
        and os.path.isdir(f"{scripts_dir}/{name}")
    )


def all_tools():
    return [name for kind in KIND_ORDER for name in discover_tools(kind)]


def display_name(container_name):
    if container_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[container_name]
    for prefix in KIND_PREFIX.values():
        if container_name.startswith(prefix):
            return container_name[len(prefix):]
    return container_name


def running_container_names():
    try:
        import docker

        client = docker.from_env()
        return {container.name for container in client.containers.list()}
    except Exception:
        return None


def tool_groups():
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
                "running": True if running is None else name in running,
            } for name in discover_tools(kind)],
        })
    return groups, docker_ok


def selected_tools(kind, selection):
    available = discover_tools(kind)
    if selection is None:
        return available
    wanted = set(selection)
    return [name for name in available if name in wanted]
