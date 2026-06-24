#!/bin/bash

# Start from the current directory (.)
START_DIR=$1

echo "Starting recursive indexing from: $START_DIR"

# Find all files ending in .fasta or .fa
# We use a while loop to handle spaces in filenames correctly
find "$START_DIR" -type f \( -name "*.fasta" -o -name "*.fa" \) | while read -r fasta_file; do
    
    # 1. Get the directory where the file lives
    dir_path=$(dirname "$fasta_file")
    
    # 2. Get the filename itself
    base_name=$(basename "$fasta_file")
    
    # 3. Create the output name (e.g., file.fasta -> file.mmi)
    # This strips the extension and adds .mmi
    mmi_name="${base_name%.*}.mmi"
    
    echo "------------------------------------------------"
    echo "Found FASTA: $base_name"
    echo "Location:    $dir_path"
    echo "Building Index..."
    
    # 4. Run minimap2
    # We cd into the directory to keep the output file next to the input
    # ( ) runs this in a subshell so we don't mess up our current directory
    (
        cd "$dir_path" || exit
        minimap2 -d "$mmi_name" "$base_name"
    )

done

echo "------------------------------------------------"
echo "¡Ya estuvo! All indices built."