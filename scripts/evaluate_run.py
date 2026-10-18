"""Evaluate one run's classification (stage 2) and AMR profiling (stage 3) results.

The run's outputs are found under output/<RUNID>/<RUNID>_N/ and scored per read
against user-supplied truth tables (one file per run, tab-separated, with header):

  pathogens.tsv   read_id  species         one row per read; species '-' = no pathogen
  amr.tsv         read_id  gene  [aliases] one row per (read, gene); aliases '|'-separated

Usage (from /opt/rica_s):
  python -m scripts.evaluate_run RUNID [--pathogens P.tsv] [--amr A.tsv] [--min-reads 1] [--outdir DIR]


P.tsv example:

read_id	    species
seq_1	    Klebsiella pneumoniae
seq_3	    Klebsiella pneumoniae
seq_39	    Escherichia coli
seq_40	    Escherichia coli
seq_2	    Acinetobacter baumannii

A.tsv example:

read_id	    gene	aliases
seq_330	    dfrA5	DFRA
seq_399	    dfrA5
seq_1052	dfrA5
seq_2257	EreA	ere(A)|EreA2|ere(A2)
seq_2627	EreA
seq_2665	floR2	floR|CmlA9|FLOR
seq_3392	floR2


"""

import argparse
import datetime
import glob
import html
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

from scripts.config import PROJECT_HOME, run_outdir, subrun_dirs, read_run_info, run_info_tools
from scripts.misc.name_resolver import NameResolver
from scripts.stage_2_classify import extract_identifier
from scripts.tool_registry import display_name

logger = logging.getLogger(__name__)

SPP_TARBALL = os.path.join(PROJECT_HOME, "scripts", "misc", "spp.tar.gz")
REF_NAMES_CSV = os.path.join(PROJECT_HOME, "reference_genomes", "output_names.csv")
EVAL_ROOT = os.path.join(PROJECT_HOME, "evaluation")
STATIC_DIR = os.path.join(PROJECT_HOME, "scripts", "rica_s_ui_web", "static")

NONE = "none"                  # truth: read carries no pathogen
UNCLASSIFIED = "unclassified"  # prediction: tool made no call
UNRESOLVED = "unresolved"      # prediction: call whose id has no species name
ABOVE_RANK = "above_rank"      # prediction: call made above the rank being scored
NO_CALL = (UNCLASSIFIED, UNRESOLVED, ABOVE_RANK)

# Names that are not species or genera, e.g. kraken2 calls at family level and up
HIGHER_TAXA = {"cellular organisms", "root", "Bacteria", "Archaea", "Eukaryota"}
HIGHER_SUFFIXES = ("aceae", "ales", "ineae", "idae", "ota", "bacteria", "etes")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def prf(tp, fp, fn):
    """Precision, recall and F1 from counts. Undefined values are NaN."""
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    recall = tp / (tp + fn) if (tp + fn) else np.nan
    if tp:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0 if (fp or fn) else np.nan  # nothing right but something to get right
    return precision, recall, f1


def binomial(name):
    """First two words of a taxon name (drops subsp./strain parts)."""
    if not isinstance(name, str) or not name.strip():
        return None
    return " ".join(name.replace("[", "").replace("]", "").split()[:2])


def taxon_rank(name):
    """'species', 'genus' or 'higher', guessed from the shape of the name."""
    words = name.split()
    if name in HIGHER_TAXA or (len(words) == 1 and name.endswith(HIGHER_SUFFIXES)):
        return "higher"
    return "species" if len(words) >= 2 and words[1].islower() else "genus"


def normalize_gene(name):
    """(Tmt)dfrA5, dfrA5_4 and dfrA5 all become 'dfra5'."""
    s = re.sub(r"^\([^)]*\)", "", str(name).strip())
    s = re.sub(r"_\d+$", "", s)
    return re.sub(r"[()\-_'\s]", "", s).lower()


