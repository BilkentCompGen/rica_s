#!/usr/bin/env python3
"""List, for each experiment run and each identifier tool, the reads the tool did not classify.

Reads the raw per-read tool outputs left in output/<EXP>/<EXP>_<n>/ and applies the same
"classified" rule each tool's classify.sh uses to build its count TSV:

    Kraken2   .kraken2.output    column 1 == "C"
    BLAST     .blastout.tab.6    read has at least one hit
    minimap2  .minimap2.paf      read appears (PAF only lists mapped reads)
    BWA       .bwa.sam           some record passes samtools view -F 2308
    NGMLR     .ngmlr.sam         same as BWA
    CLARK     .clark.csv.csv     1st_assignment is not NA/UNKNOWN
    CuCLARK   .cuclark.csv.csv   same as CLARK

Note that Kraken2 counts a read as classified at any rank, while its .tsv only counts species.

Outputs (under --out):
    summary.tsv                              one row per experiment/run/tool
    <EXP>/<run>/<tool>.unclassified.txt      read IDs, one per line, in input order
    <EXP>/<run>/unclassified_by_all.txt      reads no available tool classified
    <EXP>/<EXP>_unclassified_by_any.txt      reads at least one tool left unclassified (all runs, deduplicated)
    read_matrix/<run>.tsv                    read x tool, 1 = classified, 0 = not
"""
import argparse
import csv
import glob
import os
import sys

RICA_S_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAM_EXCLUDE = 2308  # unmapped (4) | secondary (256) | supplementary (2048)


def fasta_ids(path):
    ids = []
    with open(path) as f:
        for line in f:
            if line.startswith(">"):
                ids.append(line[1:].split(None, 1)[0])
    return ids


def kraken2_classified(path):
    out = set()
    with open(path) as f:
        for line in f:
            parts = line.split("\t", 2)
            if len(parts) >= 2 and parts[0] == "C":
                out.add(parts[1])
    return out


def first_column(path):
    # BLAST outfmt 6 and PAF: every line is a hit, the query ID is column 1
    out = set()
    with open(path) as f:
        for line in f:
            if line.strip():
                out.add(line.split("\t", 1)[0])
    return out


def sam_classified(path):
    out = set()
    with open(path) as f:
        for line in f:
            if line.startswith("@"):
                continue
            parts = line.split("\t", 2)
            if len(parts) < 2:
                continue
            try:
                flag = int(parts[1])
            except ValueError:
                continue
            if flag & SAM_EXCLUDE == 0:
                out.add(parts[0])
    return out


def clark_classified(path):
    out = set()
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) >= 4 and row[3].strip() not in ("NA", "UNKNOWN", ""):
                out.add(row[0])
    return out


# (short name, display name, file suffix after *.cleaned.fasta, parser)
TOOLS = [
    ("kraken2", "Kraken2", ".kraken2.output", kraken2_classified),
    ("blast", "BLAST", ".blastout.tab.6", first_column),
    ("minimap2", "minimap2", ".minimap2.paf", first_column),
    ("bwa", "BWA", ".bwa.sam", sam_classified),
    ("ngmlr", "NGMLR", ".ngmlr.sam", sam_classified),
    ("clark", "CLARK", ".clark.csv.csv", clark_classified),
    ("cuclark", "CuCLARK", ".cuclark.csv.csv", clark_classified),
]


def write_lines(path, lines):
    with open(path, "w") as f:
        for line in lines:
            f.write(f"{line}\n")


def process_run(exp, run_dir, out_root, summary_rows):
    run = os.path.basename(run_dir.rstrip("/"))
    fastas = sorted(glob.glob(os.path.join(run_dir, "*.cleaned.fasta")))
    if not fastas:
        print(f"[!] {run}: no *.cleaned.fasta, skipping", file=sys.stderr)
        return
    if len(fastas) > 1:
        print(f"[!] {run}: several *.cleaned.fasta, using {os.path.basename(fastas[0])}", file=sys.stderr)
    fasta = fastas[0]

    reads = fasta_ids(fasta)
    read_set = set(reads)
    total = len(reads)

    run_out = os.path.join(out_root, exp, run)
    os.makedirs(run_out, exist_ok=True)

    present = []  # (short, classified set)
    for short, display, suffix, parser in TOOLS:
        path = fasta + suffix
        if not os.path.isfile(path):
            summary_rows.append([exp, run, display, total, "missing", "missing", "missing"])
            continue
        classified = parser(path) & read_set
        unclassified = [r for r in reads if r not in classified]
        write_lines(os.path.join(run_out, f"{short}.unclassified.txt"), unclassified)
        pct = 100.0 * len(unclassified) / total if total else 0.0
        summary_rows.append([exp, run, display, total, len(classified), len(unclassified), f"{pct:.2f}"])
        present.append((short, classified))

    by_any = []
    if present:
        by_any = [r for r in reads if not all(r in c for _, c in present)]
        by_all = [r for r in reads if not any(r in c for _, c in present)]
        write_lines(os.path.join(run_out, "unclassified_by_all.txt"), by_all)

        matrix_dir = os.path.join(out_root, "read_matrix")
        os.makedirs(matrix_dir, exist_ok=True)
        with open(os.path.join(matrix_dir, f"{run}.tsv"), "w") as f:
            f.write("read_id\t" + "\t".join(s for s, _ in present) + "\tn_tools_classified\n")
            for r in reads:
                flags = [1 if r in c else 0 for _, c in present]
                f.write(r + "\t" + "\t".join(map(str, flags)) + f"\t{sum(flags)}\n")
        print(f"[i] {run}: {total} reads, {len(present)} tools, {len(by_all)} unclassified by all")
    else:
        print(f"[!] {run}: no tool outputs found", file=sys.stderr)
    return by_any


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", default=os.path.join(RICA_S_HOME, "output"),
                    help="pipeline output directory (default: %(default)s)")
    ap.add_argument("--out", default=os.path.join(RICA_S_HOME, "_analysis", "unclassified_reads"),
                    help="where to write results (default: %(default)s)")
    ap.add_argument("--experiments", nargs="+", help="only these experiments (default: all)")
    args = ap.parse_args()

    if args.experiments:
        experiments = args.experiments
    else:
        experiments = sorted(d for d in os.listdir(args.output_root)
                             if os.path.isdir(os.path.join(args.output_root, d)) and not d.startswith((".", "_")))

    os.makedirs(args.out, exist_ok=True)
    summary_rows = []
    for exp in experiments:
        run_dirs = sorted(glob.glob(os.path.join(args.output_root, exp, f"{exp}_*/")))
        if not run_dirs:
            print(f"[!] {exp}: no run directories", file=sys.stderr)
        # union over all runs and tools: reads at least one tool left unclassified
        exp_any = {}
        for run_dir in run_dirs:
            for r in process_run(exp, run_dir, args.out, summary_rows) or []:
                exp_any[r] = None
        if run_dirs:
            os.makedirs(os.path.join(args.out, exp), exist_ok=True)
            write_lines(os.path.join(args.out, exp, f"{exp}_unclassified_by_any.txt"), exp_any)

    summary = os.path.join(args.out, "summary.tsv")
    with open(summary, "w") as f:
        f.write("experiment\trun\ttool\ttotal_reads\tclassified\tunclassified\tpct_unclassified\n")
        for row in summary_rows:
            f.write("\t".join(map(str, row)) + "\n")
    print(f"[i] summary written to {summary}")


if __name__ == "__main__":
    main()
