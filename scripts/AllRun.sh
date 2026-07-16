#!/usr/bin/env bash
# set -x #debug flag

# Inject this tracking logic at the absolute top of your script
# export PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]} -> '
# exec 3>&2 2>/tmp/script_execution.log
# set -x



projecthome=/opt/rica_s
. $projecthome/scripts/_1AllFilter.sh
. $projecthome/scripts/_2AllClassify.sh
. $projecthome/scripts/_3AllProfile.sh
. $projecthome/scripts/_4AllPlot.sh



AllRun() {

	echo "[i]> Begin of sepsis detection"
	date
	echo

	runid=$1
	inputfile=$(realpath "$2")
	mkdir -p $projecthome/output/$runid
	echo run ID: $runid
	echo input file: $inputfile
	echo output dir: $projecthome/output/$runid
	echo




    AllFilter $runid $inputfile
	nohuman_inputfile=$projecthome/output/$runid/rica_s_fl_minimap2/nonhuman_unmapped_sequence_names.fasta
	# read -n 1 -p Continue?;
	echo


    AllClassify $runid $nohuman_inputfile
	# read -n 1 -p Continue?;
	echo


    AllProfile $runid $nohuman_inputfile
	# read -n 1 -p Continue?;
	echo
	
	


    AllPlot $runid
    # read -n 1 -p Continue?;



	echo
	date
	echo "[i]> End of sepsis detection"
}




AllRun $1 $2