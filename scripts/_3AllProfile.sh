#!/usr/bin/env bash

echo "[i]> Begin of profiling stage"


#projecthome is a dir in the local fs
projecthome=/opt/rica_s/
runid=$1

#inputfile is a fasta/q in the docker filesystem
#and must be ABSOLUTE PATH
inputfile="$2"
outdir=$projecthome/output/$runid/

mkdir -p $outdir

# for dir in ` ls -d /rica_s/scripts/rica_s_id_*/`
for container in `ls $projecthome/scripts/ | grep rica_s_pr*`
do

    docker exec -it $container $projecthome/scripts/$container/profile.sh $inputfile /opt/rica_s/output/$runid/ 2>&1 | tee -a $outdir/$runid.log
    printf "\n\n" | tee -a $outdir/$runid.log

    # read -n 1 -p Continue?;
done

echo "[i]> End of profiling stage"
