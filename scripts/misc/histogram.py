import pandas as pd
import plotly.express as px
import os
import sys
import re



# 1. Load up the BLAST output
file_path = sys.argv[1]
df = pd.read_csv(file_path, sep='\t', comment='#', header=None)

# 2. Count ALL hits and sort them
hit_counts = df[1].value_counts().reset_index()
hit_counts.columns = ['Subject', 'Hit_Count']

# remove taxid
# hit_counts.replace(r"\(taxid \d+\)" , "", inplace=True, regex=True)


hit_counts = hit_counts.sort_values(by='Hit_Count', ascending=False)
hit_counts = hit_counts[0:21] # keep top 20
hit_counts = hit_counts.sort_values(by='Hit_Count', ascending=True)

# 3. Build that horizontal Plotly bar chart
fig = px.bar(hit_counts,
             x='Hit_Count',
             y='Subject',
             orientation='h',
             title="Hits Distribution (Horizontal)",
             labels={'Subject': 'Species', 'Hit_Count': 'Reads'},
             color='Hit_Count',
             color_continuous_scale='sunsetdark')


# ---> THE TRICK FOR TOP & BOTTOM LABELS <---
# We build a secondary X-axis (xaxis2) that mirrors the bottom one
fig.update_layout(
    xaxis2=dict(
        title='Number of Reads',   # Give it the exact same title
        overlaying='x',            # Lay it directly over the original x-axis
        side='top',                # Push it to the roof
        matches='x'                # Force it to perfectly sync with the bottom scale
    )
)

# Plotly only draws an axis if there is data attached to it.
# We drop a single, invisible scatter point attached to 'x2' to trick it into rendering.
fig.add_scatter(x=[0],
                y=[hit_counts['Subject'].iloc[0]],
                xaxis='x2',
                opacity=0,          # Make it completely invisible
                # hoverinfo='skip',   # Don't let the mouse interact with it
                showlegend=False)   # Keep it off the legend

# 4. Make it massive and clean
fig.update_layout(
    # template="plotly_dark",
    yaxis=dict(
        tickfont=dict(size=20),
        automargin=True,
        tickmode='linear'
    ),
    # width=900,
    height=50*len(hit_counts)+300
)

# 5. Save it as a massive SVG
output_file = sys.argv[1]+"_hits_horizontal.svg"
fig.write_image(output_file)
fig.write_html(output_file+".html")

print(f"¡Listo, ese! Horizontal chart saved successfully as {output_file}")
