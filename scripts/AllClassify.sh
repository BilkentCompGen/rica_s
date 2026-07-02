#! /bin/bash

echo "[i]> Begin of classification stage"


#projecthome is a dir in the local fs
projecthome=/home/ricardo/projects/rica_s/
runid=$1

#inputfile is a fasta/q in the docker filesystem
inputfile="$2"
outdir=$projecthome/output/$runid/

mkdir -p $outdir
echo "========================="
echo $inputfile
echo "========================="
# for dir in ` ls -d /rica_s/scripts/rica_s_id_*/`
for container in `ls $projecthome/scripts/ | grep rica_s_id*`
do
    docker exec -it $container /rica_s/scripts/$container/classify.sh $inputfile /rica_s/output/$runid/ 2>&1 | tee -a $outdir/$runid.log
    printf "\n\n" | tee -a $outdir/$runid.log
    /home/ricardo/projects/rica_s/scripts/$container/fixOutput.sh
    read -n 1 -p Continue?;
done

echo "[i]> End of classification stage"
