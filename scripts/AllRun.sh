#!/usr/bin/env bash
# set -x #debug flag
echo "[i]> Begin of sepsis detection"
echo

projecthome=/opt/rica_s/
runid=$1
inputfile="$2"

$projecthome/scripts/_1AllFilter.sh $runid $inputfile
echo
$projecthome/scripts/_2AllClassify.sh $runid $inputfile
echo
$projecthome/scripts/_3AllProfile.sh $runid $inputfile
echo
$projecthome/scripts/_4AllPlot.sh $runid


echo
echo "[i]> End of sepsis detection"
