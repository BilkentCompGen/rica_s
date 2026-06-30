#! /bin/bash

input="$1"


if [[ -f $input ]]; then # if file:
    echo "$input is a file with a list of accession numbers"
    while IFS= read -r line; do
        # Do your heavy lifting right here
        echo -n $line "\t" 
        esummary -db nuccore -id $line | grep TaxId
        # echo "Processing line: $line"
    done < $input



else # if number
    echo "$input is an accession number"
    echo -n $line "\t" 
    esummary -db nuccore -id $input | grep TaxId
fi
