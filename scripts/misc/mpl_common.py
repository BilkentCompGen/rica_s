#!/usr/bin/env python3
import io
import os
import re

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

RICA_CMAP = LinearSegmentedColormap.from_list(
    "rica", ["#22092e", "#3948b8", "#7a0000"])

_BINOMIAL = re.compile(r"^[A-Za-z][A-Za-z ']*$")


def species_label(name, count):
    name = str(name)
    safe = name.replace("$", r"\$")
    count_part = rf"$\bf{{({count})}}$"

    if _BINOMIAL.match(name):
        return rf"$\it{{{name.replace(' ', r'\ ')}}}$ {count_part}"
    return f"{safe} {count_part}"


def no_data_figure(figsize=(6, 4), dpi=100):
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
    labels = list(labels)
    values = [float(v) for v in values]

    if figsize is None:
        figsize = (6, max(2.5, 0.35 * len(values) + 1.2))

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("white")

    if plot_bgcolor:
        ax.set_facecolor(plot_bgcolor)

    colormap = plt.get_cmap(cmap) if isinstance(cmap, str) else cmap
    low, high = min(values), max(values)
    if low == high:
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

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    return fig


def figure_svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    svg = buf.getvalue()
    return svg[svg.index("<svg"):]


def write_svg_html(fig, path, title=None):
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
    try:
        fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    finally:
        if close:
            plt.close(fig)
    return path
