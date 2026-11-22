#! /bin/bash

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

# project root: passed in by the stage driver (config.py), else derived from this script's location
RICA_S_HOME="${RICA_S_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
cuclarkdb=$RICA_S_HOME/tools/rica_s_id_cuclark/



echo "[cmd]> set_targets.sh $cuclarkdb custom"
set_targets.sh $cuclarkdb custom
#/rica_s/output/test_3/rica_s_fl_minimap2/nonhuman_unmapped_sequence.fasta 
echo "[cmd]> classify_metagenome.sh -n 8 -O $inputfile -R $outdir/$outputfile.cuclark.csv"
/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" classify_metagenome.sh -n 8 -O $inputfile -R $outdir/$outputfile.cuclark.csv

awk -F',' '
NR>1 {
    ref = $4
    # Strip leading and trailing spaces from the assignment
    gsub(/^[ \t]+|[ \t]+$/, "", ref)
    
    # Only count if it actually mapped to something (ignore UNKNOWN or NA)
    if (ref != "UNKNOWN" && ref != "NA") {
        count[ref]++
    }
}
END {
    # Print it out as a strict TSV
    for (r in count) {
        printf "%s\t%d\n", r, count[r]
    }
}' $outdir/$outputfile.cuclark.csv.csv > $outdir/$outputfile.cuclark.csv.csv.tsv
