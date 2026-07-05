#!/usr/bin/env bash
# set -x #debug flag
echo "[i]> Begin of sepsis detection"
echo

projecthome=/opt/rica_s/
runid=$1
inputfile="$2"

$projecthome/scripts/_1AllFilter.sh $runid $inputfile
nohuman_inputfile=$projecthome/output/$runid/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.fasta
read -n 1 -p Continue?;
echo
$projecthome/scripts/_2AllClassify.sh $runid $nohuman_inputfile
read -n 1 -p Continue?;
echo
$projecthome/scripts/_3AllProfile.sh $runid $nohuman_inputfile
read -n 1 -p Continue?;
echo
$projecthome/scripts/_4AllPlot.sh $runid


echo
echo "[i]> End of sepsis detection"
