#!/bin/bash

# Loop through all files that roughly match the pattern
for file in *_*.*; do
    
    # 1. Check if it's actually a file
    [ -f "$file" ] || continue

    # 2. Extract the Extension (e.g., .fasta)
    ext="${file##*.}"
    
    # 3. Extract the Filename without extension (e.g., ABC_1234.5_LongText)
    filename="${file%.*}"

    # 4. Use Regex to separate the Prefix (XXX_D.d) from the Rest (Y)
    # Pattern: Starts with Letters + Underscore + Digits + Dot + Digit + Underscore + Rest
    if [[ $filename =~ ^([A-Za-z]+_[0-9]+\.[0-9])_(.+)$ ]]; then
        
        prefix="${BASH_REMATCH[1]}" # The XXX_D.d part
        rest="${BASH_REMATCH[2]}"   # The Y part
        
        # 5. Construct the new name: Y_XXX_D.d.ext
        new_name="${rest}_${prefix}.${ext}"

        # 6. Rename the file
        echo "Renaming: $file -> $new_name"
        mv "$file" "$new_name"
        
    else
        echo "Skipping: $file (Did not match the strict pattern)"
    fi
done