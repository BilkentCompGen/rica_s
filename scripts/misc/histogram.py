#!/usr/bin/env python3
# Save this as: plot_top10.py

import argparse
import os
import pandas as pd
import plotly.express as px

def main():
    parser = argparse.ArgumentParser(description="Generate horizontal bar charts (HTML & PDF) for the top 10 mapped references.")
    parser.add_argument("input_tsv", help="Input 2-column TSV file (Reference, Count)")
    args = parser.parse_args()

    print(f"[*] Reading data from {args.input_tsv}...")
    
    try:
        df = pd.read_csv(args.input_tsv, sep='\t', header=None, names=['Reference', 'Count'])
    except Exception as e:
        print(f"{e}")
        return

    # Grab the top 10 highest counts.
    top10_df = df.nlargest(10, 'Count').sort_values(by='Count', ascending=True)

    # THE STREET MAGIC: Merge the Reference and Count into a single formatted string
    top10_df['Label'] = "<i>"+top10_df['Reference'] + "</i> <b>(" + top10_df['Count'].astype(str) + ")</b>  "

    fig = px.bar(
        top10_df, 
        x='Count', 
        y='Label',  # Use our new merged column here
        orientation='h',
        # title='Top 10 Mapped References',
        color='Count',
        color_continuous_scale='Turbo' 
        # Notice we dropped the text='Count' argument here so it doesn't double-print
    )

    fig.update_layout(
        # template='plotly_dark',
        xaxis_title="Number of Reads Mapped",
        yaxis_title="",  # Leave this blank so we don't crowd your new labels
        # font=dict(family="Courier New, monospace", size=14),
        margin=dict(l=10, r=10, t=0, b=60),
        coloraxis_showscale=False 
    )
    
    # Kept the bars nice and lean at 60% thickness
    fig.update_traces(width=0.5)

    base_name, _ = os.path.splitext(args.input_tsv)
    out_html = f"{base_name}.html"
    out_pdf = f"{base_name}.pdf"

    try:
        fig.write_html(out_html)
        fig.write_image(out_pdf, width=600)
        print(f"[*] Files saved: {out_pdf} {out_html}")
    except ValueError as e:
        print(f"System error: {e}")


if __name__ == "__main__":
    main()