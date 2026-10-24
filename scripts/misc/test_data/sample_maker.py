#!/usr/bin/env python3
"""
Build a FASTA file of N base pairs by sampling sequences from a list of
input FASTA files, then introduce random errors into 10% of them.

The input FASTA files are listed in a text file, one per line, optionally
followed by the percentage of the N bp to take from that file:

  # path                          percent
  772_Bartonella/refs.fasta       70
  773_Bartonella/refs.fasta       25
  amr_EreA.fasta                  5

The percentages must add up to 100. Leave the column out on every line to
split N equally between the files. Blank lines and lines starting with '#'
are ignored. Relative paths are looked up from the current directory first,
then from the list file's directory.

Sampling, for each file, until that file's share of N bp is reached:
  1. pick a record from the file uniformly at random
  2. take the whole record, or a random fragment of --length bp if given.
     --length 150 gives fragments of exactly 150 bp; --length 150,250 gives
     fragments of random length between 150 and 250 bp. Records shorter
     than the fragment length are taken whole.
The last sequence from each file is trimmed so the total is exactly N
(before indels), and the sequences from all files are shuffled together.

Each header records where the sequence came from, e.g.:
  >seq_12 source=ecoli.fasta record=NC_000913.3 start=10432 end=10582 errors=2

Usage:
  python3 sample_fasta.py -n 1000000 -o out.fasta fastas.txt
  python3 sample_fasta.py -n 50000 --length 150 --seed 42 -o reads.fasta fastas.txt
  python3 sample_fasta.py -n 50000 --length 150,250 -o reads.fasta fastas.txt
"""
import argparse
import os
import random
import sys

BASES = "ACGT"


def read_fasta(path):
    """Return a list of (record_id, sequence) from a FASTA file."""
    records = []
    name, chunks = None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    records.append((name, "".join(chunks).upper()))
                name = line[1:].split()[0] if len(line) > 1 else "unnamed"
                chunks = []
            else:
                chunks.append(line)
    if name is not None:
        records.append((name, "".join(chunks).upper()))
    return [(n, s) for n, s in records if s]


def parse_length(text):
    """Parse '150' -> (150, 150) or '150,250' -> (150, 250)."""
    try:
        parts = [int(x) for x in text.split(",")]
    except ValueError:
        parts = []
    if len(parts) == 1:
        parts *= 2
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"invalid length '{text}': use e.g. 150 or 150,250")
    lo, hi = parts
    if lo < 1 or hi < lo:
        raise argparse.ArgumentTypeError(
            f"invalid length '{text}': need 1 <= MIN <= MAX")
    return lo, hi


def parse_percent(text):
    """Parse '30' or '30%' -> 30.0; return None if it is not a number."""
    try:
        value = float(text.rstrip("%"))
    except ValueError:
        return None
    return value if value >= 0 else None


