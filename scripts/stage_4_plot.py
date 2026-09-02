import os
import subprocess
import glob
import datetime
from collections import defaultdict
from config import PROJECT_HOME

def all_plot(runid):
    print("[i]> Begin of reporting stage")
    print(datetime.datetime.now())
    
    outdir = os.path.join(PROJECT_HOME, "output", runid)
    
    # Merge TSVs (Replaces AWK)
    print("[i]> merging TSVs...")
    total = defaultdict(int)
    for file in glob.glob(os.path.join(outdir, "*.tsv")):
        with open(file, "r") as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    try:
                        total[parts[0]] += int(parts[1])
                    except ValueError:
                        pass
                        
    merged_tsv = os.path.join(outdir, f"{runid}.tsv")
    with open(merged_tsv, "w") as f:
        for ref, count in sorted(total.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{ref}\t{count}\n")
    print("[i]> done.")
    
    print("[i]> generating plots...")
    hist_script = os.path.join(PROJECT_HOME, "scripts", "misc", "histogram.py")
    
    for file in glob.glob(os.path.join(outdir, "*.tsv")):
        subprocess.run(["python3", hist_script, file])
    
    print("[i]> done.")
    
    print("[i]> generating EPS...")
    for pdf in glob.glob(os.path.join(outdir, "*.pdf")):
        subprocess.run(["pdftops", pdf, f"{pdf}.eps"])
    print("[i]> done.")
    
    print(datetime.datetime.now())
    print("[i]> End of reporting stage")
