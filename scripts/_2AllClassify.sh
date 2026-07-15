#! /bin/bash
# set -x #debug flag




RunClassify()
{
	# echo $1
	docker exec -e TERM=xterm -e COLUMNS=80 -e LINES=24 -e MALLOC_ARENA_MAX=2 -it $1 $2 $3 $4 2>&1 | tee -a $5


}


AllClassify()
{

	echo "[i]> Begin of classification stage"
	date
	echo

	#projecthome is a dir in the local fs
	projecthome=/opt/rica_s
	runid=$1

	#inputfile is a fasta/q in the docker filesystem
	#and must be ABSOLUTE PATH
	inputfile="$2"
	outdir=$projecthome/output/$runid

	mkdir -p $outdir
	# echo "========================="
	# echo $inputfile
	# echo "========================="
	# for dir in ` ls -d /rica_s/scripts/rica_s_id_*/`
	for container in `ls $projecthome/scripts/ | grep '^rica_s_id_'`
	do
		
		RunClassify $container $projecthome/scripts/$container/classify.sh $inputfile /opt/rica_s/output/$runid/ $outdir/$runid.log 
		# docker exec -it $container $projecthome/scripts/$container/classify.sh $inputfile /opt/rica_s/output/$runid/ 2>&1 | tee -a $outdir/$runid.log 
		
		
		
		printf "\n\n" | tee -a $outdir/$runid.log

		# read -n 1 -p Continue?;
	done


	$projecthome/scripts/misc/replace_taxid_for_spp_tsv.sh 1 /opt/rica_s/output/$runid/*.tsv 
	$projecthome/scripts/misc/replace_acc_for_spp_tsv.sh 1 /opt/rica_s/output/$runid/*.tsv 

	echo
	date
	echo "[i]> End of classification stage"

}


# AllClassify $1 $2