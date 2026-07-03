#! /bin/bash

echo "[i]> === kraken2"
date
echo

# run_id=$1
inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

k2db=/opt/rica_s/tools/rica_s_id_kraken2/pathogen.k2db/


/usr/bin/time -v k2 classify --db $k2db --threads `nproc` --report $outdir/$outputfile.kraken2.report --output $outputfile.kraken2.output --unclassified-out $outdir/$outputfile.kraken2.unclassified --classified-out $outdir/$outputfile.kraken2.classified $inputfile
awk -F'\t' -v OFS='\t' '$4 == "S" || $4 ~ /^S[0-9]/ {gsub(/^ +/, "", $6); print $2, $6}' $outdir/$outputfile.kraken2.report > $outdir/$outputfile.kraken2.report.tsv

echo
date
echo "[i]> kraken2 ==="