def describe(values, prefix):
    s = pd.Series(values, dtype=float).dropna()
    stats = {"mean": s.mean(), "median": s.median(), "sd": s.std(ddof=1),
             "min": s.min(), "max": s.max()} if len(s) else {}
    return {f"{prefix}_{k}": stats.get(k, np.nan) for k in ("mean", "median", "sd", "min", "max")}


def subrun_files(runid, pattern):
    """Every file matching pattern in any sub-run directory, skipping empty ones."""
    paths = []
    for _, _, path in subrun_dirs(runid):
        paths.extend(p for p in sorted(glob.glob(os.path.join(path, pattern))) if os.path.getsize(p))
    return paths


# --------------------------------------------------------------------------- #
# Truth
# --------------------------------------------------------------------------- #

def read_truth_tsv(path, required):
    df = pd.read_csv(path, sep="\t", comment="#", dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sys.exit(f"[x]> {path} is missing column(s): {', '.join(missing)}")
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df[df["read_id"] != ""]


def load_pathogen_truth(path):
    """Series read_id -> true label ('none' for reads without a pathogen)."""
    df = read_truth_tsv(path, ["read_id", "species"])
    labels = df["species"].where(~df["species"].isin(["", "-", NONE]), NONE)
    labels = labels.map(lambda s: s if s == NONE else binomial(s))
    return pd.Series(labels.values, index=df["read_id"]).groupby(level=0).first()


def load_amr_truth(path):
    """(DataFrame read_id, gene) of true pairs, and normalized alias -> gene map."""
    df = read_truth_tsv(path, ["read_id", "gene"])
    if "aliases" not in df.columns:
        df["aliases"] = ""
    alias = {}
    for gene, aliases in zip(df["gene"], df["aliases"]):
        for name in [gene] + aliases.split("|"):
            if name.strip():
                alias[normalize_gene(name)] = gene
    pairs = df[["read_id", "gene"]].drop_duplicates().reset_index(drop=True)
    return pairs, alias


def predicted_at_rank(pred, rank, truth_genera):
    """Map a predicted name onto the label space of one rank.

    A call above the scored rank ("Enterobacteriaceae" at genus, "Klebsiella"
    at species) is not a wrong taxon, only a less specific one, so it becomes
    ABOVE_RANK and counts as no call. A genus-only truth label ("Enterobacter")
    absorbs every prediction inside that genus at species rank.
    """
    if pred in NO_CALL:
        return pred
    found = taxon_rank(pred)
    if found == "higher":
        return ABOVE_RANK
    genus = pred.split()[0]
    if rank == "genus" or genus in truth_genera:
        return genus
    return pred if found == "species" else ABOVE_RANK


# --------------------------------------------------------------------------- #
# Stage 2: per-read predictions
# --------------------------------------------------------------------------- #

def parse_blast(path):
    df = pd.read_csv(path, sep="\t", header=None, usecols=[0, 1], dtype=str)
    df = df.drop_duplicates(0, keep="first")  # hits are sorted best first per read
    return dict(zip(df[0], df[1].map(extract_identifier)))


def parse_paf(path):
    best = {}
    with open(path) as fh:
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 12:
                continue
            score = next((int(c[5:]) for c in cols[12:] if c.startswith("AS:i:")), int(cols[9]))
            if cols[0] not in best or score > best[cols[0]][0]:
                best[cols[0]] = (score, cols[5])
    return {read: extract_identifier(target) for read, (_, target) in best.items()}


def parse_sam(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            cols = line.split("\t", 4)
            # 4 unmapped, 256 secondary, 2048 supplementary
            if int(cols[1]) & 2308 or cols[2] == "*":
                out.setdefault(cols[0], None)
            else:
                out[cols[0]] = extract_identifier(cols[2])
    return out


def parse_clark(path):
    df = pd.read_csv(path, dtype=str, skipinitialspace=True, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return {read: (None if taxid in ("NA", "UNKNOWN", "") else taxid)
            for read, taxid in zip(df["Object_ID"], df["1st_assignment"])}


def parse_kraken(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            cols = line.split("\t", 4)
            if len(cols) >= 3:
                out[cols[1]] = cols[2] if cols[0] == "C" and cols[2] != "0" else None
    return out


# container name -> (raw per-read file pattern, parser)
CLASSIFIERS = {
    "rica_s_id_blast": ("*.blastout.tab.6", parse_blast),
    "rica_s_id_bwa": ("*.bwa.sam", parse_sam),
    "rica_s_id_clark": ("*.clark.csv.csv", parse_clark),
    "rica_s_id_cuclark": ("*.cuclark.csv.csv", parse_clark),
    "rica_s_id_kraken2": ("*.kraken2.output", parse_kraken),
    "rica_s_id_minimap2": ("*.minimap2.paf", parse_paf),
    "rica_s_id_ngmlr": ("*.ngmlr.sam", parse_sam),
}


class Resolver:
    """Bulk accession/taxid -> binomial lookup over the NameResolver table."""

    def __init__(self):
        logger.info("[i]> loading name resolver table")
        table = NameResolver(SPP_TARBALL).df
        self.table = table.drop_duplicates("id").set_index("id")["spp"]
        self.ref = {}
        if os.path.exists(REF_NAMES_CSV):
            ref = pd.read_csv(REF_NAMES_CSV, dtype=str)
            self.ref = dict(zip(ref["Accession_Number"], ref["Species_Name"]))

    def resolve(self, raw):
        """Series read_id -> species, 'unclassified' or 'unresolved'."""
        ids = pd.Series(raw, dtype=object)
        names = ids.map(self.table)
        fallback = ids.map(self.ref).fillna(ids.str.split(".").str[0].map(self.ref))
        names = names.fillna(fallback).map(binomial)
        names[names.isna()] = UNRESOLVED
        names[ids.isna()] = UNCLASSIFIED
        return names


def stage2_predictions(runid, resolver):
    """{container: Series read_id -> predicted species} for every tool with output."""
    preds = {}
    for tool, (pattern, parser) in CLASSIFIERS.items():
        paths = subrun_files(runid, pattern)
        if not paths:
            continue
        raw = {}
        for path in paths:
            raw.update(parser(path))
        preds[tool] = resolver.resolve(raw)
    return preds


# --------------------------------------------------------------------------- #
# Stage 2: metrics
# --------------------------------------------------------------------------- #

def trim_confusion(confusion, top=15):
    """Keep truth columns and no-call columns plus the top other columns; fold the rest."""
    keep = [c for c in confusion.columns if c in confusion.index or c in NO_CALL]
    rest = confusion.drop(columns=keep)
    top_cols = rest.sum().sort_values(ascending=False).head(top).index.tolist()
    out = confusion[keep + top_cols].copy()
    other = rest.drop(columns=top_cols).sum(axis=1)
    if other.sum():
        out["other"] = other
    return out


def stage2_metrics(tool, truth, pred, rank, min_reads):
    df = pd.DataFrame({"truth": truth})
    df["pred"] = df.index.map(pred).fillna(UNCLASSIFIED)
    if rank == "genus":
        df["truth"] = df["truth"].map(lambda t: t if t == NONE else t.split()[0])
    truth_genera = {t for t in df["truth"].unique() if t != NONE and len(t.split()) == 1}
    df["pred"] = df["pred"].map(lambda p: predicted_at_rank(p, rank, truth_genera))

    has_truth = df["truth"] != NONE
    # an unresolved id is still a call (and a wrong one); above-rank is not
    classified = ~df["pred"].isin([UNCLASSIFIED, ABOVE_RANK])
    correct = has_truth & (df["pred"] == df["truth"])
    n = len(df)

    truth_n = df.loc[has_truth, "truth"].value_counts()
    pred_n = df.loc[~df["pred"].isin(NO_CALL), "pred"].value_counts()
    tp_n = df.loc[correct, "truth"].value_counts()

    per_label = []
    for label in sorted(set(truth_n.index) | set(pred_n.index)):
        tp = int(tp_n.get(label, 0))
        support, called = int(truth_n.get(label, 0)), int(pred_n.get(label, 0))
        p, r, f = prf(tp, called - tp, support - tp)
        per_label.append({"tool": display_name(tool), "rank": rank, "label": label,
                          "in_truth": label in truth_n.index, "true_reads": support,
                          "predicted_reads": called, "tp": tp, "fp": called - tp,
                          "fn": support - tp, "precision": p, "recall": r, "f1": f})
    per_label = pd.DataFrame(per_label)

    p, r, f = prf(int(correct.sum()), int((classified & ~correct).sum()), int((has_truth & ~correct).sum()))
    in_truth = per_label[per_label["in_truth"]]
    weights = in_truth["true_reads"] / in_truth["true_reads"].sum()
    overall = {
        "tool": display_name(tool), "rank": rank, "reads": n,
        "reads_with_pathogen": int(has_truth.sum()),
        "classified_pct": 100 * classified.sum() / n,
        "unclassified_pct": 100 * (~classified).sum() / n,
        "above_rank_pct": 100 * (df["pred"] == ABOVE_RANK).sum() / n,
        "unresolved_pct": 100 * (df["pred"] == UNRESOLVED).sum() / n,
        # a read without a pathogen is correct when the tool makes no call on it
        "accuracy": (correct.sum() + (~has_truth & ~classified).sum()) / n,
        "precision": p, "recall": r, "f1": f,
        "macro_precision": in_truth["precision"].mean(),
        "macro_recall": in_truth["recall"].mean(),
        "macro_f1": in_truth["f1"].mean(),
        "weighted_precision": (in_truth["precision"].fillna(0) * weights).sum(),
        "weighted_recall": (in_truth["recall"].fillna(0) * weights).sum(),
        "weighted_f1": (in_truth["f1"].fillna(0) * weights).sum(),
    }

    true_set = set(truth_n.index)
    called_set = set(pred_n[pred_n >= min_reads].index)
    tp, fp, fn = len(true_set & called_set), len(called_set - true_set), len(true_set - called_set)
    sp, sr, sf = prf(tp, fp, fn)
    presence = {"tool": display_name(tool), "rank": rank, "min_reads": min_reads,
                "true_taxa": len(true_set), "called_taxa": len(called_set),
                "tp": tp, "fp": fp, "fn": fn, "precision": sp, "recall": sr, "f1": sf,
                "missed": ", ".join(sorted(true_set - called_set)),
                "false": ", ".join(sorted(called_set - true_set)[:30])}

    confusion = trim_confusion(pd.crosstab(df["truth"], df["pred"])) if rank == "species" else None
    return overall, per_label, presence, confusion


def evaluate_stage2(runid, truth, min_reads):
    preds = stage2_predictions(runid, Resolver())
    if not preds:
        logger.warning("[!]> no stage 2 per-read output found")
        return None

    seen = set().union(*(set(p.index) for p in preds.values()))
    unseen = len(set(truth.index) - seen)
    if unseen:
        logger.warning(f"[!]> {unseen} of {len(truth)} truth reads appear in no stage 2 output "
                       f"(filtered out, or the truth uses different read ids)")
    extra = len(seen - set(truth.index))
    if extra:
        logger.warning(f"[!]> {extra} reads in the stage 2 output are not in the truth; ignored")

    overall, per_label, presence, confusions = [], [], [], {}
    for tool, pred in preds.items():
        for rank in ("species", "genus"):
            o, pl, pr, conf = stage2_metrics(tool, truth, pred, rank, min_reads)
            overall.append(o)
            per_label.append(pl)
            presence.append(pr)
            if conf is not None:
                confusions[display_name(tool)] = conf
    return {"overall": pd.DataFrame(overall), "per_label": pd.concat(per_label, ignore_index=True),
            "presence": pd.DataFrame(presence), "confusions": confusions}


# --------------------------------------------------------------------------- #
# Stage 3: per-read gene hits
# --------------------------------------------------------------------------- #

HIT_COLUMNS = ["tool", "database", "read_id", "gene_raw", "identity", "coverage"]


def abricate_hits(runid):
    frames = []
    for path in subrun_files(runid, "*.abricate.csv"):
        df = pd.read_csv(path, sep="\t", dtype=str)
        frames.append(df[df["#FILE"] != "#FILE"])  # repeated headers from concatenated dbs
    if not frames:
        return pd.DataFrame(columns=HIT_COLUMNS)
    df = pd.concat(frames, ignore_index=True)
    return pd.DataFrame({
        "tool": display_name("rica_s_pr_abricate"), "database": df["DATABASE"],
        "read_id": df["SEQUENCE"], "gene_raw": df["GENE"],
        "identity": pd.to_numeric(df["%IDENTITY"], errors="coerce"),
        "coverage": pd.to_numeric(df["%COVERAGE"], errors="coerce"),
    })


def leasyarg_hits(runid):
    """L-easyARG filtered ARG alignments (PAF; target ends in '|<gene>')."""
    rows = []
    for path in subrun_files(runid, os.path.join("ARG", "*_ARG_filter.txt")):
        with open(path) as fh:
            for line in fh:
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 11 or not cols[1].isdigit():
                    continue
                tlen, tstart, tend = int(cols[6]), int(cols[7]), int(cols[8])
                rows.append((display_name("rica_s_pr_l-easyarg"), "card", cols[0],
                             cols[5].split("|")[-1], 100 * int(cols[9]) / max(int(cols[10]), 1),
                             100 * (tend - tstart) / max(tlen, 1)))
    return pd.DataFrame(rows, columns=HIT_COLUMNS)


# --------------------------------------------------------------------------- #
# Stage 3: metrics
# --------------------------------------------------------------------------- #

def stage3_metrics(tool, database, hits, truth_pairs, min_reads):
    true_set = set(zip(truth_pairs["read_id"], truth_pairs["gene"]))
    pred_set = set(zip(hits["read_id"], hits["gene"]))
    tp, fp, fn = len(true_set & pred_set), len(pred_set - true_set), len(true_set - pred_set)
    p, r, f = prf(tp, fp, fn)

    true_genes = set(truth_pairs["gene"])
    reads_per_gene = hits.drop_duplicates(["read_id", "gene"])["gene"].value_counts()
    called = set(reads_per_gene[reads_per_gene >= min_reads].index)
    gtp, gfp, gfn = len(true_genes & called), len(called - true_genes), len(true_genes - called)
    gp, gr, gf = prf(gtp, gfp, gfn)

    overall = {"tool": tool, "database": database,
               "read_tp": tp, "read_fp": fp, "read_fn": fn,
               "read_precision": p, "read_recall": r, "read_f1": f,
               "gene_tp": gtp, "gene_fp": gfp, "gene_fn": gfn,
               "gene_precision": gp, "gene_recall": gr, "gene_f1": gf,
               "missed_genes": ", ".join(sorted(true_genes - called)),
               "false_genes": ", ".join(sorted(called - true_genes)[:30])}

    per_gene = []
    for gene in sorted(true_genes | called):
        t = {pair for pair in true_set if pair[1] == gene}
        q = {pair for pair in pred_set if pair[1] == gene}
        a, b, c = len(t & q), len(q - t), len(t - q)
        gp_, gr_, gf_ = prf(a, b, c)
        per_gene.append({"tool": tool, "database": database, "gene": gene,
                         "in_truth": gene in true_genes, "true_reads": len(t),
                         "predicted_reads": len(q), "tp": a, "fp": b, "fn": c,
                         "precision": gp_, "recall": gr_, "f1": gf_})

    descr = {"tool": tool, "database": database, "hits": len(hits),
             "reads_with_hit": hits["read_id"].nunique(), "distinct_genes": hits["gene"].nunique(),
             **describe(hits["identity"], "identity"), **describe(hits["coverage"], "coverage")}
    return overall, per_gene, descr


def evaluate_stage3(runid, truth_pairs, alias, min_reads):
    hits = pd.concat([abricate_hits(runid), leasyarg_hits(runid)], ignore_index=True)
    hits["gene"] = hits["gene_raw"].map(lambda g: alias.get(normalize_gene(g), normalize_gene(g)))

    groups = [(t, d, h) for (t, d), h in hits.groupby(["tool", "database"])]
    groups += [(t, "ALL", h) for t, h in hits.groupby("tool") if h["database"].nunique() > 1]
    tools_found = set(hits["tool"])
    for tool in (display_name("rica_s_pr_abricate"), display_name("rica_s_pr_l-easyarg")):
        if tool not in tools_found:
            logger.warning(f"[!]> no {tool} hits found; scored as zero detections")
            groups.append((tool, "-", hits.iloc[0:0]))

    overall, per_gene, descr = [], [], []
    for tool, database, h in groups:
        o, pg, d = stage3_metrics(tool, database, h, truth_pairs, min_reads)
        overall.append(o)
        per_gene.extend(pg)
        descr.append(d)
    return {"overall": pd.DataFrame(overall), "per_gene": pd.DataFrame(per_gene),
            "descr": pd.DataFrame(descr)}


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def truth_summary(pathogens, amr):
    rows = []
    if pathogens is not None:
        counts = pathogens.value_counts()
        for label, n in counts.items():
            rows.append({"truth": "pathogen", "label": label, "reads": int(n),
                         "fraction_pct": 100 * n / counts.sum()})
    if amr is not None:
        for gene, n in amr["gene"].value_counts().items():
            rows.append({"truth": "amr", "label": gene, "reads": int(n), "fraction_pct": np.nan})
    return pd.DataFrame(rows)


def html_table(df):
    if df is None or df.empty:
        return "<p class='muted'>No data.</p>"
    return df.to_html(index=False, border=0, na_rep="", classes="data-table compact",
                      float_format=lambda x: f"{x:.4f}")


def inline_asset(rel):
    """Contents of a web UI static file, so the report works offline as one file."""
    path = os.path.join(STATIC_DIR, rel)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        logger.warning(f"[!]> {path} not found; report tables will be static")
        return ""


# Pagination, sorting and one filter box per column on every .data-table. The
# filter row sits under the header (orderCellsTop keeps sorting on the top
# row), and each box suggests that column's distinct values.
TABLE_JS = """
if (window.jQuery && $.fn.DataTable) {
  $('table.data-table').each(function (n) {
    const $table = $(this);
    const $filters = $('<tr class="filters"></tr>').appendTo($table.find('thead'));
    $table.find('thead tr:first th').each(function () {
      $filters.append('<th><input type="search" placeholder="filter"></th>');
    });
    const dt = $table.DataTable({
      order: [], orderCellsTop: true, autoWidth: false, pageLength: 10,
      lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
    });
    $table.wrap('<div class="table-scroll"></div>');
    dt.columns().every(function (i) {
      const column = this;
      const values = [...new Set(column.data().toArray()
        .map(v => $('<div>').html(v).text().trim()).filter(v => v !== ''))]
        .sort((a, b) => a.localeCompare(b, undefined, {numeric: true})).slice(0, 300);
      const listId = 'dl-' + n + '-' + i;
      const $list = $('<datalist>').attr('id', listId).appendTo(document.body);
      values.forEach(v => $('<option>').attr('value', v).appendTo($list));
      $filters.children().eq(i).find('input').attr('list', listId).on('input', function () {
        if (column.search() !== this.value) column.search(this.value).draw();
      });
    });
  });
}
"""


def write_report(path, meta, truth_df, s2, s3):
    parts = ["<h2>Truth</h2>", html_table(truth_df)]
    if s2:
        parts += ["<h2>Stage 2 · overall per tool</h2>",
                  "<p class='muted'>Precision = correct / classified reads; recall = correct / reads "
                  "with a pathogen; accuracy also counts no-call on pathogen-free reads as correct. "
                  "A call above the scored rank (e.g. a family) counts as no call.</p>",
                  html_table(s2["overall"]),
                  "<h2>Stage 2 · presence/absence</h2>", html_table(s2["presence"]),
                  "<h2>Stage 2 · per species</h2>", html_table(s2["per_label"]),
                  "<h2>Stage 2 · confusion matrices (rows = truth)</h2>"]
        for tool, conf in s2["confusions"].items():
            conf = conf.reset_index()
            conf.columns.name = None
            parts.append(f"<details><summary>{html.escape(tool)}</summary>{html_table(conf)}</details>")
    if s3:
        parts += ["<h2>Stage 3 · overall per tool and database</h2>",
                  "<p class='muted'>Read level scores (read, gene) pairs; gene level scores the set "
                  "of genes detected in at least min_reads reads.</p>",
                  html_table(s3["overall"]),
                  "<h2>Stage 3 · descriptive</h2>", html_table(s3["descr"])]
    meta_html = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
                        for k, v in meta.items())
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RICA-S Evaluation</title>
<style>{inline_asset("css/jquery.dataTables.min.css")}</style>
<script>{inline_asset("js/jquery-3.7.1.min.js")}</script>
<script>{inline_asset("js/jquery.dataTables.min.js")}</script>
<style>
  :root {{ --bg: #f8f9fa; --fg: #212529; --muted: #6c757d; --line: #dee2e6; --head: #e9ecef; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #16181b; --fg: #e6e6e6; --muted: #9aa0a6; --line: #33373c; --head: #23262a; }}
  }}
  html, body {{ width: 100%; max-width: 100vw; overflow-x: hidden; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         margin: 0; padding: 20px 16px; box-sizing: border-box;
         background: var(--bg); color: var(--fg); }}
  h2 {{ font-size: 1.05rem; margin-top: 28px; }}
  .muted {{ color: var(--muted); font-size: 13px; }}
  .table-scroll {{ width: 100%; overflow-x: auto; }}
  .meta td {{ white-space: normal; word-break: break-all; text-align: left; }}
  table {{ border-collapse: collapse; font-size: 13px; margin: 6px 0 12px; }}
  th, td {{ border: 1px solid var(--line); padding: 3px 7px; text-align: right; white-space: nowrap; }}
  th {{ background: var(--head); }}
  details summary {{ cursor: pointer; padding: 4px 0; }}
  .dataTables_wrapper {{ margin: 6px 0 16px; font-size: 13px; }}
  .dataTables_wrapper .dataTables_length, .dataTables_wrapper .dataTables_filter,
  .dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate,
  .dataTables_wrapper .dataTables_paginate .paginate_button {{ color: var(--fg) !important; }}
  .dataTables_wrapper input, .dataTables_wrapper select {{
    background: var(--bg); color: var(--fg); border: 1px solid var(--line); border-radius: 3px; }}
  table.dataTable {{ margin: 6px 0 !important; }}
  table.dataTable tbody tr {{ background: transparent; }}
  table.dataTable tbody tr:hover {{ background: var(--head); }}
  tr.filters th {{ padding: 2px 4px; }}
  tr.filters input {{ width: 100%; min-width: 60px; box-sizing: border-box; font-size: 12px; padding: 2px 4px; }}
</style>
</head>
<body>
<h1>RICA-S evaluation: {html.escape(meta['run'])}</h1>
<table class="meta">{meta_html}</table>
{''.join(parts)}
<script>{TABLE_JS}</script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)


def print_summary(s2, s3):
    pd.set_option("display.width", 200)
    if s2:
        cols = ["tool", "classified_pct", "accuracy", "precision", "recall", "f1", "macro_f1"]
        o = s2["overall"]
        print("\n=== Stage 2: read level, species rank ===")
        print(o.loc[o["rank"] == "species", cols].round(3).to_string(index=False))
    if s3:
        cols = ["tool", "database", "read_precision", "read_recall", "read_f1",
                "gene_precision", "gene_recall", "gene_f1"]
        print("\n=== Stage 3: AMR genes ===")
        print(s3["overall"][cols].round(3).to_string(index=False))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m scripts.evaluate_run",
                                     description=__doc__.split("\n")[0])
    parser.add_argument("runid", help="run directory name under output/")
    parser.add_argument("--pathogens", help="per-read pathogen truth (read_id, species)")
    parser.add_argument("--amr", help="per-read AMR truth (read_id, gene[, aliases])")
    parser.add_argument("--min-reads", type=int, default=1,
                        help="reads needed to call a species/gene present (default: 1)")
    parser.add_argument("--outdir", help="output directory (default: evaluation/<runid>/)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(message)s", stream=sys.stderr)

    if not (args.pathogens or args.amr):
        parser.error("give --pathogens and/or --amr")
    if not subrun_dirs(args.runid):
        sys.exit(f"[x]> no sub-runs found in {run_outdir(args.runid)}")

    info_path = os.path.join(run_outdir(args.runid), f"{args.runid}.info")
    if os.path.exists(info_path):
        selected = run_info_tools(read_run_info(info_path))
        logger.info(f"[i]> run tools: {', '.join(map(display_name, selected)) if selected is not None else 'all'}")

    outdir = args.outdir or os.path.join(EVAL_ROOT, args.runid)
    os.makedirs(outdir, exist_ok=True)

    pathogens = load_pathogen_truth(args.pathogens) if args.pathogens else None
    amr_pairs, alias = load_amr_truth(args.amr) if args.amr else (None, None)

    s2 = evaluate_stage2(args.runid, pathogens, args.min_reads) if pathogens is not None else None
    s3 = evaluate_stage3(args.runid, amr_pairs, alias, args.min_reads) if amr_pairs is not None else None

    truth_df = truth_summary(pathogens, amr_pairs)
    truth_df.to_csv(os.path.join(outdir, "truth_summary.csv"), index=False)
    if s2:
        s2["overall"].to_csv(os.path.join(outdir, "stage2_overall.csv"), index=False)
        s2["per_label"].to_csv(os.path.join(outdir, "stage2_per_species.csv"), index=False)
        s2["presence"].to_csv(os.path.join(outdir, "stage2_presence.csv"), index=False)
        for tool, conf in s2["confusions"].items():
            conf.to_csv(os.path.join(outdir, f"stage2_confusion_{tool}.csv"))
    if s3:
        s3["overall"].to_csv(os.path.join(outdir, "stage3_overall.csv"), index=False)
        s3["per_gene"].to_csv(os.path.join(outdir, "stage3_per_gene.csv"), index=False)
        s3["descr"].to_csv(os.path.join(outdir, "stage3_descriptive.csv"), index=False)

    meta = {"run": args.runid, "pathogen truth": args.pathogens or "-", "amr truth": args.amr or "-",
            "min_reads": args.min_reads,
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    report = os.path.join(outdir, "report.html")
    write_report(report, meta, truth_df, s2, s3)

    print_summary(s2, s3)
    print(f"\n[i]> results in {outdir}\n[i]> report: {report}")


if __name__ == "__main__":
    main()
