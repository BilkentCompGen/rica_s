#! /usr/bin/python3

import pandas as pd
import os
import sys


def accession2name(accession):
    global df
    df_filtered = df.query(f'Accession == "{accession}"', engine="python")
    return df_filtered["Name"].iloc[0]


def accession2tax(accession):
    global df
    df_filtered = df.query(f'Accession == "{accession}"', engine="python")
    return df_filtered["Tax"].iloc[0]


def tax2accession(tax):
    global df
    df_filtered = df.query(f'Tax == "{tax}"', engine="python")
    return df_filtered["Accession"].iloc[0]


def tax2name(tax):
    global df
    df_filtered = df.query(f'Tax == "{tax}"', engine="python")
    return df_filtered["Name"].iloc[0]


def name2accession(name):
    global df
    df_filtered = df.query(f'Name == "{name}"', engine="python")
    return df_filtered["Accession"].iloc[0]


def name2tax(name):
    global df
    df_filtered = df.query(f'Name == "{name}"', engine="python")
    return df_filtered["Tax"].iloc[0]


def load_data(filepath):
    global df
    df = pd.read_csv(filepath)
    return df


def how():
    usage = '''Usage: name_resolver <operation> <data>

    Available Operations:
    t2n  : Taxonomy ID -> Species Name
    t2a  : Taxonomy ID -> Accession ID
    a2t  : Accession ID -> Taxonomy ID
    a2n  : Accession ID -> Species Name
    n2t  : Species Name -> Taxonomy ID
    n2a  : Species Name -> Accession ID

    Examples:
    name_resolver t2n 562
    name_resolver a2t NZ_CP065993.1
    name_resolver n2a "Escherichia coli"'''
    return usage


global csv_file
csv_file = "/opt/rica_s/scripts/misc/spp.csv"
global df


if __name__ == "__main__":
    r = how()

    if len(sys.argv) == 3:
        op = sys.argv[1]
        data = sys.argv[2]
        print(f"loading data {csv_file}...")
        global df
        df = load_data(csv_file)
        print("ready...")
        match op:
            case "t2n":
                r = tax2name(data)
            case "t2a":
                r = tax2accession(data)
            case "a2t":
                r = accession2tax(data)
            case "a2n":
                r = accession2name(data)
            case "n2t":
                r = name2tax(data)
            case "n2a":
                r = name2accession(data)
            case _:
                print("error")
    
    print(r)
 # endif
