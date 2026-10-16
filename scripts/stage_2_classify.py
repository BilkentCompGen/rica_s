import sys
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



def extract_identifier(cell_value):
    """Parses a string to extract an NCBI Accession, TaxID, or Kraken TaxID."""
    val = str(cell_value).strip()
    if not val:
        return None
        
        
    # 3. NCBI Accession / Genome / Reference number
    # Matches formats like NC_010397.1, NZ_BAABHT010000001.1, CP068211
    # Looks for 1-6 capital letters, optional underscore, 4-15 digits, and optional .version
    match = re.search(r"\b(?:PMC\d+|[A-Z]{2}_[A-Z]{0,6}\d{5,}(?:\.\d+)?|[A-Z]{1,3}\d{5,7}(?:\.\d+)?|[A-Z]{4,6}\d{8,}(?:\.\d+)?|PRJ[A-Z]{2}\d+|SAM[A-Z]{1,2}\d+|[SDE]R[RXSP]\d{6,})\b", val)
    if match:
        return match.group()

    # 2. Taxonomical ID (strictly digits)
    if val.isdigit():
        return val

    # 1. Kraken format (e.g., "taxid|1234" or "kraken:taxid|1234")
    if "taxid|" in val:
        return val.split("taxid|")[1].split()[0]
            
    return None

def fix_names(filepath, nr, delimiter="\t"):
    # Skip completely empty 0-byte files to prevent errors
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        logger.info(f"[-] Skipping {filepath}: File is empty.")
        return

    temp_file = filepath + ".tmp"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as fin, \
             open(temp_file, 'w', encoding='utf-8', newline='') as fout:
             
            reader = csv.reader(fin, delimiter=delimiter)
            writer = csv.writer(fout, delimiter=delimiter)
            
            for row in reader:
                # Ensure the row actually has data before trying to access index 0
                if row and len(row) > 0:
                    
                    # Step 1: Parse the first column for the identifier
                    extracted_id = extract_identifier(row[0])
                    
                    # Step 2: If a valid ID is found, pass it to id2spp()
                    if extracted_id:
                        resolved_name = nr.id2spp(extracted_id)
                        
                        # Step 3: Replace column 1 only if id2spp returns a valid, non-empty string
                        if resolved_name and str(resolved_name).strip():
                            row[0] = resolved_name
                            
                # Write the row to the temp file (either modified or exactly as it was)
                writer.writerow(row)
                
        # Safely overwrite the original file with the completed temp file
        os.replace(temp_file, filepath)
        logger.info(f"[*] Successfully processed {filepath}")
        
    except Exception as e:
        logger.info(f"[!] Error processing {filepath}: {e}")
        # Clean up the temp file if the script crashes halfway through
        if os.path.exists(temp_file):
            os.remove(temp_file)



def merge_repeats(filepath, delimiter="\t"):
    # Skip completely empty or missing files
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        logger.info(f"[-] Skipping {filepath}: File is empty or missing.")
        return

    merged_data = {}
    temp_file = filepath + ".tmp"
    
    try:
        # 1. Read and accumulate sums
        with open(filepath, 'r', encoding='utf-8') as fin:
            reader = csv.reader(fin, delimiter=delimiter)
            
            for row in reader:
                # Ensure the row has at least 2 columns
                if len(row) >= 2:
                    search_query = row[0].strip()
                    
                    try:
                        # Attempt to parse the 2nd column as a float
                        # (Using float handles both ints and decimals)
                        value = float(row[1])
                    except ValueError:
                        # If it fails (e.g., it's a header like "Count" or "Abundance"), skip it
                        continue
                    
                    # Accumulate the sum
                    if search_query in merged_data:
                        merged_data[search_query] += value
                    else:
                        merged_data[search_query] = value
                        
        # 2. Write the merged dictionary back to a temporary file
        with open(temp_file, 'w', encoding='utf-8', newline='') as fout:
            writer = csv.writer(fout, delimiter=delimiter)
            
            for query, total in merged_data.items():
                # Clean up formatting: if the sum is exactly 5.0, print it as an integer '5'
                formatted_total = int(total) if total.is_integer() else total
                writer.writerow([query, formatted_total])
                
        # 3. Replace the original file
        os.replace(temp_file, filepath)
        logger.info(f"[*] Successfully merged counts for {filepath}")
        
    except Exception as e:
        logger.info(f"[!] Error processing {filepath}: {e}")
        # Clean up the temp file if something crashes
        if os.path.exists(temp_file):
            os.remove(temp_file)
    return




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



    logger.info("[i]> Fixing TSVs")
    tsv_files = glob.glob(os.path.join(outdir, "*.tsv"))
    nr=NameResolver("/opt/rica_s/scripts/misc/spp.tar.gz")

    for tsv in tsv_files:
        fix_names(tsv,nr)
        merge_repeats(tsv)

    logger.info(datetime.datetime.now())
    logger.info("[i]> End of classification stage")




############################################################################
############################################################################
############################################################################
if __name__ == "__main__":
    
    if sys.argv[1] == "fix_names":
        search_pattern = os.path.join(sys.argv[2], "**", "*.tsv")
        tsvs = glob.glob(search_pattern, recursive=True)
        nr=NameResolver("/opt/rica_s/scripts/misc/spp.tar.gz")

        for tsv in tsvs:
            # if("05B_0.001A_1H_0_aggregate" in tsv):
            #     print("here")
            fix_names(tsv,nr)
            merge_repeats(tsv)