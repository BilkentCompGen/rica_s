#!/bin/bash

# Define our input and output files
INPUT=$1
CLEAN_TSV="clean_kraken_reads.tsv"
TREEMAP_HTML="kraken_treemap.html"

echo "\e[1;33m[1/2] Slicing the Kraken2 output...\e[0m"
# Extract only Classified reads (C), and grab Read_ID ($2) and Species ($3)
awk -F'\t' 'BEGIN {OFS="\t"} $1=="C" {print $2, $3}' "$INPUT" > "$CLEAN_TSV"

echo "\e[1;33m[2/2] Firing up Plotly to build the Treemap dashboard...\e[0m"


# Run Python directly inside the bash script
python3 -c "
import pandas as pd
import plotly.express as px
# 1. Load the freshly filtered TSV
df = pd.read_csv('$CLEAN_TSV', sep='\t', header=None, names=['Read_ID', 'Species'])

# 2. Clean up the Kraken names (Removes the ugly ' (taxid 123)' tags)
df['Species'] = df['Species'].str.replace(r' \(taxid \d+\)', '', regex=True)

# 3. Count how many reads hit each species
hit_counts = df['Species'].value_counts().reset_index()
hit_counts.columns = ['Species', 'Read_Count']

# 4. Build the interactive Treemap
fig = px.treemap(hit_counts, 
   	             path=[px.Constant('All Classified Reads'), 'Species'], 
       	         values='Read_Count',
         	     title='Kraken2 Pathogen Abundance (Treemap)',
               	 color='Read_Count', 
               	 color_continuous_scale='Magma')

# 5. Clean up the edges
fig.update_layout(
#    template='plotly_dark',
   	margin=dict(t=50, l=25, r=25, b=25)
)

# 6. Save the HTML dashboard
fig.write_image('kraken2.svg')
"

echo "\e[1;32m¡Ya estuvo, ese! Kraken pipeline complete.\e[0m"
echo "-> Clean TSV table saved to: \e[1;36m$CLEAN_TSV\e[0m"
echo "-> Interactive dashboard saved to: \e[1;36m$TREEMAP_HTML\e[0m"
