#! /bin/bash

date
echo 'starting rica_s_id_kraken'
echo '-----------------------------------'

run_id=$1
read_file=$2
k2 classify --db /rica_s/tools/rica_s_id_kraken2/pathogen.k2db /
	--output /rica_s/output/$1/$1.outk2 /
	--threads 16 /
	--unclassified-out $1.unclassifiedk2 /
	--classified-out $1.classifiedk2 /
	--report $1.reportk2 /
	read_file

echo '-----------------------------------'
echo 'finishing rica_s_id_kraken'
date
