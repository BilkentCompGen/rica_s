#! /usr/bin/python3
"""Rerun only the ABRicate profiling on runs that are already in output/.

For each sub-run it reruns ABRicate on the existing cleaned FASTA, then rebuilds
everything that is derived from the ABRicate CSV: the sub-run final report and
the run-level merged AMR table and plot. Basecalling, filtering, classification
and L-EasyARG are not touched.

Every file that would be overwritten is first copied to
<file>.pre_abricate_rerun_<timestamp>, so earlier results are kept.

Usage (from the project root):
    python3 -m scripts.rerun_abricate              # every run in output/
    python3 -m scripts.rerun_abricate RUNID ...    # only these runs
    python3 -m scripts.rerun_abricate --dry-run    # list what would be rerun
"""

import argparse
import datetime
import glob
import logging
import os
import shutil
import sys

from scripts.config import c, subrun_dirs
from scripts.main_run import (_attach_run_log, _detach_run_log,
                              merge_and_plot_amr_subruns)
from scripts.stage_3_profile import all_profile
from scripts.stage_5_report import all_report
from scripts.tool_registry import selected_tools

TOOL = "rica_s_pr_abricate"
logger = logging.getLogger("rerun_abricate")


def backup(path, tag):
    if os.path.isfile(path):
        shutil.copy2(path, f"{path}.{tag}")


def find_runs(wanted):
    runs = sorted(d for d in os.listdir(c["OUT_DIR"])
                  if os.path.isfile(f"{c['OUT_DIR']}/{d}/{d}.info"))
    if wanted:
        missing = sorted(set(wanted) - set(runs))
        if missing:
            sys.exit(f"[e]> not found in {c['OUT_DIR']}: {', '.join(missing)}")
        runs = [r for r in runs if r in wanted]
    return runs


def cleaned_fasta(subrun_path):
    # same name main_run.py gives the filter stage output
    hits = sorted(glob.glob(f"{subrun_path}/*.fastq.cleaned.fasta"))
    return hits[0] if len(hits) == 1 else None


def rerun(runid, tag):
    run_dir = f"{c['OUT_DIR']}/{runid}"
    log_handler = _attach_run_log(f"{run_dir}/{runid}.log")
    try:
        logger.info(f"[i]> === ABRicate rerun of {runid}")
        for _, sub_id, sub_path in subrun_dirs(runid):
            fasta = cleaned_fasta(sub_path)
            if fasta is None:
                logger.warning(f"[!]> {sub_id}: no single *.fastq.cleaned.fasta; skipping")
                continue

            for f in glob.glob(f"{sub_path}/*.abricate.csv"):
                backup(f, tag)
            backup(f"{sub_path}/{sub_id}_final_report.html", tag)

            all_profile(sub_id, fasta, runid, tools=[TOOL])
            all_report(sub_id, runid)

        backup(f"{run_dir}/{runid}_merged_amr.tsv", tag)
        backup(f"{run_dir}/{runid}_amr.png", tag)
        merge_and_plot_amr_subruns(runid, f"{run_dir}/{runid}")
        logger.info(f"[i]> ABRicate rerun of {runid} ===")
    finally:
        _detach_run_log(log_handler)


def main():
    parser = argparse.ArgumentParser(description="Rerun only ABRicate on runs in output/.")
    parser.add_argument("runids", nargs="*", help="runs to redo (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be rerun")
    args = parser.parse_args()

    runs = find_runs(args.runids)
    for r in runs:
        # if "4H" in r:
        #     runs.remove(r)

    if args.dry_run:
        for runid in runs:
            for _, sub_id, sub_path in subrun_dirs(runid):
                print(f"{sub_id}\t{cleaned_fasta(sub_path) or 'NO CLEANED FASTA, would skip'}")
        return

    if not selected_tools("pr", [TOOL]):
        sys.exit(f"[e]> container {TOOL} is not running; start it first")

    tag = f"pre_abricate_rerun_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    for i, runid in enumerate(runs, 1):
        print(f"[i]> ({i}/{len(runs)}) {runid}", flush=True)
        try:
            rerun(runid, tag)
        except Exception:
            logger.exception(f"[e]> ABRicate rerun of {runid} failed; continuing")


if __name__ == "__main__":
    main()
