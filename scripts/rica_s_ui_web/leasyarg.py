"""
Parse L-EasyARG results into rows shaped like the ABRicate AMR table.

ARG hits come from ARG/<sample>_ARG_filter.txt (minimap2 PAF against CARD).
MGE hits come from MGE/<sample>_filtered_hits.txt (LAST hits against mobileOG).
L-EasyARG drops the read name (t_name) from filtered_hits.txt, so it is recovered
by matching each hit back to its line in MGE/<sample>_my-alignments.psl.
"""
import csv
from functools import lru_cache
from pathlib import Path

from scripts.config import c

ARG_SUFFIX = "_ARG_filter.txt"
MGE_SUFFIX = "_filtered_hits.txt"

# filtered_hits.txt columns, as written by L-EasyARG, and their PSL column index
MGE_KEY_PSL_COLUMNS = {"matches": 0, "strand": 8, "q_name": 9, "q_len": 10, "q_start": 11,
                       "q_end": 12, "t_len": 14, "t_start": 15, "t_end": 16, "block_count": 17}
PSL_T_NAME = 13


@lru_cache(maxsize=1)
def card_index():
    path = Path(c["RICA_S_HOME"]) / \
        "tools/rica_s_pr_l-easyarg/database/card/aro_index.tsv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        index = {}
        for row in csv.DictReader(handle, delimiter="\t"):
            index.setdefault(row["CARD Short Name"], row)
        return index


def percent(part, whole):
    return f"{100 * part / whole:.2f}" if whole else ""


def amr_row(gene, coverage, identity, product, resistance, database, accession,
            reads_name, sequence):
    # same order as web_ui.AMR_COLUMNS
    return [gene, coverage, identity, product, resistance, database, accession,
            reads_name, sequence]


def arg_rows(path: Path, reads_name: str):
    card = card_index()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) < 11 or not cols[1].isdigit():
            continue
        gene = cols[5].split("|")[-1]
        gene_len, gene_start, gene_end = int(
            cols[6]), int(cols[7]), int(cols[8])
        info = card.get(gene, {})
        rows.append(amr_row(
            gene,
            percent(gene_end - gene_start, gene_len),
            percent(int(cols[9]), int(cols[10])),
            info.get("ARO Name", ""),
            info.get("Drug Class", ""),
            "card",
            info.get("DNA Accession", ""),
            reads_name,
            cols[0]))
    return rows


def psl_read_names(psl_path: Path):
    names = {}
    if not psl_path.exists():
        return names
    for line in psl_path.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) > PSL_T_NAME:
            key = tuple(cols[i] for i in MGE_KEY_PSL_COLUMNS.values())
            names.setdefault(key, cols[PSL_T_NAME])
    return names


def mge_rows(path: Path, psl_path: Path, reads_name: str):
    with open(path, newline="", encoding="utf-8") as handle:
        hits = list(csv.DictReader(handle, delimiter="\t"))
    if not hits:
        return []

    read_names = {} if "t_name" in hits[0] else psl_read_names(psl_path)
    rows = []
    for hit in hits:
        key = tuple(hit.get(column, "") for column in MGE_KEY_PSL_COLUMNS)
        read = hit.get("t_name") or read_names.get(key, "?")

        # mobileOG header: id|name|accession|major category|minor categories|source|evidence
        fields = (hit["q_name"].split("|") + [""] * 7)[:7]
        name = fields[1] if fields[1] and not fields[1].startswith(
            "NA") else fields[0]
        product = fields[3] if fields[4] in (
            "", "NA") else f"{fields[3]}:{fields[4]}"

        q_len, q_start, q_end = int(hit["q_len"]), int(
            hit["q_start"]), int(hit["q_end"])
        rows.append(amr_row(
            name,
            percent(q_end - q_start, q_len),
            percent(int(hit["matches"]), q_end - q_start),
            product,
            "",
            "mobileOG",
            fields[2],
            reads_name,
            read))
    return rows


def sample_reads_name(run_dir: Path, sample: str):
    return f"{sample}.fasta" if (run_dir / f"{sample}.fasta").exists() else sample


def result_rows(run_dir: Path):
    """Yield (source file relative to run_dir, rows loader) for each L-EasyARG result file."""
    for path in sorted(run_dir.glob(f"ARG/*{ARG_SUFFIX}")):
        sample = path.name[:-len(ARG_SUFFIX)]
        yield (path.relative_to(run_dir).as_posix(),
               lambda p=path, s=sample: arg_rows(p, sample_reads_name(run_dir, s)))

    for path in sorted(run_dir.glob(f"MGE/*{MGE_SUFFIX}")):
        sample = path.name[:-len(MGE_SUFFIX)]
        psl = path.with_name(f"{sample}_my-alignments.psl")
        yield (path.relative_to(run_dir).as_posix(),
               lambda p=path, q=psl, s=sample: mge_rows(p, q, sample_reads_name(run_dir, s)))
