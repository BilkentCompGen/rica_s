#! /bin/bash

echo '[i]> === clark'
date


inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

clarkdb=/rica_s/tools/rica_s_id_clark/


/root/CLARK/scripts/set_targets.sh $clarkdb custom 

/usr/bin/time -v /root/CLARK/scripts/classify_metagenome.sh --long -O $inputfile -R $outdir/$outputfile.csv -m 0 -n `nproc`


date
echo '[i]> clark ==='
