#!/bin/bash
# Save this as: add_taxids.sh
# Run it like: bash add_taxids.sh input.fasta output.fasta

IN_FASTA=$1
OUT_FASTA=$2

if [ -z "$IN_FASTA" ] || [ -z "$OUT_FASTA" ]; then
    echo "Hold up, ese. Usage: $0 <input.fasta> <output.fasta>"
    exit 1
fi

echo "[*] Extracting accessions..."
# Grab the first word after the '>', removing the '>' itself
grep "^>" "$IN_FASTA" | awk '{print $1}' | sed 's/^>//' > tmp_accs.txt

echo "[*] Hitting NCBI in bulk to get TaxIDs..."
# epost sends the whole list to the NCBI server at once.
# esummary and xtract pull down exactly what we need without heavy parsing.
epost -db nuccore -input tmp_accs.txt | \
esummary | \
xtract -pattern DocumentSummary -element AccessionVersion,TaxId > tmp_map.txt

echo "[*] Rebuilding the FASTA headers..."
awk '
# First pass: Load the map file into memory
NR==FNR { map[$1]=$2; next }

# Second pass: Process the FASTA file
/^>/ {
    acc = $1
    sub(/^>/, "", acc)
    
    # If we got a TaxID for this accession, format the header
    if (acc in map) {
        taxid = map[acc]
        # Rebuild column 1. Awk automatically keeps the long_description intact.
        $1 = ">" acc "|kraken:taxid|" taxid
    } else {
        print "Warning: No TaxID found for " acc > "/dev/stderr"
    }
    
    print $0
    next
}
# Print the sequence lines exactly as they are
{ print $0 }
' tmp_map.txt "$IN_FASTA" > "$OUT_FASTA"

echo "[*] Cleaning up the neighborhood..."
rm tmp_accs.txt tmp_map.txt

echo "[*] ¡Ya estuvo! Your Kraken2-ready file is at $OUT_FASTA"