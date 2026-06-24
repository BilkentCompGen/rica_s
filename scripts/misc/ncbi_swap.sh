#!/bin/bash
export NCBI_API_KEY=6011b8a8b99182bce9ff83bda81dea964e09
export api_key=6011b8a8b99182bce9ff83bda81dea964e09
INPUT=$1
OUTPUT=$2

echo -e "\e[1;33m[1] Extracting unique accession IDs...\e[0m"
# Grab column 2, ignore the comments, and sort for unique IDs
grep -v "^#" "$INPUT" | awk '{print $2}' | sort -u > unique_accs.txt

echo -e "\e[1;33m[2] Hitting the NCBI mothership in bulk...\e[0m"
# epost sends the whole list to NCBI's memory
# esummary pulls the metadata
# xtract pulls out a clean, 2-column list: "AccessionVersion \t Organism"
epost -db nuccore -input unique_accs.txt | esummary | xtract -pattern DocumentSummary -element AccessionVersion,Organism > acc_map.txt

echo -e "\e[1;33m[3] Rewriting your BLAST output with species names...\e[0m"
awk '
BEGIN { FS="\t"; OFS="\t"; block_done=0 }

# Pass 1: Build the dictionary from the NCBI map we just downloaded
NR==FNR {
    acc = $1
    # Everything after the first column is the species name
    species = $0
    sub($1 "\t", "", species)
    
    # Replace spaces with underscores to keep your tables clean
    gsub(/ /, "_", species) 
    
    dict[acc] = species
    next
}

# Pass 2: Process the BLAST output file
FNR!=NR {
    if (/^#/) {
        # Keep only the very first comment block
        if (block_done == 0) { print $0 }
        next
    }
    
    block_done = 1 # Lock the comment block so we drop the rest
    
    # Swap the ID if we found it in NCBI
    if ($2 in dict) {
        $2 = dict[$2]
    }
    
    print $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
}
' acc_map.txt "$INPUT" > "$OUTPUT"

# Clean up the evidence
rm unique_accs.txt acc_map.txt

echo -e "\e[1;32m¡Listo, ese! Check out $OUTPUT\e[0m"
