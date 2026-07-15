#!/bin/bash
# set -x #debug flag

AllFilter() {

	echo "[i]> Begin of Filtering stage"
	date
	echo

	#projecthome is a dir in the local fs
	projecthome=/opt/rica_s/
	runid=$1

	#inputfile is a fasta/q in the docker filesystem
	#and must be ABSOLUTE PATH
	inputfile="$2"
	outdir=$projecthome/output/$runid/

	mkdir -p $outdir

	# echo "docker exec -it rica_s_id_minimap2 $projecthome/scripts/rica_s_id_minimap2/filterHumanDna.sh $inputfile $outdir 2>&1 | tee -a $outdir/$runid.log"

	docker exec -it rica_s_id_minimap2 \
		$projecthome/scripts/rica_s_id_minimap2/filterHumanDna.sh $inputfile $outdir \
		2>&1 | tee -a $outdir/$runid.log

	echo
	date
	echo "[i]> End of Filtering stage"
}
# AllFilter $1 $2
