#! /usr/bin/python3

import os
import sys
import datetime
import time
from scripts.config import PROJECT_HOME, run_outdir, parse_run_info, c
from scripts.stage_0_basecall import all_basecall
from scripts.stage_1_filter import all_filter
from scripts.stage_2_classify import all_classify
from scripts.stage_3_profile import all_profile
from scripts.stage_4_plot import all_plot
from scripts.stage_5_report import all_report
import pod5 as p5
import statistics
from Bio import SeqIO
import os
import glob
import csv
import json
import argparse
import logging
import pandas as pd
from pathlib import Path
import plotly.express as px


logger = logging.getLogger(__name__)


def start_run(run_info):
    runid, inputfile_path, inputfile_names = parse_run_info(run_info)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(name)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.FileHandler(f"{c["OUT_DIR"]}/{runid}/{runid}.log"),
            logging.StreamHandler()
        ]
    )


    time.sleep(1)
    if not runid or not inputfile_names:
        logger.error(
            f"[!]> unusable run info {run_info}: runid={runid!r}, files={inputfile_names}")
        return

    statusfile = f"{c["OUT_DIR"]}/{runid}/{runid}.status"
    os.system("echo started > "+statusfile)

    for i, f in enumerate(inputfile_names):
        all_run(f"{runid}_{i}", os.path.join(inputfile_path, f), parent=runid)

    # load tsv of subruns of _id_ and merge in a pandas df
    # add them in one df
    # generate plot
    merge_and_plot_subruns(
        runid, c["OUT_DIR"]+"/"+runid, c["OUT_DIR"]+"/"+runid+"/_bigfile.png")

    # load tsv of subruns of _pr_
    # add them in 1
    # display

    # Example usage:
    merge_abricate_tsvs(runid, c["OUT_DIR"]+"/"+runid)


############################

def merge_abricate_tsvs(run_id, target_dir):
    target_path = Path(target_dir)

    # 1. Find all abricate TSVs recursively in the subdirectories (runid_0, runid_1, etc.)
    tsv_files = list(target_path.rglob("*abricate.csv"))

    if not tsv_files:
        logger.warning(
            f"No abricate CSV files found in {target_dir} or its subdirectories.")
        return None

    logger.info(f"Found {len(tsv_files)} abricate CSV. Merging now...")

    # 2. Load them into a list of DataFrames
    df_list = []
    for file in tsv_files:
        try:
            df = pd.read_csv(file)
            # Optional: Add a column to track exactly which subrun file it came from
            df['source_file'] = file.name
            df_list.append(df)
        except Exception as e:
            logger.exception(f"Failed to read CSV file: {file.name}")

    if not df_list:
        return None

    merged_df = pd.concat(df_list, ignore_index=True)
    output_file = target_path / f"{run_id}_merged_abricate.csv"

    merged_df.to_csv(output_file, sep='\t', index=False)
    logger.info(
        f"Successfully merged {len(merged_df)} rows and saved to {output_file}")

    with open(f"{target_dir}/{run_id}.merged_pr_.csv", "w") as f:
        f.write(merged_df.to_string(max_rows=None, max_cols=None))

    return merged_df


def merge_and_plot_subruns(run_id, target_dir, output_image_path):
    target_path = Path(target_dir)

    # 1. Find all TSV files matching the run_id (e.g., subrun_01_run123.tsv)
    # The '*' acts as a wildcard before and after the ID
    tsv_files = list(target_path.rglob(f"*{run_id}*_aggregate.tsv"))

    if not tsv_files:
        logger.warning(
            f"No TSV files found for run ID: {run_id} in {target_dir}")
        return None

    logger.info(f"Found {len(tsv_files)} TSV files. Starting merge...")

    # 2. Load all TSVs into a list of DataFrames
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

    # 3. Concatenate all DataFrames into one massive DataFrame
    # ignore_index=True resets the row numbers so they go from 0 to total_rows
    merged_df = pd.concat(df_list, ignore_index=True)

    # Extract the names of the columns at index 1 and 2
    col_to_group = merged_df.columns[0]
    col_to_sum = merged_df.columns[1]

    # Group and sum using those dynamic names
    merged_df = merged_df.groupby(col_to_group, as_index=False)[
        col_to_sum].sum()

    logger.info(f"Successfully merged {len(merged_df)} total rows.")
