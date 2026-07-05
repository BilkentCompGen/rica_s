#!/bin/bash
# set -x #debug flag
echo "[i]> Begin of Filtering stage"


#projecthome is a dir in the local fs
projecthome=/opt/rica_s/
runid=$1

#inputfile is a fasta/q in the docker filesystem
#and must be ABSOLUTE PATH
inputfile="$2"
outdir=$projecthome/output/$runid/

mkdir -p $projecthome/output/$runid/

docker exec -it rica_s_id_minimap2 \
    $projecthome/scripts/rica_s_id_minimap2/filterHumanDna.sh \
    $inputfile \
    /opt/rica_s/output/$runid/ \
    2>&1 | tee -a $outdir/$runid.log


echo "[i]> End of Filtering stage"
