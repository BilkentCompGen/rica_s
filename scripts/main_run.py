#! /usr/bin/python3
import os
import sys
import datetime
import time
from scripts.config import (RICA_S_HOME, run_outdir, parse_run_info,
                            read_run_info, run_info_tuple, run_info_tools, c,
                            subrun_dirs)
from scripts.rica_s_ui_web.amr_results import AMR_COLUMNS, amr_sources
from scripts import run_state
from scripts.stage_0_basecall import all_basecall
from scripts.stage_1_filter import all_filter
from scripts.stage_2_classify import all_classify
from scripts.stage_3_profile import all_profile
from scripts.stage_4_plot import all_plot
from scripts.stage_5_report import all_report
import pod5 as p5
import statistics
import os
import glob
import csv
import json
import argparse
import logging
import pandas as pd
from pathlib import Path
from scripts.misc.mpl_common import (RICA_CMAP, barh_figure,
                                     save_image, species_label)
from time import sleep
import subprocess
from concurrent.futures import ThreadPoolExecutor



logger = logging.getLogger(__name__)



############################

def merge_and_plot_amr_subruns(run_id, output_prefix):
    """Merge ABRicate and L-EasyARG hits of every sub-run and plot the top genes."""
    rows = []
    for _, subrun, path in subrun_dirs(run_id):
        for tool, name, load in amr_sources(Path(path)):
            try:
                rows += [[subrun, tool, name] + row for row in load()]
            except Exception:
                logger.exception(f"Failed to read AMR results: {subrun}/{name}")

    if not rows:
        logger.warning(f"No AMR results found for run ID: {run_id}")
        return None

    merged_df = pd.DataFrame(
        rows, columns=["SUBRUN", "TOOL", "SOURCE_FILE"] + AMR_COLUMNS)
    output_file = f"{output_prefix}_merged_amr.tsv"
    merged_df.to_csv(output_file, sep="\t", index=False)
    logger.info(f"Merged {len(merged_df)} AMR hits into {output_file}")

    try:
        # distinct reads per (tool, gene), top 50
        counts = (merged_df.drop_duplicates(["TOOL", "GENE", "SEQUENCE"])
                  .groupby(["TOOL", "GENE"]).size().nlargest(50).sort_values())
        labels = [f"{gene} [{tool}] ({n})" for (tool, gene), n in counts.items()]
        # ~0.28 in per bar so 11 pt labels never overlap
        fig = barh_figure(labels, counts.values, cmap=RICA_CMAP,
                          figsize=(8, max(3, 0.28 * len(counts))), dpi=300,
                          ytick_size=11, xlabel="Number of Reads with Hit")
        save_image(fig, f"{output_prefix}_amr.png")
        logger.info(f"AMR plot saved to: {output_prefix}_amr.png")
    except Exception:
        logger.exception("An error occurred while plotting the AMR hits.")

    return merged_df


def merge_and_plot_subruns(run_id, target_dir, output_image_path):
    target_path = Path(target_dir)

    tsv_files = list(target_path.rglob(f"*{run_id}*_aggregate.tsv"))

    if not tsv_files:
        logger.warning(
            f"No TSV files found for run ID: {run_id} in {target_dir}")
        return None

    logger.info(f"Found {len(tsv_files)} TSV files. Starting merge...")

    df_list = []
    for file in tsv_files:
        try:
            # sep='\t' tells pandas this is a TSV, not a CSV
            df = pd.read_csv(file, sep='\t', header=None)
            df_list.append(df)
        except Exception as e:
            logger.exception(f"Failed to read TSV file: {file.name}")

    if not df_list:
        return None

    merged_df = pd.concat(df_list, ignore_index=True)

    col_to_group = merged_df.columns[0]
    col_to_sum = merged_df.columns[1]

    merged_df = merged_df.groupby(col_to_group, as_index=False)[
        col_to_sum].sum()

    logger.info(f"Successfully merged {len(merged_df)} total rows.")
    try:
        col_name = merged_df.columns[0]
        col_count = merged_df.columns[1]

        if col_name in merged_df.columns and col_count in merged_df.columns:
            merged_df = merged_df.nlargest(50, col_count)
            merged_df['y_label'] = [
                species_label(name, count) for name, count
                in zip(merged_df[col_name], merged_df[col_count])]

            merged_df = merged_df.sort_values(by=col_count, ascending=True)

            fig = barh_figure(
                merged_df['y_label'],
                merged_df[col_count],
                cmap=RICA_CMAP,
                figsize=(8, 6),
                dpi=300,
                ytick_size=13,
            )

            # Save the figure to disk
            save_image(fig, output_image_path)
            logger.info(f"Plot saved successfully to: {output_image_path}")

        else:
            logger.error(
                f"Plot failed: columns '{col_name}' or '{col_count}' not found.")

    except Exception as e:
        logger.exception("An error occurred while plotting the data.")

    from scripts.misc.histogram import plot_df
    # hist_script = f"{c['RICA_S_HOME']}/scripts/misc/histogram.py"
    # subprocess.run(["python3", hist_script, file])
    plot_df(merged_df, output_image_path)

    return merged_df









