#! /bin/bash
# set -x


echo '[i]> === clark'
date
echo ""

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

clarkdb=/opt/rica_s/tools/rica_s_id_clark




set_targets.sh $clarkdb custom 
classify_metagenome.sh -O $inputfile -R $outdir/$outputfile.clark.csv -n 8 -m 0 --long
#/opt/CLARK/exe/CLARK -T /opt/rica_s/tools/rica_s_id_clark/targets.txt -D /opt/rica_s/tools/rica_s_id_clark/custom_0/ -O /opt/rica_s/input/pathogens_25.fasta -R ./caca -m 0 --long



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
