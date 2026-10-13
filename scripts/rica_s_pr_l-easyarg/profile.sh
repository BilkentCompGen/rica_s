#!/usr/bin/env bash

echo '[i]> === L-EasyARG' && date && echo ""

inputdir=$(dirname "$1")
echo "inputdir: " $inputdir
outdir="$2"
echo "outdir: " $outdir


/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" /bin/bash -ic "cd $outdir && conda activate && easyARG.sh --rawdata $inputdir --database '/opt/rica_s/tools/rica_s_pr-l-easyarg/database/' --threads `nproc`"


echo "" && date && echo '[i]> L-EasyARG ==='
