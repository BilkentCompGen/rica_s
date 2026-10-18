#!/bin/bash
# Recreate the time/memory usage report for the runs in output/.
#
# Usage (from anywhere):
#   scripts/misc/run_resources.sh              # every directory in output/, plus the overview
#   scripts/misc/run_resources.sh DIR [DIR...] # only these output directories (no overview)
#
# What it does (implemented in scripts/evaluate_resources.py):
#   1. Reads every pipeline log output/<DIR>/<DIR>.log and splits it into runs at
#      "Begin of sepsis detection". Runs are attributed by their "run ID:" line,
#      not by the file they are in: while the web UI is up, a run is often logged
#      into ANOTHER directory's log. Duplicate runs (same ID and start) are dropped.
#   2. Per run: stage times from "Begin/End of <stage> stage"; tool wall time from
#      "[i]> <tool> ===" to the first log line after "[i]> === <tool>"; metadata
#      steps ("getting/fetching ... metadata") to the next line; gaps > 30 s that
#      nothing covers. A gap right after "End of reporting stage" is idle (main_run
#      does no work there) and is excluded from "active time"; other gaps are
#      unlogged work (e.g. FASTQ statistics after basecalling in older versions).
#   3. Reads the tool log output/<DIR>/<DIR>_N/<DIR>_N.log, where every tool is
#      wrapped in /usr/bin/time ("T> elapsed", "M> max RSS KB"). Entries carry no
#      tool name, so each is labeled from the tool output just before it (Dorado,
#      human-filter minimap2, BWA, CLARK, CuCLARK, Kraken2, minimap2, NGMLR,
#      ABRicate per database, L-easyARG; an otherwise empty chunk is BLAST).
#   4. Uses the run that executed the most tools as the directory's primary run.
#   5. Writes evaluation/<DIR>/resources_* (report .md, .tsv tables, 3 plots) and
#      evaluation/resources_overview/ (summary tables, 2 cross-directory plots).
#      Only resources_* files are written; nothing else in evaluation/ is touched
#      and nothing is deleted.

set -euo pipefail

PROJECT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_HOME"

python3 -m scripts.evaluate_resources "$@"
