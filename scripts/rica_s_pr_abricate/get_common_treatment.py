#! python

import sys
import sqlite3
import os
import pandas as pd
import re


conn = sqlite3.connect('rica_s.db')

p1=sys.argv[1]
print(p1)

p1= re.sub('[^a-zA-Z0-9]+', r'%', p1)
# p1="%"+p1+"%"
# p1 = "%E%coli%"
# p2 = "%ESCHERICHIA%coli%"



print(p1)
print("=====")
# Let Pandas handle the heavy lifting
# Let the library handle the variables, nice and clean


df = pd.read_sql_query("SELECT distinct t.canonical_name, t.treatment FROM pathogen p, treatment t WHERE p.name LIKE ? AND p.canonical_name = t.canonical_name;", conn, params=(p1,))
print(df)
print("=====")
conn.close()
