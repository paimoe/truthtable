import pandas as pd
import numpy as np
import re

from parser import *

def _notval(s): return '~{0}'.format(s)

def pgen(complete):
    _l = len(complete)
    i = 0
    term = []
    while i < _l:
        yield complete[i]

        i += 1


def classify(s):
    return s if not (s.startswith('~') or s.endswith("'")) else NOT(s)

s = '~p'
s = 'p q r'
s = 'p + s p.q s, (~p ^ q) > '
s = '(q . s) + ((p . s) + z)'
s = '(q . s) + (p . (s + q))'
# From actual question
s = '(p . (q + r)) + (z . x)'
"""

LIMITATIONS:
- only 2 variables in each thing , so no a + b + c
- no nested yet
- pull out bracket parsing into its own lib cause its useful (also for eu4 parser)
- can't handle NOTs
- NOT entire expressions ~(a + b) => NOT($ph2) $ph2: OR(a,b)
"""

p = Parse(s)
p.parse()

# Get all alphabet chars in string, set() uniqueifys it
keys = sorted(set(''.join(ch for ch in s if ch.isalpha())))
numvars = len(keys)

# Split string into components
# start with just space separators
# then also to k-maps
allvars = []
components = []
components += p.components()
#components += collect_ors + collect_ands
for item in pgen(s):
    allvars.append(item)

# Add column labels
allcolumns = list(keys) + [c[0] for c in components]
df = pd.DataFrame(columns=allcolumns)

for k in keys:
    df[k].astype(int)

# max rows really
maxrow = 2 ** numvars
for i in range(maxrow):
    #print('i',i)
    binstr = [ bool(int(s)) for s in list(bin(i)[2:].zfill(numvars)) ]


    kz = dict(zip(keys,binstr))
    #print('kz', kz)

    # Loop all things
    binstr += p.binstrappend(kz)
    #for c in components:
    #    binstr += [c[1].compute(kz, p)]

    df.loc[i] = binstr

print(p.ph_stack)

# As bool
#print(df.head(16))
print(df.astype(int).head(32))