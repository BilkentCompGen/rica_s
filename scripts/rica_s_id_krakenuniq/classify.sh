#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.

echo "[i]> === krakenuniq"
date



inputfile=$1
outputfile=$(basename $inputfile)

outdir="$2"

kudb=/rica_s/tools/rica_s_id_krakenuniq/pathogen.kudb

# inputfile=/rica_s/datasets/_1/dataset_5120reads.fasta



krakenuniq --db $kudb \
           --threads `nproc` \
           --report-file $outdir/$outputfile.tsv \
           "$inputfile" > $outdir/$outputfile.kraken 2> $outdir/$outputfile.log


echo "[i]> krakenuniq ==="
date