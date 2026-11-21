#! /bin/bash
inputfile="$1"
outdir="$2"
# project root: passed in by the stage driver (config.py), else derived from this script's location
RICA_S_HOME="${RICA_S_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
indexfile="$RICA_S_HOME/tools/rica_s_id_minimap2/human_v38.mmi"

# 2. Extract just the filename without the path
filename=$(basename "$inputfile")

# 3. Strip the file extension (e.g., removes .fastq or .fasta)
clean_id="${filename%.*}"


echo "[cmd]> minimap2 -a -R \"@RG\tID:$filename\tSM:$clean_id\" $indexfile $inputfile > $outdir/$filename.filterHumanDna.sam"
/usr/bin/time -f "\n\tT> %E [h:]m:s.s\n\tM> %M KB" minimap2 -a -R "@RG\tID:$filename\tSM:$clean_id" "$indexfile" "$inputfile" > $outdir/$filename.filterHumanDna.sam

# mkdir -p $outdir/rica_s_fl_minimap2/
fix_mapq() {
    awk 'BEGIN{FS=OFS="\t"} /^@/ {print; next} ($5 < 0 || $5 > 255) {$5 = 255} {print}' "$1"
}

fix_mapq "$outdir/$filename".filterHumanDna.sam | samtools view -F 4 - | awk '{print $1}' | sort -u > "$outdir/$filename".human_mapped_sequence_names.txt
fix_mapq "$outdir/$filename".filterHumanDna.sam | samtools view -f 4 - | awk '{print $1}' | sort -u > "$outdir/$filename".nonhuman_unmapped_sequence_names.txt

echo "[cmd]> seqtk subseq $inputfile $outdir/$filename.nonhuman_unmapped_sequence_names.txt | seqtk seq -A > $outdir/$filename.cleaned.fasta"
seqtk subseq $inputfile $outdir/$filename.nonhuman_unmapped_sequence_names.txt | seqtk seq -A > $outdir/$filename.cleaned.fasta
