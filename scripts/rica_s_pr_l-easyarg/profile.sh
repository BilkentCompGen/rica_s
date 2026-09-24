#!/usr/bin/env bash
echo '[i]> === L-EasyARG' && date && echo ""

inputdir="$1"
outputfile=$(basename $inputfile).abricate.csv

outdir="$2"

source /root/.bashrc
micromamba activate


./easyARG.sh --rawdata XXX --database YYY --threads NNN


echo "" && date && echo '[i]> L-EasyARG ==='
