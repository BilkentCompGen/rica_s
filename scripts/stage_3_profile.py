import os
import datetime
import docker
from config import PROJECT_HOME

def all_profile(runid, inputfile):
    print("[i]> Begin of profiling stage")
    print(datetime.datetime.now())
    
    outdir = os.path.join(PROJECT_HOME, "output", runid)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")
    
    scripts_dir = os.path.join(PROJECT_HOME, "scripts")
    containers = [c for c in os.listdir(scripts_dir) if c.startswith("rica_s_pr_")]
    
    client = docker.from_env()

    for container_name in containers:
        script_path = os.path.join(PROJECT_HOME, "scripts", container_name, "profile.sh")
        try:
            container = client.containers.get(container_name)
            exit_code, output_stream = container.exec_run(
                cmd=[script_path, inputfile, os.path.join("/opt/rica_s/output/", runid)],
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
            log.write(f"Container {container_name} not found.\n")
        except Exception as e:
            log.write(f"Error running in {container_name}: {e}\n")
            
    print(datetime.datetime.now())
    print("[i]> End of profiling stage")