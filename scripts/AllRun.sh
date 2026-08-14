#!/usr/bin/env bash
# set -x #debug flag

# Inject this tracking logic at the absolute top of your script
# export PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]} -> '
# exec 3>&2 2>/tmp/script_execution.log
# set -x

source ./config.sh
echo `pwd`

. $project_home/scripts/_1AllFilter.sh
. $project_home/scripts/_2AllClassify.sh
. $project_home/scripts/_3AllProfile.sh
. $project_home/scripts/_4AllPlot.sh



AllRun() {

	echo "[i]> Begin of sepsis detection"
	date
	echo

	runid=$1
	inputfile=$(realpath "$2")
	mkdir -p $project_home/output/$runid
	echo "------------------------------"
	echo run ID: $runid
	echo input file: $inputfile
	echo output dir: $project_home/output/$runid
	echo "------------------------------"
	echo




    AllFilter $runid $inputfile
	inputfile_cleaned=$project_home/output/$runid/rica_s_fl_minimap2/$(basename $inputfile).cleaned.fasta
	read -n 1 -p Continue?;
	echo


    AllClassify $runid $inputfile_cleaned
	read -n 1 -p Continue?;
	echo


    AllProfile $runid $inputfile_cleaned
	read -n 1 -p Continue?;
	echo
	
	
    AllPlot $runid
    read -n 1 -p Continue?;
	echo


	echo
	date
	echo "[i]> End of sepsis detection"
}




AllRun $1 $2