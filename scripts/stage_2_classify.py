import os
import subprocess
import datetime
import docker
import pandas as pd
from scripts.config import PROJECT_HOME, run_outdir, c
from scripts.misc.name_resolver import NameResolver
from scripts.tool_registry import selected_tools
import logging
import re
import glob
import csv

logger = logging.getLogger(__name__)


def check_accession(s):
    reg_ex = r"\b(?:PMC\d+|[A-Z]{2}_[A-Z]{0,6}\d{5,}(?:\.\d+)?|[A-Z]{1,3}\d{5,7}(?:\.\d+)?|[A-Z]{4,6}\d{8,}(?:\.\d+)?|PRJ[A-Z]{2}\d+|SAM[A-Z]{1,2}\d+|[SDE]R[RXSP]\d{6,})\b"
    r = re.findall(reg_ex, s)
    if len(r) > 0: 
        return (True, r[0])
    else:
        return (False, s)


def check_taxid(s):
    if "taxid|" in s:
        v = s.split("taxid|")[1]
        v = v.split()[0]
        return (True, v)
    else:
        return (False, s)



def process_cell(val, t: NameResolver):
    
    is_accession, spp_from_acc = check_accession(val)
    if is_accession:
        return t.accession2name(spp_from_acc)
    else:
        is_taxid, spp_from_taxid = check_taxid(val)
        if is_taxid:
            return t.tax2name(spp_from_taxid)
        else:
            return val






def fix_names(tsv_files):
    t = NameResolver("/opt/rica_s/scripts/misc/spp.csv")
    
    for target_tsv in tsv_files:
        try:
            if os.path.getsize(target_tsv) > 0:
                with open(target_tsv, "r", encoding="utf-8") as fileR:
                    reader = csv.reader(fileR, delimiter="\t")
                    rows = list(reader)
                    for row in rows:
                        row[0] = process_cell(row[0], t)
                    with open(target_tsv, "w", encoding="utf-8") as fileW:
                        writer = csv.writer(fileW, delimiter="\t")
                        writer.writerows(rows)
                
        except Exception as e:
            print(e)
        print("[*] Done.")


def all_classify(runid, inputfile, parent=None, tools=None):
    logger.info("[i]> Begin of classification stage")
    logger.info(datetime.datetime.now())

    outdir = run_outdir(runid, parent)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(outdir, f"{runid}.log")

    # tools is None for runs started before the selector existed, and from the
    # CLI; that means "run everything", which is the original behavior.
    containers = selected_tools("id", tools)
    logger.info(f"[i]> classification tools: {', '.join(containers) or 'none'}")

    client = docker.from_env()

    for container_name in containers:
        script_path = os.path.join(
            PROJECT_HOME, "scripts", container_name, "classify.sh")
        try:
            container = client.containers.get(container_name)
            # Setting the environment variables identical to the previous CLI command
            env_vars = {
                "TERM": "xterm",
                "COLUMNS": "80",
                "LINES": "24",
                "MALLOC_ARENA_MAX": "2"
            }
            logger.info(f"[i]> {container.name} ===")

            exit_code, output_stream = container.exec_run(
                cmd=[script_path, inputfile, outdir],
                environment=env_vars,
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
                    log.write("\n\n")

        # logger, not log: log is bound inside the with-block above, so it is
        # unbound here on the first container and closed on any later one.
        except docker.errors.NotFound:
            logger.error(f"[e]> container {container_name} not found; skipping.")
        except Exception:
            logger.exception(f"[e]> error running in {container_name}")

    # taxid_script = os.path.join(
    #     PROJECT_HOME, "scripts", "misc", "replace_taxid_for_spp_tsv.sh")
    # acc_script = os.path.join(PROJECT_HOME, "scripts",
    #                           "misc", "replace_acc_for_spp_tsv.sh")
    # subprocess.run(f"sh {taxid_script} 1 {outdir}/*.tsv", shell=True)
    # subprocess.run(f"sh {acc_script} 1 {outdir}/*.tsv", shell=True)

    tsv_files = glob.glob(os.path.join(outdir, "*.tsv"))
    fix_names(tsv_files)

    logger.info(datetime.datetime.now())
    logger.info("[i]> End of classification stage")
