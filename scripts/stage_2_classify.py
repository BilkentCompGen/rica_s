import os
import subprocess
import datetime
import docker
from config import PROJECT_HOME

def all_classify(runid, inputfile):
    print("[i]> Begin of classification stage")
    print(datetime.datetime.now())
    
    outdir = os.path.join(PROJECT_HOME, "output", runid)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")
    
    scripts_dir = os.path.join(PROJECT_HOME, "scripts")
    containers = [c for c in os.listdir(scripts_dir) if c.startswith("rica_s_id_")]
    
    client = docker.from_env()
    
    for container_name in containers:
        script_path = os.path.join(PROJECT_HOME, "scripts", container_name, "classify.sh")
        try:
            container = client.containers.get(container_name)
            # Setting the environment variables identical to the previous CLI command
            env_vars = {
                "TERM": "xterm", 
                "COLUMNS": "80", 
                "LINES": "24", 
                "MALLOC_ARENA_MAX": "2"
            }
            
            exit_code, output_stream = container.exec_run(
                cmd=[script_path, inputfile, os.path.join("/opt/rica_s/output/", runid)],
                environment=env_vars,
                tty=True,
                stream=True
            )

            with open(logfile, "a") as log:
                for chunk in output_stream:
                    text_chunk = chunk.decode("utf-8", errors="replace")
                    print(text_chunk, end="")
                    log.write(text_chunk)
                    log.flush()
                    log.write("\n\n")

            
        except docker.errors.NotFound:
            log.write(f"Container {container_name} not found.\n")
        except Exception as e:
            log.write(f"Error running in {container_name}: {e}\n")
        
    # Executing external dependencies via local shell
    taxid_script = os.path.join(PROJECT_HOME, "scripts", "misc", "replace_taxid_for_spp_tsv.sh")
    acc_script = os.path.join(PROJECT_HOME, "scripts", "misc", "replace_acc_for_spp_tsv.sh")
    subprocess.run(f"sh {taxid_script} 1 /opt/rica_s/output/{runid}/*.tsv", shell=True)
    subprocess.run(f"sh {acc_script} 1 /opt/rica_s/output/{runid}/*.tsv", shell=True)
    
    print(datetime.datetime.now())
    print("[i]> End of classification stage")