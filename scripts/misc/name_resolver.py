#! /usr/bin/python3

import pandas as pd
import os
import sys


class NameResolver():
    def __init__(self, csv_file):
        self.df = pd.read_csv(csv_file)
        
    def accession2name(self, accession):
        # 1. Find all 'Name' values where 'Accession' matches your string
        matches = self.df.loc[self.df["Accession"] == accession, "Name"]
        
        # 2. Safely check if we actually found anything to prevent a crash
        if not matches.empty:
            return matches.iloc[0]
        else:
            return None

    def accession2tax(self, accession):

        df_filtered = self.df.query(
            f'Accession == "{accession}"', engine="python")
        return df_filtered["Tax"].iloc[0]

    def tax2accession(self, tax):

        df_filtered = self.df.query(f'Tax == "{tax}"', engine="python")
        return df_filtered["Accession"].iloc[0]

    def tax2name(self, tax):

        df_filtered = self.df.query(f'Tax == "{tax}"', engine="python")
        return df_filtered["Name"].iloc[0]

    def name2accession(self, name):

        df_filtered = self.df.query(f'Name == "{name}"', engine="python")
        return df_filtered["Accession"].iloc[0]

    def name2tax(self, name):

        df_filtered = self.df.query(f'Name == "{name}"', engine="python")
        return df_filtered["Tax"].iloc[0]
