#! /usr/bin/python3
# Re-run the experiments listed in the __main__ section of scripts/main_run.py
# (commented-out entries included), then evaluate them.
#
# Usage (from /opt/rica_s):
#   python3 -m scripts.run_experiments              # all runs
#   python3 -m scripts.run_experiments RUNID ...    # only these runs
#
# Each run gets its own process: start_run configures logging once per process,
# so later runs in a shared process would log into the first run's directory.
# Results in output/<runid>/ and evaluation/<runid>/ are overwritten.

import os
import re
import subprocess
import sys

from scripts.config import PROJECT_HOME, read_run_info

PY = sys.executable

src = open(os.path.join(PROJECT_HOME, "scripts", "main_run.py")).read()
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

    truth_p = os.path.join(readpath, f"gt_P_{runid}.tsv")
    truth_a = os.path.join(readpath, f"gt_A_{runid}.tsv")
    if os.path.isfile(truth_p) and os.path.isfile(truth_a):
        subprocess.run([PY, "-m", "scripts.evaluate_run", runid, "--pathogens", truth_p, "--amr", truth_a,
                        "--outdir", os.path.join("evaluation", runid)], cwd=PROJECT_HOME)

subprocess.run([PY, "-m", "scripts.evaluate_resources"], cwd=PROJECT_HOME)
