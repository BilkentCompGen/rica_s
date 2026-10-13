#!/usr/bin/env python3
# Save this as: plot_top10.py

import argparse
import os
import pandas as pd

# stage_4_plot.py runs this file directly, where the "scripts" package is not
# importable; main_run.py imports it as scripts.misc.histogram. Support both.
try:
    from scripts.misc.mpl_common import (barh_figure, no_data_figure,
                                         save_figure, species_label)
except ImportError:
    from mpl_common import (barh_figure, no_data_figure,
                            save_figure, species_label)


def main():
    parser = argparse.ArgumentParser(
        description="Generate horizontal bar charts (HTML & images) for the top 10 mapped references.")
    parser.add_argument("input_tsv", help="Input TSV file (Reference, Count)")
    args = parser.parse_args()

    print(f"[*] Reading data from {args.input_tsv}...")

    try:
        df = pd.read_csv(args.input_tsv, sep='\t', header=None,
                         names=['Reference', 'Count'])
    except Exception as e:
        print(f"{e}")
        return

    if len(df.index) == 0:
        print("Empty TSV")
        fig = no_data_figure()
    else:
        # Grab the top 10 highest counts. Horizontal bars are drawn bottom to
        # top, so ascending puts the biggest one at the top of the chart.
        top10_df = df.nlargest(10, 'Count').sort_values(by='Count', ascending=True)

        # Merge the Reference and Count into a single formatted tick label.
        labels = [species_label(name, count) for name, count
                  in zip(top10_df['Reference'], top10_df['Count'])]

        fig = barh_figure(labels, top10_df['Count'], cmap='turbo')

    base_name, _ = os.path.splitext(args.input_tsv)

    try:
        # PDF is deliberately left out here; only plot_df writes one.
        written = save_figure(fig, base_name, formats=("html", "png", "svg"))
        print(f"[*] Files saved: {' '.join(written)}")
    except ValueError as e:
        print(f"System error: {e}")


def plot_df(df, outfile):
    """Plot an already-prepared frame.

    The caller is expected to have added a "y_label" column and sorted the
    rows ascending by count; the count itself is read positionally from the
    second column, as it always was.
    """
    if len(df.index) == 0:
        print("Empty TSV")
        fig = no_data_figure()
    else:
        fig = barh_figure(df["y_label"], df[df.columns[1]], cmap='turbo')

    try:
        written = save_figure(fig, outfile,
                              formats=("html", "pdf", "png", "svg"))
        print(f"[*] Files saved: {' '.join(written)}")
    except ValueError as e:
        print(f"System error: {e}")


if __name__ == "__main__":
    main()
