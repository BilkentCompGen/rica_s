#!/bin/bash
set -e

# Canonical downloader for RICA_S reference data and prebuilt databases.
#
# Model: ONE tar per item, served over HTTP from the lab data host, extracted
# into place under /opt/rica_s. Per-tool DBs live under tools/rica_s_id_<tool>/;
# test data (datasets/, reads/) is extracted at the project root.
#
# (Legacy alternatives scripts/misc/download_data.sh and
#  scripts/misc/download_data_from_donut.sh are kept for reference only.)

python3 - << 'EOF'
import os
import sys 
import subprocess

tools = [
    "kraken2", 
    # "krakenuniq"
    "blast", 
    "bwa", 
    "ngmlr", 
    "clark", 
    "cuclark",
]

data = [
    "reference_genomes",
    "datasets",
    # "reads",
]


project_home = "/opt/rica_s"
base_url = "http://donut.cs.bilkent.edu.tr/rica_s"



def fetch_tar(urlpath, dest):
    
    tarname = os.path.basename(urlpath)
    os.makedirs(dest, exist_ok=True)
    tmp_tar = os.path.join(project_home, "tmp", tarname)
    

    # wget -nc
    subprocess.run(["wget", "-nc", "-P", os.path.join(project_home, "tmp"), f"{BASE_URL}/{urlpath}"], check=True)
    
    # tar xf
    subprocess.run(["tar", "xf", tmp_tar, "-C", dest], check=True)
    
    # rm -f
    try: 
        os.remove(tmp_tar) 
    except FileNotFoundError: 
        pass




os.makedirs(os.path.join(project_home, "tmp"), exist_ok=True)
os.makedirs(os.path.join(project_home, "tools"), exist_ok=True)
os.makedirs(os.path.join(project_home, "reference_genomes"), exist_ok=True)
os.makedirs(os.path.join(project_home, "datasets"), exist_ok=True)

print("=== downloading data ===")

for d in data:
    fetch_tar(base_url+"/"+d/".tar")

for t in tools:
    fetch_tar(base_url+"/"+t/".tar")


print("=== finished ===")
EOF
