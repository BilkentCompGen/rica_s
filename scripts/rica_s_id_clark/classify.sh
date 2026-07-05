#! /bin/bash

echo '[i]> === clark'
date
echo ""

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

clarkdb=/opt/rica_s/tools/rica_s_id_clark/


set_targets.sh $clarkdb custom 

/usr/bin/time -v classify_metagenome.sh --long -O $inputfile -R $outdir/$outputfile.clark.csv -m 0 -n `nproc`
# tail -n +2 $outdir/$outputfile.clark.csv.csv | cut -d',' -f1,4 | tr ',' '\t' > $outdir/$outputfile.clark.csv.tsv

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
}' $outdir/$outputfile.clark.csv.csv > $outdir/$outputfile.clark.csv.csv.tsv


echo ""
date
echo '[i]> clark ==='
