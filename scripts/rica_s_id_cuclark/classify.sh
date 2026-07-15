#! /bin/bash

echo '[i]> === cuclark'
date
echo

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

cuclarkdb=/opt/rica_s/tools/rica_s_id_cuclark/



set_targets.sh $cuclarkdb custom
#/rica_s/output/test_3/rica_s_fl_minimap2/nonhuman_unmapped_sequence.fasta 
/usr/bin/time -v classify_metagenome.sh  -n 8 -O $inputfile -R $outdir/$outputfile.cuclark.csv
# tail -n +2 $outdir/$outputfile.cuclark.csv.csv | cut -d',' -f1,4 | tr ',' '\t' > $outdir/$outputfile.cuclark.csv.tsv

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


echo
date
echo '[i]> cuclark ==='
