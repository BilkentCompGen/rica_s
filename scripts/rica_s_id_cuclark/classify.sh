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
/usr/bin/time -v classify_metagenome.sh  -n `nproc` -O $inputfile -R $outdir/$outputfile.cuclark.csv
tail -n +2 $outdir/$outputfile.cuclark.csv.csv | cut -d',' -f1,4 | tr ',' '\t' > $outdir/$outputfile.cuclark.csv.tsv


echo
date
echo '[i]> cuclark ==='
