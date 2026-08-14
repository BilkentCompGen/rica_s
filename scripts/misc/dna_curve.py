#! /usr/bin/python3

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from Bio import SeqIO
import pathlib


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
    """
    Generates an interactive Plotly HTML chart tracking the sequence walk.
    """
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
        
    # 3. Optimize data display (Subsample only for massive files to preserve memory)
    # Plotly handles up to 500k points easily, but let's map indexes for custom hover data
    indices = list(range(len(x)))
    
    # 4. Generate Interactive Plotly Trace
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode='lines',
        line=dict(width=2, color='#1f77b4'),
        name=method.upper(),
        hoverinfo='text',
        text=[f"Base Position: {idx}<br>X: {coord_x:.0f}, Y: {coord_y:.0f}" for idx, coord_x, coord_y in zip(indices, x, y)]
    ))
    
    # 5. Add start/end landmarks
    fig.add_trace(go.Scatter(x=[x[0]], y=[y[0]], mode='markers', marker=dict(size=10, color='green'), name='Start (5\')'))
    fig.add_trace(go.Scatter(x=[x[-1]], y=[y[-1]], mode='markers', marker=dict(size=10, color='red'), name='End (3\')'))
    
    # 6. Apply formatting layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Cumulative X Vector Walk",
        yaxis_title="Cumulative Y Vector Walk",
        template="plotly_white",
        hovermode="closest",
        showlegend=True,
        # width=1000,
        # height=700
    )
    
    # 7. Open plot dynamically in browser
    # fig.show()
    fig.save("cosa.html")
# --- Example Execution Usage ---
if __name__ == "__main__":
    import sys
    # # Create a dummy fasta file to run a proof of concept script
    # example_fasta_content = ">NC_001422.1_coliphage_phiX174\nGAGTTTTATCGCTTCCATGACGCAGAAGTTAACACTTTCGGATATTTCTGATGAGTCGAAAAATTATCTTGATAAAGCAG"
    
    # with open("sample.fasta", "w") as f:
    #     f.write(example_fasta_content)
        
    # Execute visualization for the sample file (Change method to 'dn' for double nucleotide)
    plot_dna_curves(sys.argv[1], file_format=pathlib.Path(sys.argv[1]).suffix, method="dv")
    # plot_dna_curves("/opt/rica_s/input/pathogens_100.fasta", file_format="fasta", method="dv")
# 