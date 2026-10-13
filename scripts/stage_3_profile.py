import os
import datetime
import docker
from scripts.config import PROJECT_HOME, run_outdir
from scripts.tool_registry import selected_tools
import logging

logger = logging.getLogger(__name__)


def all_profile(runid, inputfile, parent=None, tools=None):
    logger.info("[i]> Begin of profiling stage")
    logger.info(datetime.datetime.now())

    outdir = run_outdir(runid, parent)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")

    # tools is None for runs started before the selector existed, and from the
    # CLI; that means "run everything", which is the original behavior.
    containers = selected_tools("pr", tools)
    logger.info(f"[i]> profiling tools: {', '.join(containers) or 'none'}")

    client = docker.from_env()

    for container_name in containers:
        script_path = os.path.join(
            PROJECT_HOME, "scripts", container_name, "profile.sh")
        try:
            container = client.containers.get(container_name)
            logger.info(f"[i]> {container.name} ===")

            exit_code, output_stream = container.exec_run(cmd=[script_path, inputfile, outdir],
                                                          tty=True,
                                                          stream=True
                                                          )
            logger.info(f"[i]> === {container.name}")

            with open(logfile, "a") as log:
                for chunk in output_stream:
                    text_chunk = chunk.decode("utf-8", errors="replace")
                    print(text_chunk, end="")
                    log.write(text_chunk)
                    log.flush()
        # logger, not log: log is bound inside the with-block above, so it is
        # unbound here on the first container and closed on any later one.
        except docker.errors.NotFound:
            logger.error(f"[e]> container {container_name} not found; skipping.")
        except Exception:
            logger.exception(f"[e]> error running in {container_name}")

    logger.info(datetime.datetime.now())
    logger.info("[i]> End of profiling stage")
