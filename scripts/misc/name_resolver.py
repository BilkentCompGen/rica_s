#! /usr/bin/python3

import pandas as pd
import os
import sys
import gzip

class NameResolver():
    def __init__(self, csv_file):
        self.df = pd.read_csv(
            csv_file,
            names=["id", "spp"],            # Force column 1 to be 'id', column 2 to be 'spp'
            header=0,                       # Skip the existing header row (Change to header=None if your file has no headers)
            dtype={"id": str, "spp": str},  # Now this will apply perfectly
            compression="gzip",
            sep=","                         # Change to "\t" if this is actually a TSV file
        )
        
    def id2spp(self, id):
        df_filtered = self.df.query(
            f'id == "{id}"', engine="python")
        if df_filtered.empty:
            return ""
        else:
            return df_filtered["spp"].iloc[0]



    # def accession2name(self, accession):
    #     # 1. Find all 'Name' values where 'Accession' matches your string
    #     matches = self.df.loc[self.df["Accession"] == accession, "Name"]
        
    #     # 2. Safely check if we actually found anything to prevent a crash
    #     if not matches.empty:
    #         return matches.iloc[0]
    #     else:
    #         return None

    # def accession2tax(self, accession):

    #     df_filtered = self.df.query(
    #         f'Accession == "{accession}"', engine="python")
    #     return df_filtered["Tax"].iloc[0]

    # def tax2accession(self, tax):

    #     df_filtered = self.df.query(f'Tax == "{tax}"', engine="python")
    #     return df_filtered["Accession"].iloc[0]

    # def tax2name(self, tax):

    #     df_filtered = self.df.query(f'Tax == "{tax}"', engine="python")
    #     return df_filtered["Name"].iloc[0]

    # def name2accession(self, name):

    #     df_filtered = self.df.query(f'Name == "{name}"', engine="python")
    #     return df_filtered["Accession"].iloc[0]

    # def name2tax(self, name):

    #     df_filtered = self.df.query(f'Name == "{name}"', engine="python")
    #     return df_filtered["Tax"].iloc[0]
