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
tail -n +2 $outdir/$outputfile.clark.csv.csv | cut -d',' -f1,4 | tr ',' '\t' > $outdir/$outputfile.clark.csv.tsv

echo ""
date
echo '[i]> clark ==='
