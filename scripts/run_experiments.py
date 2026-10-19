#! /usr/bin/python3
# Usage (from /opt/rica_s):
#   python3 -m scripts.run_experiments              # all runs
#   python3 -m scripts.run_experiments RUNID ...    # only these runs

import os
import re
import subprocess
import sys

from scripts.config import PROJECT_HOME, read_run_info

PY = sys.executable

src = open(f"{PROJECT_HOME}/scripts/main_run.py").read()
main_block = src[src.index('if __name__ == "__main__":'):]
infos = list(dict.fromkeys(re.findall(r"""["'](/[^"']+\.info)["']""", main_block)))

for info in infos:
    fields = read_run_info(info)
    runid, readpath = fields["runid"], fields["readpath"]
    if sys.argv[1:] and runid not in sys.argv[1:]:
        continue
    print(f"[i]> {runid}", flush=True)

    subprocess.run([PY, "-c", "import sys; from scripts.main_run import start_run; start_run(sys.argv[1])", info],
                   cwd=PROJECT_HOME)

    truth_p = f"{readpath}/gt_P_{runid}.tsv"
    truth_a = f"{readpath}/gt_A_{runid}.tsv"
    if os.path.isfile(truth_p) and os.path.isfile(truth_a):
        subprocess.run([PY, "-m", "scripts.evaluate_run", runid, "--pathogens", truth_p, "--amr", truth_a,
                        "--outdir", f"evaluation/{runid}"], cwd=PROJECT_HOME)

subprocess.run([PY, "-m", "scripts.evaluate_resources"], cwd=PROJECT_HOME)
