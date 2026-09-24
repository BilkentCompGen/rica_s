import os
import datetime
import docker
from scripts.config import PROJECT_HOME, run_outdir
import logging
import subprocess

logger = logging.getLogger(__name__)

def all_basecall(runid, inputfile, parent=None):
    logger.info("[i]> Begin of Basecalling stage")
    logger.info(datetime.datetime.now())

    outdir = run_outdir(runid, parent)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")

    script_path = os.path.join(
        PROJECT_HOME, "scripts", "rica_s_bc_dorado", "basecall.sh")

    logger.info("[i]> rica_s_bc_dorado ===")


    # Connect to Docker API
    client = docker.from_env()

    try:
        container = client.containers.get("rica_s_bc_dorado")
        logger.info(f"[i]> {container.name} ===")

        exit_code, output_stream = container.exec_run(
            cmd=[script_path, inputfile, outdir],
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

    except docker.errors.NotFound:
        logger.error("Error: Container 'rica_s_bc_dorado' not found.")
    except Exception as e:
        logger.error(f"Docker API Error: {e}")

    logger.info(datetime.datetime.now())
    logger.info("[i]> End of Basecalling stage")
