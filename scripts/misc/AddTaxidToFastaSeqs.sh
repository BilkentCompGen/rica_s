 
#!/bin/bash

# Define your input and output files right here at the top
MAP_FILE=/home/ricardo/projects/rica_s/tools/rica_s_id_kraken2/pathogen.k2db/taxonomy/nucl_wgs.accession2taxid #NCBI Accession-to-TaxID mapping file.
INPUT_FASTA=/home/ricardo/projects/rica_s/reference_genomes/coosa.fasta
OUTPUT_FASTA="$INPUT_FASTA"_withtaxid.fasta

echo -e "\e[1;33m[+] Firing up the FASTA tagger, ese...\e[0m"
echo -e "\e[1;34m[+] Reading the NCBI accession map into memory (give it a minute)...\e[0m"

# Run the master awk mapping hustle
awk -F'\t' '
# 1. First Pass: Read the accession map into memory
NR==FNR {
    # Skip the header line if it exists
    if (NR > 1) {
        acc2tax[$2] = $3
    }
    next
}

# 2. Second Pass: Process your FASTA file
/^>/ {
    # Find exactly where the first space is to separate ID from description
    space_pos = index($0, " ")
    
    if (space_pos > 0) {
        acc = substr($0, 2, space_pos - 2)  # The ID without the >
        desc = substr($0, space_pos)        # The description (including the space)
    } else {
        acc = substr($0, 2)
        desc = ""
    }

    # Look up the ID in our memory map and inject the Kraken tag
    if (acc in acc2tax) {
        print ">" acc "|kraken:taxid|" acc2tax[acc] desc
    } else {
        print "WARNING: Dead end, no TaxID found for " acc > "/dev/stderr"
        print $0 
    }
    next
}

# 3. For the sequence lines (A,T,C,G), just print them raw
{ print $0 }
' "$MAP_FILE" "$INPUT_FASTA" > "$OUTPUT_FASTA"

echo -e "\e[1;32m[+] Solid! Tagged sequences saved perfectly to: $OUTPUT_FASTA\e[0m"