#!/usr/bin/env python3
"""Shared matplotlib helpers for the pipeline's figures.

Every chart in the project used to be a Plotly figure written out as a
standalone page with the whole of plotly.js inlined (~4.8 MB apiece) plus
static images via kaleido. These helpers draw the same figures with
matplotlib, which needs no extra binary for PNG/SVG/PDF, and keep the
".html next to the image" contract the web UI and the final report both
rely on by writing a small page with the SVG inlined instead.
"""

import io
import os
import re

import matplotlib
# The pipeline and the Flask server are both headless, so the backend has to
# be chosen before pyplot is imported.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402

# The gradient main_run.py passes to Plotly as a colour scale.
RICA_CMAP = LinearSegmentedColormap.from_list(
    "rica", ["#22092e", "#3948b8", "#7a0000"])

# Only the name itself goes through mathtext, and only when it is a plain
# alphabetic binomial. Mathtext treats its input as maths, so anything else
# renders wrong rather than failing loudly: a hyphen becomes a minus sign
# ("Foo-bar" -> "Foo - bar"), digits stay upright inside \it, and "|", ":" and
# "." pick up operator spacing. Accession-style labels such as
# "NZ_LR134352.1|kraken:taxid|1824" are far better off as literal text.
_BINOMIAL = re.compile(r"^[A-Za-z][A-Za-z ']*$")


def species_label(name, count):
    """A y-axis tick label: species name in italics, count in bold.

    Plotly got this from HTML markup in the label string ("<i>x</i> <b>(n)</b>").
    Matplotlib has no HTML, so the styling goes through mathtext. Anything
    outside a $...$ pair is literal, which is what non-binomial names fall back
    to -- they keep the bold count but are not italicised.
    """
    name = str(name)
    # A stray "$" would break the $...$ pairing for the whole label.
    safe = name.replace("$", r"\$")
    count_part = rf"$\bf{{({count})}}$"

    if _BINOMIAL.match(name):
        return rf"$\it{{{name.replace(' ', r'\ ')}}}$ {count_part}"
    return f"{safe} {count_part}"


def no_data_figure(figsize=(6, 4), dpi=100):
    """The placeholder drawn when there is nothing to plot: bare "NO DATA"."""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.axis("off")
    ax.text(0.5, 0.5, "NO DATA", transform=ax.transAxes,
            ha="center", va="center", fontsize=24, color="gray")
    return fig


def barh_figure(labels, values, cmap="turbo", *, figsize=None, dpi=100,
                bar_height=0.5, xlabel="Number of Reads Mapped",
                plot_bgcolor="#e5ecf6", xgrid_color="white",
                ytick_size=None):
    """A horizontal bar chart, bars coloured by their own value.

    `labels` and `values` are expected in the order they should be drawn,
    bottom to top -- the same ascending sort the Plotly version relied on.
    No colourbar is drawn, matching `coloraxis_showscale=False`.

    The default background and white gridlines reproduce the Plotly template
    these charts were previously rendered with, so the switch does not change
    how an existing report looks.
    """
    labels = list(labels)
    values = [float(v) for v in values]

    if figsize is None:
        # Plotly grew the canvas with the bar count; matplotlib won't, so the
        # height is derived and the width left to bbox_inches="tight".
        figsize = (6, max(2.5, 0.35 * len(values) + 1.2))

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("white")

    if plot_bgcolor:
        ax.set_facecolor(plot_bgcolor)

    colormap = plt.get_cmap(cmap) if isinstance(cmap, str) else cmap
    low, high = min(values), max(values)
    if low == high:
        # A single distinct value has no range to normalise against; take the
        # middle of the scale rather than an arbitrary end of it.
        colors = [colormap(0.5)] * len(values)
    else:
        colors = [colormap(c) for c in Normalize(vmin=low, vmax=high)(values)]

    ax.barh(range(len(values)), values, height=bar_height, color=colors)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)

    if ytick_size:
        ax.tick_params(axis="y", labelsize=ytick_size)

    if xgrid_color:
        ax.xaxis.grid(True, color=xgrid_color)
        ax.set_axisbelow(True)
    ax.yaxis.grid(False)

    # Plotly drew no frame around the plotting area.
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    return fig


def figure_svg(fig):
    """The figure as an inlinable SVG fragment, prolog stripped."""
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    svg = buf.getvalue()
    return svg[svg.index("<svg"):]


def write_svg_html(fig, path, title=None):
    """Write a standalone page with the figure inlined as SVG.

    This stands in for Plotly's `write_html`. It keeps every `*.html` glob in
    web_ui.py and stage_5_report.py working, and because the page is
    self-contained with no external requests it still embeds cleanly in the
    final report's `iframe srcdoc`.
    """
    if title is None:
        title = os.path.basename(path)

    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{title}</title>\n"
        "<style>\n"
        "  html,body{margin:0;padding:0;background:#fff}\n"
        "  body{min-height:100vh;display:flex;align-items:center;"
        "justify-content:center;padding:16px;box-sizing:border-box}\n"
        "  svg{max-width:100%;height:auto}\n"
        "</style>\n</head>\n<body>\n"
        f"{figure_svg(fig)}\n"
        "</body>\n</html>\n"
    )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)


def save_figure(fig, basename, formats=("html", "png", "svg"), title=None,
                close=True):
    """Write `basename.<ext>` for each requested format, then drop the figure.

    Closing matters: a run draws nine of these and the web server is
    long-lived, so figures left open accumulate.
    """
    written = []
    try:
        for ext in formats:
            path = f"{basename}.{ext}"
            if ext == "html":
                write_svg_html(fig, path, title=title)
            else:
                fig.savefig(path, format=ext, bbox_inches="tight",
                            facecolor=fig.get_facecolor())
            written.append(path)
    finally:
        if close:
            plt.close(fig)

    return written


def save_image(fig, path, close=True):
    """Write a figure to one explicit path, extension deciding the format."""
    try:
        fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    finally:
        if close:
            plt.close(fig)
    return path
