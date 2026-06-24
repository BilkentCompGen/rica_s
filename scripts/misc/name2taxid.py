 
import os
import sys

taxfile=sys.argv[1]
queryfile=sys.argv[2]



with open(taxfile, "r") as f:
    taxonomy = f.readlines()

with open(queryfile, "r") as f:
    query = f.readlines()

with open(queryfile+".taxid", "w") as f:
    for q in query:
        if q[0] == '>':
            headerinfo = q.split()
            spname = q[1] + " " + q[2]
            for t in taxonomy:
                if spname in t:
                    headerinfo.replace(spname, spname+"t.split()[0]")
            f.write(headerinfo)
        else:
            f.write(q)

