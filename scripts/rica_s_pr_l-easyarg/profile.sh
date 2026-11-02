#!/usr/bin/env bash

echo '[i]> === L-EasyARG' && date && echo ""

inputdir=$(dirname "$1")
echo "inputdir: " $inputdir
outdir="$2"
echo "outdir: " $outdir


# project root: passed in by the stage driver (config.py), else derived from this script's location
RICA_S_HOME="${RICA_S_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" /bin/bash -ic "cd $outdir && conda activate && easyARG.sh --rawdata $inputdir --database '$RICA_S_HOME/tools/rica_s_pr-l-easyarg/database/' --threads `nproc`"


echo "" && date && echo '[i]> L-EasyARG ==='
