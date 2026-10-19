#! /usr/bin/python3
import os

import numpy as np
import pandas as pd
from Bio import SeqIO
import pathlib

try:
    from scripts.misc.mpl_common import save_figure
except ImportError:
    from mpl_common import save_figure
import matplotlib.pyplot as plt


def parse_sequence(file_path, file_format="fasta"):
    """
    Parses a FASTA or FASTQ file and extracts the sequence of the first record.
    """
    try:
        record = next(SeqIO.parse(file_path, file_format))
        return str(record.seq).upper(), record.id
    except StopIteration:
        raise ValueError(f"No records found in the file: {file_path}")
    except Exception as e:
        raise Exception(f"Error parsing file: {e}")

def generate_dv_curve_coords(sequence):
    """
    Generates 2D coordinates using the Dual-Vector (DV-Curve) mapping philosophy.
    Uses symmetrical vectors to represent nucleotides without degeneracy:
    A = (1, 1), T = (1, -1), C = (-1, 1), G = (-1, -1)
    """
    # Initialize coordinate arrays
    x = np.zeros(len(sequence) + 1)
    y = np.zeros(len(sequence) + 1)
    
    # Vector mappings
    mapping = {
        'A': (1, 1),
        'T': (1, -1),
        'C': (-1, 1),
        'G': (-1, -1)
    }
    
    current_x, current_y = 0, 0
    for i, base in enumerate(sequence):
        dx, dy = mapping.get(base, (0, 0)) # Non-ATCG bases (like N) default to stationary
        current_x += dx
        current_y += dy
        x[i+1] = current_x
        y[i+1] = current_y
        
    return x, y

# def generate_dn_curve_coords(sequence):
#     """
#     Generates 2D coordinates using a Double Nucleotide (DN-Curve) approach.
#     Maps adjacent dinucleotides as cumulative trajectory steps over a sliding window.
#     """
#     if len(sequence) < 2:
#         return np.array([0]), np.array([0])
        
#     x = np.zeros(len(sequence))
#     y = np.zeros(len(sequence))
    
#     # Symmetrical mapping for 16 possible dinucleotides over a 2D grid matrix
#     dinucleotide_vectors = {
#         'AA': (2, 2),   'AT': (2, 1),   'AC': (2, -1),  'AG': (2, -2),
#         'TA': (1, 2),   'TT': (1, 1),   'TC': (1, -1),  'TG': (1, -2),
#         'CA': (-1, 2),  'CT': (-1, 1),  'CC': (-1, -1), 'CG': (-1, -2),
#         'GA': (-2, 2),  'GT': (-2, 1),  'GC': (-2, -1), 'GG': (-2, -2)
#     }
    
#     current_x, current_y = 0, 0
#     for i in range(len(sequence) - 1):
#         dinucl = sequence[i:i+2]
#         dx, dy = dinucleotide_vectors.get(dinucl, (0, 0))
#         current_x += dx
#         current_y += dy
#         x[i+1] = current_x
#         y[i+1] = current_y
        
#     return x, y

def plot_dna_curves(file_path, file_format="fasta", method="dv"):
    # 1. Read the sequence file
    sequence, seq_id = parse_sequence(file_path, file_format)
    print(f"Loaded sequence '{seq_id}' with length: {len(sequence)} bp")
    
    # 2. Extract coordinates based on selected method
    if method.lower() == "dv":
        x, y = generate_dv_curve_coords(sequence)
        title = f"DV-Curve (Dual-Vector) 2D Representation: {seq_id}"
    # elif method.lower() == "dn":
    #     x, y = generate_dn_curve_coords(sequence)
    #     title = f"DN-Curve (Double Nucleotide) 2D Representation: {seq_id}"
    # else:
    #     raise ValueError("Invalid method selection. Use 'dv' or 'dn'.")
        
    fig, ax = plt.subplots(figsize=(10, 7), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(x, y, linewidth=2, color='#1f77b4', label=method.upper())

    ax.plot([x[0]], [y[0]], marker='o', markersize=10, color='green',
            linestyle='none', label="Start (5')")
    ax.plot([x[-1]], [y[-1]], marker='o', markersize=10, color='red',
            linestyle='none', label="End (3')")

    ax.set_title(title, fontsize=16)
    ax.set_xlabel("Cumulative X Vector Walk")
    ax.set_ylabel("Cumulative Y Vector Walk")
    ax.grid(True, color="#eeeeee")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend()

    base_name, _ = os.path.splitext(file_path)
    written = save_figure(fig, base_name, formats=("html", "png", "svg"))
    print(f"[*] Files saved: {' '.join(written)}")
# --- Example Execution Usage ---
if __name__ == "__main__":
    import sys
    # # Create a dummy fasta file to run a proof of concept script
    # example_fasta_content = ">NC_001422.1_coliphage_phiX174\nGAGTTTTATCGCTTCCATGACGCAGAAGTTAACACTTTCGGATATTTCTGATGAGTCGAAAAATTATCTTGATAAAGCAG"
    
    # with open("sample.fasta", "w") as f:
    #     f.write(example_fasta_content)
        
    # Execute visualization for the sample file (Change method to 'dn' for double nucleotide)
    plot_dna_curves(sys.argv[1], file_format=pathlib.Path(sys.argv[1]).suffix.lstrip("."), method="dv")
    # plot_dna_curves("/opt/rica_s/input/pathogens_100.fasta", file_format="fasta", method="dv")
# 