LOG_FORMAT = "%(asctime)s - [%(name)s:%(lineno)d] - %(message)s"


def _attach_run_log(log_path):
    # basicConfig only works once per process, so batch runs would all log
    # to the first run's file; attach (and later remove) a handler per run
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    if not any(type(h) is logging.StreamHandler for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    return file_handler


def _detach_run_log(file_handler):
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()


def _restart_containers():
    logger.info("[i]> === Starting containers")
    process = subprocess.Popen(
        [f"{c['RICA_S_HOME']}/builder/docker_control.sh", "restart"],
        cwd=f"{c['RICA_S_HOME']}/builder/",
        env={**os.environ, "RICA_S_HOME": c['RICA_S_HOME']},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    logger.info(process.stdout.read())
    process.wait()
    logger.info("[i]> Containers started ===")


def _n50(lengths):
    total_yield = sum(lengths)
    running_sum = 0
    for length in sorted(lengths, reverse=True):
        running_sum += length
        if running_sum >= total_yield / 2:
            return length
    return 0


def _ont_header_ids(header, channels, run_ids):
    # header: the record's header line without its '@' / '>' marker
    for item in header.split()[1:]:
        if item.startswith("ch="):
            channels.add(item.split("=")[1])
        elif item.startswith("runid="):
            run_ids.add(item.split("=")[1])


def _append_summary(summaryfile, header, metrics):
    with open(summaryfile, "a") as f:
        f.write(f"\n--- {header}\n")
        for key, value in metrics.items():
            f.write(f"{key}: {value}\n")


def pod5_metadata(inputfile, summaryfile):
    with p5.Reader(inputfile) as reader:
        try:
            # the run info of the very first read describes the whole file
            first_read = next(reader.reads())
            info = first_read.run_info
            metrics = {
                "Sample Rate": info.sample_rate,
                "Sequencing Kit": info.sequencing_kit,
                "Experiment Name": info.experiment_name,
                # pore_type is stored in a separate Pore object on the read
                "Pore Type": first_read.pore.pore_type,
            }
        except StopIteration:
            metrics = {"Error": "No reads found in this POD5 file."}
    _append_summary(summaryfile, inputfile + " ", metrics)


def _fastq_records(fastq):
    """(header, sequence length, mean Phred) per read of a 4-line FASTQ.

    Reads raw bytes instead of Biopython records: ~30x faster on ONT output, and the
    mean Phred is computed in C (sum of the quality bytes).
    """
    with open(fastq, "rb") as handle:
        for header in handle:
            if not header.strip():
                continue
            seq = handle.readline().rstrip(b"\r\n")
            handle.readline()
            qual = handle.readline().rstrip(b"\r\n")
            mean_q = sum(qual) / len(qual) - 33 if qual else None
            yield header[1:].decode(errors="replace"), len(seq), mean_q


def _fasta_records(fasta):
    """(header, sequence length) per record; sequences may span several lines."""
    header, length = None, 0
    with open(fasta, "rb") as handle:
        for line in handle:
            if line.startswith(b">"):
                if header is not None:
                    yield header, length
                header, length = line[1:].decode(errors="replace"), 0
            else:
                length += len(line.strip())
    if header is not None:
        yield header, length


def fastq_metadata(fastq, summaryfile):
    lengths, q_scores = [], []
    channels, run_ids = set(), set()
    for header, length, mean_q in _fastq_records(fastq):
        lengths.append(length)
        if mean_q is not None:
            q_scores.append(mean_q)
        _ont_header_ids(header, channels, run_ids)

    _append_summary(summaryfile, fastq, {
        "Total Reads": len(lengths),
        "Total Yield (bp)": sum(lengths),
        "Max Read Length (bp)": max(lengths) if lengths else 0,
        "Read Length N50 (bp)": _n50(lengths),
        "Overall Mean Q-Score": round(statistics.mean(q_scores), 2) if q_scores else 0,
        "Active MinION Channels": len(channels),
        "Run IDs Detected": list(run_ids),
    })


def fasta_metadata(fasta, summaryfile):
    lengths = []
    channels, run_ids = set(), set()
    for header, length in _fasta_records(fasta):
        lengths.append(length)
        # only present if the FASTA kept the ONT headers of the FASTQ
        _ont_header_ids(header, channels, run_ids)

    metrics = {
        "Total Sequences": len(lengths),
        "Total Yield (bp)": sum(lengths),
        "Max Sequence Length (bp)": max(lengths) if lengths else 0,
        "Sequence Length N50 (bp)": _n50(lengths),
    }
    if channels:
        metrics["Active MinION Channels"] = len(channels)
    if run_ids:
        metrics["Run IDs Detected"] = list(run_ids)
    _append_summary(summaryfile, fasta, metrics)


def tsv_metadata(outdir, summaryfile):
    tsv_files = glob.glob(f"{outdir}/*.tsv")
    if not tsv_files:
        logger.info(f"No .tsv files found in directory: {outdir}")
        return

    summarydata = {}
    for filepath in tsv_files:
        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                for row in csv.reader(f, delimiter='\t'):
                    summarydata[row[0]] = summarydata.get(row[0], 0) + int(row[1])
        except Exception as e:
            logger.error(f"Error reading {os.path.basename(filepath)}: {e}")

    _append_summary(summaryfile, "tsv", {
        "Tools used": len(tsv_files),
        "Pathogens detected": len(summarydata),
    })


def _log_metadata_error(future):
    # metadata is informative only, so a failure is logged, not fatal
    if future.exception():
        logger.error(f"[!]> metadata job failed: {future.exception()!r}")


def start_run(run_info):
    # give whoever is writing the .info file a moment to finish
    time.sleep(1)
    fields = read_run_info(run_info)
    runid, input_dir, input_names = run_info_tuple(fields)
    tools = run_info_tools(fields)
    if not runid or not input_names:
        logger.error(
            f"[!]> unusable run info {run_info}: runid={runid!r}, files={input_names}")
        return

    run_dir = Path(c["OUT_DIR"]) / runid
    log_handler = _attach_run_log(run_dir / f"{runid}.log")
    status = run_dir / f"{runid}.status"
    sub_status = None
    # one worker keeps the metadata jobs from interleaving in the summary
    metadata_pool = ThreadPoolExecutor(max_workers=1)

    def metadata(fn, *args):
        metadata_pool.submit(fn, *args).add_done_callback(_log_metadata_error)

    # registered before the status file says "started", so the web UI never sees
    # a started run that is not active
    run_state.active_runs.add(runid)
    status.write_text("started\n")
    logger.info(f"=======\n{Path(run_info).read_text()}\n=======")

    try:
        _restart_containers()
        logger.info("[i]> Begin of sepsis detection")

        for i, name in enumerate(input_names):
            sub_id = f"{runid}_{i}"
            inputfile = os.path.realpath(f"{input_dir}/{name}")
            outdir = run_outdir(sub_id, runid)
            os.makedirs(outdir, exist_ok=True)
            summaryfile = f"{outdir}/{sub_id}.summary"
            fastq = f"{outdir}/{os.path.basename(inputfile)}.fastq"
            fasta = f"{outdir}/{os.path.basename(fastq)}.cleaned.fasta"
            sub_status = Path(outdir) / f"{sub_id}.status"
            Path(outdir, f"{sub_id}.log").write_text("RICA_S\n")

            logger.info("-" * 30)
            logger.info(f"run ID: {sub_id}")
            logger.info(f"input file: {inputfile}")
            logger.info(f"output dir: {outdir}")
            logger.info("-" * 30)

            metadata(pod5_metadata, inputfile, summaryfile)

            logger.info(f"AllBasecall {sub_id} {inputfile}")
            all_basecall(sub_id, inputfile, runid)
            metadata(fastq_metadata, fastq, summaryfile)

            logger.info(f"AllFilter {sub_id} {fastq}")
            all_filter(sub_id, fastq, runid)
            metadata(fasta_metadata, fasta, summaryfile)

            # dummy runs skip basecall/filter and use the prepared fasta
            if "dummy.pod5" in name:
                fasta = f"{os.path.dirname(f'{input_dir}/{name}')}/{runid}.fasta"

            logger.info(f"AllClassify {sub_id} {fasta}")
            all_classify(sub_id, fasta, runid, tools=tools)
            metadata(tsv_metadata, outdir, summaryfile)

            logger.info(f"AllProfile {sub_id} {fasta}")
            all_profile(sub_id, fasta, runid, tools=tools)

            logger.info(f"AllPlot {sub_id}")
            all_plot(sub_id, runid)

            logger.info(f"AllReport {sub_id}")
            all_report(sub_id, runid)

            sub_status.write_text("finished\n")
            sub_status = None

        # merge the tsvs of all sub-runs into one df and plot it
        merge_and_plot_subruns(runid, f"{run_dir}", f"{run_dir}/_bigfile.png")
        # merge the AMR hits (ABRicate + L-EasyARG) of all sub-runs and plot them
        merge_and_plot_amr_subruns(runid, f"{run_dir}/{runid}")

        # summaries must be complete before the run is reported as finished
        logger.info("[i]> waiting for metadata jobs to finish")
        metadata_pool.shutdown(wait=True)
        logger.info("[i]> metadata jobs done")
        status.write_text("finished\n")
        logger.info("[i]> End of sepsis detection")
    except BaseException as e:
        for s in (status, sub_status):
            if s is not None:
                s.write_text("killed\n")
        logger.exception(f"[!]> run {runid} killed: {e!r}")
        # Ctrl+C and friends still stop the process; pipeline errors do not,
        # so the listener and the batch loop carry on with the next run
        if not isinstance(e, Exception):
            raise
    finally:
        metadata_pool.shutdown(wait=False)
        _detach_run_log(log_handler)
        run_state.active_runs.discard(runid)













































############################################################################
############################################################################
############################################################################

if __name__ == "__main__":
    

    if sys.argv[1] == "do_main_run":
        # basepath=Path(sys.argv[2])
        # run_infos = list(basepath.rglob("*.info"))
        infos = [
            f"{c['OUT_DIR']}/expr2_05B_0.100A_4H_1G/expr2_05B_0.100A_4H_1G.info",
            f"{c['OUT_DIR']}/expr2_05B_0.100A_4H_3G/expr2_05B_0.100A_4H_3G.info",
            f"{c['OUT_DIR']}/expr2_10B_0.100A_4H_1G/expr2_10B_0.100A_4H_1G.info",
            f"{c['OUT_DIR']}/expr2_10B_0.100A_4H_3G/expr2_10B_0.100A_4H_3G.info",
            f"{c['OUT_DIR']}/expr2_15B_0.100A_4H_1G/expr2_15B_0.100A_4H_1G.info",
            f"{c['OUT_DIR']}/expr2_15B_0.100A_4H_3G/expr2_15B_0.100A_4H_3G.info"
        ]


        l1 = [
            # f"{c['OUT_DIR']}/05B_0.001A_1H/05B_0.001A_1H.info",
            # f"{c['OUT_DIR']}/05B_0.010A_1H/05B_0.010A_1H.info",
            # f"{c['OUT_DIR']}/05B_0.100A_1H/05B_0.100A_1H.info", 
            # f"{c['OUT_DIR']}/10B_0.001A_1H/10B_0.001A_1H.info",
            # f"{c['OUT_DIR']}/10B_0.010A_1H/10B_0.010A_1H.info",
            # f"{c['OUT_DIR']}/10B_0.100A_1H/10B_0.100A_1H.info",
            # f"{c['OUT_DIR']}/15B_0.001A_1H/15B_0.001A_1H.info",
            # f"{c['OUT_DIR']}/15B_0.010A_1H/15B_0.010A_1H.info",
            # f"{c['OUT_DIR']}/15B_0.100A_1H/15B_0.100A_1H.info",
            

            f"{c['OUT_DIR']}/05B_0.001A_2H/05B_0.001A_2H.info",
            f"{c['OUT_DIR']}/05B_0.010A_2H/05B_0.010A_2H.info",
            f"{c['OUT_DIR']}/05B_0.100A_2H/05B_0.100A_2H.info", 
            f"{c['OUT_DIR']}/10B_0.001A_2H/10B_0.001A_2H.info",
            f"{c['OUT_DIR']}/10B_0.010A_2H/10B_0.010A_2H.info",
            f"{c['OUT_DIR']}/10B_0.100A_2H/10B_0.100A_2H.info",
            f"{c['OUT_DIR']}/15B_0.001A_2H/15B_0.001A_2H.info",
            f"{c['OUT_DIR']}/15B_0.010A_2H/15B_0.010A_2H.info",
            f"{c['OUT_DIR']}/15B_0.100A_2H/15B_0.100A_2H.info"
        ]


        print("starting batch runs")
        print(l1)
        for info in l1:
            start_run(info)
        print("finished batch runs")

        