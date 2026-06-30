#! /bin/bash

echo '[i]> === cuclark'
date

inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

cuclarkdb=/rica_s/tools/rica_s_id_cuclark/



set_targets.sh $cuclarkdb custom
#/rica_s/output/test_3/rica_s_fl_minimap2/nonhuman_unmapped_sequence.fasta 
/usr/bin/time -v classify_metagenome.sh  -n `nproc` -O $inputfile -R $outdir/$outputfile.csv



date
echo '[i]> cuclark ==='
