#! /usr/bin/python3

import os
import sys
import datetime
from config import PROJECT_HOME
from stage_0_basecall import all_basecall
from stage_1_filter import all_filter
from stage_2_classify import all_classify
from stage_3_profile import all_profile
from stage_4_plot import all_plot
from stage_5_report import all_report
import pod5 as p5
import statistics
from Bio import SeqIO
import os
import glob
import csv
import json
import argparse


def all_run(runid, inputfile_raw):

    try:
        

        print("[i]> Begin of sepsis detection")
        print(datetime.datetime.now())
        
        inputfile = os.path.realpath(inputfile_raw)
        outdir = os.path.join(PROJECT_HOME, "output", runid)
        statusfile = outdir + "/" + runid + ".status"
        summaryfile = outdir + "/" + runid + ".summary"

        os.makedirs(outdir, exist_ok=True)

        os.system("echo started > "+statusfile)
        os.system("touch "+summaryfile)
        os.system("echo RICA_S > "+outdir+"/"+runid+".log")

        print("-" * 30)
        print(f"run ID: {runid}")
        print(f"input file: {inputfile}")
        print(f"output dir: {outdir}")
        print("-" * 30)
        
##############################################################################
##############################################################################
##############################################################################


        # pod5 data
        with p5.Reader(inputfile) as reader:
            with open(summaryfile, "a") as sf:
                sf.write("\n--- "+ inputfile +" \n")
                
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
        print(f"AllBasecall {runid} {inputfile}")
        all_basecall(runid, inputfile)
        inputfile_bc = os.path.join(outdir, f"{os.path.basename(inputfile)}.fastq")
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
        print(f"AllFilter {runid} {inputfile_bc}")
        all_filter(runid, inputfile_bc)
        inputfile_cleaned = os.path.join(outdir, f"{os.path.basename(inputfile_bc)}.cleaned.fasta")
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
        print(f"AllClassify {runid} {inputfile_cleaned}")
        all_classify(runid, inputfile_cleaned)
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
        
        if not tsv_files:
            print(f"No .tsv files found in directory: {outdir}")
            return

        # Process each file
        for filepath in tsv_files:
            filename = os.path.basename(filepath)
            
            try:
                with open(filepath, mode='r', encoding='utf-8') as f:
                    # DictReader automatically uses the first row as dictionary keys
                    reader = csv.reader(f, delimiter='\t')
                    for row in reader:
                        if row[0] in summarydata.keys():
                            summarydata[row[0]]+=int(row[1])
                        else:
                            summarydata[row[0]] =int(row[1])
            except Exception as e:
                print(f"Error reading {filename}: {e}")

        # Dump the accumulated dictionary to a JSON file
        with open(summaryfile, "a") as f:
            f.write("\n--- tsv\n")
            f.write("Tools used: "+ str(len(tsv_files))+"\n")
            f.write("Pathogens detected: "+str(len(summarydata))+"\n")

##############################################################################
##############################################################################
##############################################################################





        print(f"AllProfile {runid} {inputfile_cleaned}")
        all_profile(runid, inputfile_cleaned)
        # input("Continue? Press Enter.")
        
        print(f"AllPlot {runid}")
        all_plot(runid)
        # input("Continue? Press Enter.")
        
        print(f"AllReport {runid}")
        all_report(runid)
        # input("Continue? Press Enter.")
        





##############################################################################
##############################################################################
##############################################################################

        print(datetime.datetime.now())
        print("[i]> End of sepsis detection")
        os.system("echo finished > "+statusfile)
    except Exception as e:
        os.system("echo killed > "+statusfile)
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        all_run(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python main_run.py <runid> <inputfile>")