# 4. Generate the plot
    try:
        col_name = merged_df.columns[0]
        col_count = merged_df.columns[1]

        if col_name in merged_df.columns and col_count in merged_df.columns:

            # 1. Format the Y-axis labels using HTML tags for italics <i> and bold <b>
            merged_df['y_label'] = "<i>" + merged_df[col_name].astype(
                str) + "</i> <b>(" + merged_df[col_count].astype(str) + ")</b>"

            # 2. Sort the DataFrame so the largest values appear at the top
            # Plotly draws horizontal charts from bottom to top, so we sort ascending
            merged_df = merged_df.sort_values(by=col_count, ascending=True)

            # 3. Create the horizontal bar chart
            fig = px.bar(
                merged_df,
                x=col_count,
                y='y_label',
                orientation='h',
                color=col_count,  # Map bar color to the count value
                # Custom color scale to match the dark purple -> blue -> dark red gradient
                color_continuous_scale=['#22092e', '#3948b8', '#7a0000']
            )

            # 4. Replicate the specific styling from the target image
            fig.update_layout(
                width=800,  # Adjusted width better suited for bar charts
                height=600,
                xaxis_title="Number of Reads Mapped",
                yaxis_title=None,          # Remove the default y-axis title
                coloraxis_showscale=False,  # Hide the color scale legend on the right
                plot_bgcolor='#e5ecf6',    # Matches the light blue/gray Plotly default background
                paper_bgcolor='white',
                xaxis=dict(
                    showgrid=True,
                    gridcolor="white",     # Solid white vertical grid lines
                    zeroline=False
                ),
                yaxis=dict(
                    showgrid=False,        # Removes horizontal grid lines
                    # Slightly larger font for readability
                    tickfont=dict(size=13)
                )
            )

            # Save the figure to disk
            fig.write_image(output_image_path, scale=3)

            logger.info(f"Plot saved successfully to: {output_image_path}")

        else:
            logger.error(
                f"Plot failed: columns '{col_name}' or '{col_count}' not found.")

    except Exception as e:
        logger.exception("An error occurred while plotting the data.")

    from scripts.misc.histogram import plot_df
    # hist_script = os.path.join(c["PROJECT_HOME"], "scripts", "misc", "histogram.py")
    # subprocess.run(["python3", hist_script, file])
    plot_df(merged_df, output_image_path)

    return merged_df


def all_run(runid, inputfile_raw, parent=None):

    try:

        logger.info("[i]> Begin of sepsis detection")
        logger.info(datetime.datetime.now())

        inputfile = os.path.realpath(inputfile_raw)
        outdir = run_outdir(runid, parent)
        statusfile = outdir + "/" + runid + ".status"
        summaryfile = outdir + "/" + runid + ".summary"

        os.makedirs(outdir, exist_ok=True)

        # os.system("echo started > "+statusfile)
        # os.system("touch "+summaryfile)
        os.system("echo RICA_S > "+outdir+"/"+runid+".log")

        logger.info("-" * 30)
        logger.info(f"run ID: {runid}")
        logger.info(f"input file: {inputfile}")
        logger.info(f"output dir: {outdir}")
        logger.info("-" * 30)

##############################################################################
##############################################################################
##############################################################################

        logger.info(f"[i]> getting metadata for {inputfile}")

        # pod5 data
        with p5.Reader(inputfile) as reader:
            with open(summaryfile, "a") as sf:
                sf.write("\n--- " + inputfile + " \n")

                try:
                    # Grab the very first read in the file
                    first_read = next(reader.reads())

                    # Extract the RunInfo object
                    info = first_read.run_info

                    sf.write(f"Sample Rate: {info.sample_rate}\n")
                    sf.write(f"Sequencing Kit: {info.sequencing_kit}\n")
                    sf.write(f"Experiment Name: {info.experiment_name}\n")

                    # pore_type is stored in a separate Pore object on the read
                    sf.write(f"Pore Type: {first_read.pore.pore_type}\n")

                except StopIteration:
                    # Failsafe in case the pod5 file is completely empty
                    sf.write("Error: No reads found in this POD5 file.\n")

##############################################################################
##############################################################################
##############################################################################

        # 0. Basecall
        logger.info(f"AllBasecall {runid} {inputfile}")
        all_basecall(runid, inputfile, parent)
        inputfile_bc = os.path.join(
            outdir, f"{os.path.basename(inputfile)}.fastq")
        # input("Continue? Press Enter.")

##############################################################################
##############################################################################
##############################################################################

        # fastq data
        lengths = []
        q_scores = []
        channels = set()
        run_ids = set()

        # Iterate through the FASTQ file exactly once
        for record in SeqIO.parse(inputfile_bc, "fastq"):

            seq_len = len(record.seq)
            lengths.append(seq_len)

            read_phreds = record.letter_annotations["phred_quality"]
            if read_phreds:
                q_scores.append(statistics.mean(read_phreds))

            parts = record.description.split()
            for item in parts[1:]:
                if item.startswith("ch="):
                    channels.add(item.split("=")[1])
                elif item.startswith("runid="):
                    run_ids.add(item.split("=")[1])

        # Calculate N50
        lengths.sort(reverse=True)
        total_yield = sum(lengths)
        n50 = 0
        running_sum = 0

        for length in lengths:
            running_sum += length
            if running_sum >= total_yield / 2:
                n50 = length
                break

        # Compile the final statistics dictionary
        metrics = {
            "Total Reads": len(lengths),
            "Total Yield (bp)": total_yield,
            "Max Read Length (bp)": max(lengths) if lengths else 0,
            "Read Length N50 (bp)": n50,
            "Overall Mean Q-Score": round(statistics.mean(q_scores), 2) if q_scores else 0,
            "Active MinION Channels": len(channels),
            "Run IDs Detected": list(run_ids)
        }
        # Using "a" to append. Change to "w" if you want to overwrite the file each time.
        with open(summaryfile, "a") as f:
            f.write("\n--- "+inputfile_bc+"\n")
            for key, value in metrics.items():
                f.write(f"{key}: {value}\n")