def read_list(list_path):
    """Return [(path, percent or None)] from the FASTA list file."""
    base = os.path.dirname(os.path.abspath(list_path))
    entries = []
    with open(list_path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(None, 1)
            pct = parse_percent(parts[1]) if len(parts) == 2 else None
            name = parts[0] if pct is not None else line
            path = os.path.expanduser(name)
            if not os.path.isabs(path) and not os.path.exists(path):
                path = os.path.join(base, path)
            if not os.path.isfile(path):
                sys.exit(f"error: {list_path} line {n}: file not found: {name}")
            entries.append((path, pct, n))
    if not entries:
        sys.exit(f"error: no FASTA files listed in {list_path}")

    missing = [n for _, pct, n in entries if pct is None]
    if missing and len(missing) < len(entries):
        sys.exit(f"error: {list_path}: give a percentage on every line or on "
                 f"none (missing on line(s) {', '.join(map(str, missing))})")
    if not missing:
        total = sum(pct for _, pct, _ in entries)
        if abs(total - 100) > 0.01:
            sys.exit(f"error: {list_path}: percentages add up to {total:g}, "
                     f"not 100")
    return [(path, pct) for path, pct, _ in entries]


def split_bases(total, weights):
    """Split total bp by weights into integers that add up to total."""
    wsum = sum(weights)
    raw = [total * w / wsum for w in weights]
    parts = [int(r) for r in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - parts[i],
                          reverse=True)
    for i in by_remainder[:total - sum(parts)]:
        parts[i] += 1
    return parts


def mutate(seq, rate, types, rng):
    """Apply random substitutions/insertions/deletions; at least one error."""
    n_errors = max(1, sum(rng.random() < rate for _ in range(len(seq))))
    seq = list(seq)
    for _ in range(n_errors):
        kind = rng.choice(types)
        if kind == "del" and len(seq) <= 1:
            kind = "sub"
        if kind == "sub":
            i = rng.randrange(len(seq))
            seq[i] = rng.choice([b for b in BASES if b != seq[i]])
        elif kind == "ins":
            seq.insert(rng.randrange(len(seq) + 1), rng.choice(BASES))
        else:
            del seq[rng.randrange(len(seq))]
    return "".join(seq), n_errors


def write_fasta(fh, header, seq, width=60):
    fh.write(f">{header}\n")
    for i in range(0, len(seq), width):
        fh.write(seq[i:i + width] + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fasta_list",
                   help="text file listing the input FASTA files, one per "
                        "line, optionally followed by a percentage of N")
    p.add_argument("-n", "--bases", type=int, required=True,
                   help="total number of base pairs to generate (N)")
    p.add_argument("-o", "--output", help="output FASTA (default: stdout)")
    p.add_argument("-l", "--length", type=parse_length,
                   help="fragment length, either fixed (150) or MIN,MAX "
                        "for a random length in that range (150,250); "
                        "records shorter than that are taken whole. "
                        "If omitted, whole records are taken")
    p.add_argument("--error-fraction", type=float, default=0.10,
                   help="fraction of sequences that receive errors (default 0.10)")
    p.add_argument("--error-rate", type=float, default=0.01,
                   help="per-base error rate inside an affected sequence "
                        "(default 0.01; at least 1 error is always added)")
    p.add_argument("--error-types", default="sub",
                   help="comma-separated: sub,ins,del (default: sub). "
                        "ins/del change lengths, so the total drifts from N")
    p.add_argument("--seed", type=int, help="random seed for reproducibility")
    args = p.parse_args()

    if args.bases <= 0:
        p.error("-n must be positive")
    types = [t.strip() for t in args.error_types.split(",") if t.strip()]
    if not types or any(t not in ("sub", "ins", "del") for t in types):
        p.error("--error-types must be a comma list of sub, ins, del")

    rng = random.Random(args.seed)

    # Load files. Without percentages, empty files are skipped and N is
    # split equally among the rest; with percentages, an empty file with a
    # share above 0 is an error.
    pool = []  # (source, records, percent or None)
    for path, pct in read_list(args.fasta_list):
        if pct == 0:
            continue
        recs = read_fasta(path)
        if recs:
            pool.append((os.path.basename(path), recs, pct))
        elif pct is None:
            print(f"warning: skipping {path} (no sequences found)", file=sys.stderr)
        else:
            sys.exit(f"error: {path} has no sequences but is assigned {pct:g}%")
    if not pool:
        sys.exit("error: no sequences in any input file")

    weights = [1 if pct is None else pct for _, _, pct in pool]
    targets = split_bases(args.bases, weights)

    # Sample from each file until its share of N bp is reached.
    sampled = []  # (source, record_id, start, end, seq)
    for (source, recs, _), target in zip(pool, targets):
        got = 0
        while got < target:
            rec_id, full = rng.choice(recs)
            if args.length:
                # Draw a length in range; a shorter record is taken whole.
                frag = min(rng.randint(*args.length), len(full))
                start = rng.randrange(len(full) - frag + 1)
                end = start + frag
            else:
                start, end = 0, len(full)
            end = min(end, start + target - got)  # trim the last one to hit the share
            sampled.append((source, rec_id, start, end, full[start:end]))
            got += end - start
    rng.shuffle(sampled)

    # Pick exactly error_fraction of the sequences to mutate.
    # Always mutate at least one sequence when errors are requested, so small
    # samples (e.g. 3 whole genomes) don't round down to zero.
    n_bad = min(len(sampled), int(len(sampled) * args.error_fraction + 0.5))
    if args.error_fraction > 0 and n_bad == 0:
        n_bad = 1
    bad = set(rng.sample(range(len(sampled)), n_bad))

    out = open(args.output, "w") if args.output else sys.stdout
    out_bp = 0
    try:
        for i, (source, rec_id, start, end, seq) in enumerate(sampled, 1):
            n_err = 0
            if i - 1 in bad:
                seq, n_err = mutate(seq, args.error_rate, types, rng)
            out_bp += len(seq)
            header = (f"seq_{i} source={source} record={rec_id} "
                      f"start={start + 1} end={end} errors={n_err}")
            write_fasta(out, header, seq)
    finally:
        if out is not sys.stdout:
            out.close()

    print(f"wrote {len(sampled)} sequences, {out_bp} bp, "
          f"{n_bad} with errors", file=sys.stderr)


if __name__ == "__main__":
    main()
