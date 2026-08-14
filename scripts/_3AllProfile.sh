#!/usr/bin/env bash
# set -x #debug flag

RunProfile() {

	docker exec -it $1 $2 $3 $4 2>&1 | tee -a $5
	# docker exec -it $container $project_home/scripts/$container/profile.sh $inputfile /opt/rica_s/output/$runid/ 2>&1 | tee -a $outdir/$runid.log

}

AllProfile() {
	echo "[i]> Begin of profiling stage"
	date
	echo

	#project_home is a dir in the local fs
	project_home=/opt/rica_s/
	runid=$1

	#inputfile is a fasta/q in the docker filesystem
	#and must be ABSOLUTE PATH
	inputfile="$2"
	outdir=$project_home/output/$runid/

	mkdir -p $outdir

	# for dir in ` ls -d /rica_s/scripts/rica_s_id_*/`
	for container in $(ls $project_home/scripts/ | grep '^rica_s_pr_'); do

		RunProfile $container $project_home/scripts/$container/profile.sh $inputfile /opt/rica_s/output/$runid/ $outdir/$runid.log
		# docker exec -it $container $project_home/scripts/$container/profile.sh $inputfile /opt/rica_s/output/$runid/ 2>&1 | tee -a $outdir/$runid.log
		printf "\n\n" | tee -a $outdir/$runid.log

		# read -n 1 -p Continue?;
	done

	echo
	date
	echo "[i]> End of profiling stage"
}

# AllProfile $1 $2
