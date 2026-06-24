#! /bin/bash

# this script sends a fasta file containing hopefully 1 read, and it for the samfile
# to be able to retrieve it for later classification

# 1. Quote your variables to handle spaces
inputfile="$1"
outputfile="$2"
indexfile="/rica_s/tools/rica_s_id_minimap2/human_dna_db/human_v38.mmi"

# 2. Extract just the filename without the path
filename=$(basename "$inputfile")

# 3. Strip the file extension (e.g., removes .fastq or .fasta)
clean_id="${filename%.*}"

# 4. Use double quotes around everything and add the SM tag
minimap2 -a -R "@RG\tID:$filename\tSM:$clean_id" "$indexfile" "$inputfile" > "$outputfile"