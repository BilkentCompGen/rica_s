import os
import datetime
import docker
from config import PROJECT_HOME


def all_basecall(runid, inputfile):
    print("[i]> Begin of Basecalling stage")
    print(datetime.datetime.now())

    outdir = os.path.join(PROJECT_HOME, "output", runid)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")

    script_path = os.path.join(
        PROJECT_HOME, "scripts", "rica_s_bc_dorado", "basecall.sh")

    # Connect to Docker API
    client = docker.from_env()

    try:
        container = client.containers.get("rica_s_bc_dorado")
        exit_code, output_stream = container.exec_run(
            cmd=[script_path, inputfile, outdir],
            tty=True,
            stream=True
        )

        with open(logfile, "a") as log:
            for chunk in output_stream:
                text_chunk = chunk.decode("utf-8", errors="replace")
                print(text_chunk, end="")
                log.write(text_chunk)
                log.flush()

    except docker.errors.NotFound:
        print("Error: Container 'rica_s_bc_dorado' not found.")
    except Exception as e:
        print(f"Docker API Error: {e}")

    print(datetime.datetime.now())
    print("[i]> End of Basecalling stage")
