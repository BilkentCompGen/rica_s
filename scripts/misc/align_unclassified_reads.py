#!/usr/bin/env python3
"""Align each experiment's unclassified reads to its reference FASTA with minimap2.

Input (from find_unclassified_reads.py), under --root:
    <EXP>/<EXP>_unclassified_by_any.txt      read IDs, one per line
    <PREFIX>.fasta                           reference, where <PREFIX> is <EXP> without "_<n>H"
                                             (e.g. 05B_0.001A_1H -> 05B_0.001A.fasta)
Read sequences come from output/<EXP>/<EXP>_*/*.cleaned.fasta.

Experiments sharing a reference are aligned in one minimap2 call, so each reference is
indexed once. Reads are tagged "<EXP>|<read_id>" on the way in and split back out.

Outputs:
    <EXP>/<EXP>_unclassified_by_any.fasta            the reads that were aligned
    <EXP>/<EXP>_unclassified_by_any.minimap2.paf     raw minimap2 output (primary alignments)
    <EXP>/<EXP>_unclassified_by_any.best_hits.tsv    one row per read, best hit or "unaligned"
    <EXP>/<EXP>_unclassified_by_any.target_counts.tsv reads per best-hit target
    minimap2_summary.tsv                             one row per experiment
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import threading
from collections import Counter, defaultdict

RICA_S_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEP = "|"
HUMAN_PREFIXES = ("chr", "HLA-")


def reference_prefix(exp):
    return re.sub(r"_\d+H$", "", exp)


def read_fasta(path, wanted):
    # yields (id, sequence) for reads whose ID is in wanted
    rid, chunks = None, []
    with open(path) as f:
        for line in f:
            if line.startswith(">"):
                if rid in wanted:
                    yield rid, "".join(chunks)
                rid, chunks = line[1:].split(None, 1)[0], []
            else:
                chunks.append(line.strip())
    if rid in wanted:
        yield rid, "".join(chunks)


def target_descriptions(ref):
    # header lines only, via grep (much faster than Python on a multi-GB file)
    out = {}
    res = subprocess.run(["grep", "^>", ref], capture_output=True, text=True, check=True)
    for line in res.stdout.splitlines():
        parts = line[1:].split(None, 1)
        out[parts[0]] = parts[1] if len(parts) > 1 else ""
    return out


def origin(target):
    return "human" if target.startswith(HUMAN_PREFIXES) else "non-human"


def extract_reads(exp, output_root, root):
    ids_file = os.path.join(root, exp, f"{exp}_unclassified_by_any.txt")
    with open(ids_file) as f:
        order = [line.strip() for line in f if line.strip()]
    wanted = set(order)

    seqs = {}
    for fasta in sorted(glob.glob(os.path.join(output_root, exp, f"{exp}_*", "*.cleaned.fasta"))):
        for rid, seq in read_fasta(fasta, wanted):
            seqs.setdefault(rid, seq)
    missing = wanted - seqs.keys()
    if missing:
        print(f"[!] {exp}: {len(missing)} read IDs not found in output/{exp}", file=sys.stderr)

    reads = [(rid, seqs[rid]) for rid in order if rid in seqs]
    with open(os.path.join(root, exp, f"{exp}_unclassified_by_any.fasta"), "w") as f:
        for rid, seq in reads:
            f.write(f">{rid}\n{seq}\n")
    return reads


def run_minimap2(ref, batch, root, threads, preset):
    # batch: {exp: [(read_id, seq), ...]}; writes one PAF per experiment
    cmd = ["minimap2", "-t", str(threads), "-c", "-x", preset, "--secondary=no", ref, "-"]
    print(f"[cmd]> {' '.join(cmd)}  ({sum(len(r) for r in batch.values())} reads from {len(batch)} experiments)")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def feed():
        try:
            for exp, reads in batch.items():
                for rid, seq in reads:
                    proc.stdin.write(f">{exp}{SEP}{rid}\n{seq}\n")
        finally:
            proc.stdin.close()

    writer = threading.Thread(target=feed)
    writer.start()

    pafs = {exp: open(os.path.join(root, exp, f"{exp}_unclassified_by_any.minimap2.paf"), "w") for exp in batch}
    try:
        for line in proc.stdout:
            exp, rest = line.split(SEP, 1)
            pafs[exp].write(rest)
    finally:
        for f in pafs.values():
            f.close()
    writer.join()
    if proc.wait() != 0:
        sys.exit(f"[!] minimap2 failed on {ref} (exit {proc.returncode})")


def summarize(exp, reads, root, descriptions, ref_name, summary_rows):
    best = {}  # read_id -> PAF fields of its best primary alignment
    with open(os.path.join(root, exp, f"{exp}_unclassified_by_any.minimap2.paf")) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if "tp:A:P" not in p[12:]:
                continue
            if p[0] not in best or int(p[9]) > int(best[p[0]][9]):
                best[p[0]] = p

    counts = Counter()
    n_human = 0
    with open(os.path.join(root, exp, f"{exp}_unclassified_by_any.best_hits.tsv"), "w") as f:
        f.write("read_id\tread_len\tstatus\ttarget\torigin\tdescription\tmapq\tidentity\tquery_coverage\n")
        for rid, seq in reads:
            p = best.get(rid)
            if p is None:
                f.write(f"{rid}\t{len(seq)}\tunaligned\t\t\t\t\t\t\n")
                continue
            target, org = p[5], origin(p[5])
            n_human += org == "human"
            counts[(target, org)] += 1
            identity = int(p[9]) / int(p[10]) if int(p[10]) else 0.0
            cov = (int(p[3]) - int(p[2])) / int(p[1]) if int(p[1]) else 0.0
            f.write(f"{rid}\t{p[1]}\taligned\t{target}\t{org}\t{descriptions.get(target, '')}\t"
                    f"{p[11]}\t{identity:.4f}\t{cov:.4f}\n")

    with open(os.path.join(root, exp, f"{exp}_unclassified_by_any.target_counts.tsv"), "w") as f:
        f.write("target\torigin\tdescription\treads\n")
        for (target, org), n in counts.most_common():
            f.write(f"{target}\t{org}\t{descriptions.get(target, '')}\t{n}\n")

    aligned = len([r for r, _ in reads if r in best])
    summary_rows.append([exp, ref_name, len(reads), aligned, n_human, aligned - n_human, len(reads) - aligned])
    print(f"[i] {exp}: {len(reads)} reads, {aligned} aligned ({n_human} human), {len(reads) - aligned} unaligned")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.join(RICA_S_HOME, "_analysis", "unclassified_reads"),
                    help="folder with <EXP>/ subfolders and reference FASTAs (default: %(default)s)")
    ap.add_argument("--output-root", default=os.path.join(RICA_S_HOME, "output"),
                    help="pipeline output, source of read sequences (default: %(default)s)")
    ap.add_argument("--experiments", nargs="+", help="only these experiments (default: all found)")
    ap.add_argument("--threads", type=int, default=os.cpu_count(), help="minimap2 threads (default: %(default)s)")
    ap.add_argument("--preset", default="map-ont", help="minimap2 -x preset (default: %(default)s)")
    args = ap.parse_args()

    found = sorted(os.path.basename(os.path.dirname(p))
                   for p in glob.glob(os.path.join(args.root, "*", "*_unclassified_by_any.txt")))
    experiments = [e for e in found if not args.experiments or e in args.experiments]

    groups = defaultdict(list)  # reference path -> experiments
    for exp in experiments:
        ref = os.path.join(args.root, f"{reference_prefix(exp)}.fasta")
        if not os.path.isfile(ref):
            print(f"[!] {exp}: no reference {os.path.basename(ref)}, skipping", file=sys.stderr)
            continue
        groups[ref].append(exp)

    summary_rows = []
    for ref, exps in sorted(groups.items()):
        batch = {}
        for exp in exps:
            reads = extract_reads(exp, args.output_root, args.root)
            if reads:
                batch[exp] = reads
            else:
                print(f"[!] {exp}: no reads to align", file=sys.stderr)
                summary_rows.append([exp, os.path.basename(ref), 0, 0, 0, 0, 0])
        if not batch:
            continue
        run_minimap2(ref, batch, args.root, args.threads, args.preset)
        descriptions = target_descriptions(ref)
        for exp, reads in batch.items():
            summarize(exp, reads, args.root, descriptions, os.path.basename(ref), summary_rows)

    summary = os.path.join(args.root, "minimap2_summary.tsv")
    with open(summary, "w") as f:
        f.write("experiment\treference\treads\taligned\taligned_human\taligned_non_human\tunaligned\n")
        for row in sorted(summary_rows):
            f.write("\t".join(map(str, row)) + "\n")
    print(f"[i] summary written to {summary}")


if __name__ == "__main__":
    main()
