#! /bin/bash
# this will classify (align, identify) a read against the pathogen DB.


inputfile="$1"
outputfile=$(basename $inputfile)
outdir="$2"

# project root: passed in by the stage driver (config.py), else derived from this script's location
RICA_S_HOME="${RICA_S_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
doradomodel="$RICA_S_HOME/tools/rica_s_bc_dorado/dna_r10.4.1_e8.2_400bps_hac@v4.1.0"

/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" \
	dorado basecaller \
	-x "cuda:all" \
	--batchsize 0 \
	$doradomodel \
	$inputfile \
	> $outdir/$outputfile.bam \
	2>> $outdir/$(basename $outdir).log	
	 

samtools fastq $outdir/$outputfile.bam > $outdir/$outputfile.fastq