##############################################################################
##############################################################################
##############################################################################

        # 1. Filter
        logger.info(f"AllFilter {runid} {inputfile_bc}")
        all_filter(runid, inputfile_bc, parent)
        inputfile_cleaned = os.path.join(
            outdir, f"{os.path.basename(inputfile_bc)}.cleaned.fasta")
        # input("Continue? Press Enter.")

##############################################################################
##############################################################################
##############################################################################

        lengths = []
        channels = set()
        run_ids = set()

        # Iterate through the FASTA file exactly once
        for record in SeqIO.parse(inputfile_cleaned, "fasta"):

            # 1. Sequence & Length Metrics
            seq_len = len(record.seq)
            lengths.append(seq_len)

            # 2. Hardware & Run Metadata
            # (Only applies if the FASTA retained ONT headers from a FASTQ conversion)
            parts = record.description.split()
            for item in parts[1:]:
                if item.startswith("ch="):
                    channels.add(item.split("=")[1])
                elif item.startswith("runid="):
                    run_ids.add(item.split("=")[1])

        # Calculate N50
        lengths.sort(reverse=True)
        total_yield = sum(lengths)
        n50 = 0
        running_sum = 0

        for length in lengths:
            running_sum += length
            if running_sum >= total_yield / 2:
                n50 = length
                break

        # Compile the final statistics dictionary
        metrics = {
            "Total Sequences": len(lengths),
            "Total Yield (bp)": total_yield,
            "Max Sequence Length (bp)": max(lengths) if lengths else 0,
            "Sequence Length N50 (bp)": n50,
        }

        # Only add hardware metrics if they were actually found in the FASTA header
        if channels:
            metrics["Active MinION Channels"] = len(channels)
        if run_ids:
            metrics["Run IDs Detected"] = list(run_ids)

        # Using "a" to append. Change to "w" if you want to overwrite.
        with open(summaryfile, "a") as f:
            f.write("\n--- "+inputfile_cleaned+"\n")
            for key, value in metrics.items():
                f.write(f"{key}: {value}\n")

##############################################################################
##############################################################################
##############################################################################

        # Uncomment the following when ready to execute full pipeline end-to-end:
        logger.info(f"AllClassify {runid} {inputfile_cleaned}")
        all_classify(runid, inputfile_cleaned, parent)
        # input("Continue? Press Enter.")

##############################################################################
##############################################################################
##############################################################################

    # def compile_tsvs(target_dir, output_file="summarydata.json"):
        # Initialize the main dictionary
        summarydata = {}

        # Locate all TSV files in the target directory
        search_pattern = os.path.join(outdir, "*.tsv")
        tsv_files = glob.glob(search_pattern)

        # No TSVs is not a reason to abandon the run: profiling, plotting and
        # reporting still have work to do, and bailing out here would leave the
        # .status file stuck at "started" forever.
        if not tsv_files:
            logger.info(f"No .tsv files found in directory: {outdir}")
        else:
            # Process each file
            for filepath in tsv_files:
                filename = os.path.basename(filepath)

                try:
                    with open(filepath, mode='r', encoding='utf-8') as f:
                        # DictReader automatically uses the first row as dictionary keys
                        reader = csv.reader(f, delimiter='\t')
                        for row in reader:
                            if row[0] in summarydata.keys():
                                summarydata[row[0]] += int(row[1])
                            else:
                                summarydata[row[0]] = int(row[1])
                except Exception as e:
                    logger.error(f"Error reading {filename}: {e}")

            # Dump the accumulated dictionary to a JSON file
            with open(summaryfile, "a") as f:
                f.write("\n--- tsv\n")
                f.write("Tools used: " + str(len(tsv_files))+"\n")
                f.write("Pathogens detected: "+str(len(summarydata))+"\n")

##############################################################################
##############################################################################
##############################################################################

        logger.info(f"AllProfile {runid} {inputfile_cleaned}")
        all_profile(runid, inputfile_cleaned, parent)
        # input("Continue? Press Enter.")

        logger.info(f"AllPlot {runid}")
        all_plot(runid, parent)
        # input("Continue? Press Enter.")

        logger.info(f"AllReport {runid}")
        all_report(runid, parent)
        # input("Continue? Press Enter.")

##############################################################################
##############################################################################
##############################################################################

        logger.info(datetime.datetime.now())
        logger.info("[i]> End of sepsis detection")
        os.system("echo finished > "+statusfile)
    except Exception as e:
        os.system("echo killed > "+statusfile)
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) in (3, 4):
        all_run(sys.argv[1], sys.argv[2], sys.argv[3]
                if len(sys.argv) > 3 else None)
    else:
        print(
            "Usage: python3 -m scripts.main_run <runid> <inputfile> [parent]")
