import pandas as pd
import numpy as np
import math
import re
import argparse
from tabulate import tabulate
import crayons
from parser import *

def _notval(s): return '~{0}'.format(s)

def pgen(complete):
    _l = len(complete)
    i = 0
    term = []
    while i < _l:
        yield complete[i]

        i += 1
"""
LIMITATIONS:
- only 2 variables in each thing , so no a + b + c
- no nested yet
- pull out bracket parsing into its own lib cause its useful (also for eu4 parser)
- can't handle NOTs
- NOT entire expressions ~(a + b) => NOT($ph2) $ph2: OR(a,b)
"""

def main(s, opts):
    p = Parse(s)
    p.parse()

    # Get all alphabet chars in string, set() uniqueifys it
    keys = sorted(set(''.join(ch for ch in s if ch.isalpha())))
    numvars = len(keys)

    # Split string into components
    # start with just space separators
    # then also to k-maps
    kdata = {}
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

        as_bin = list(bin(i)[2:].zfill(numvars))
        binstr = [ bool(int(s)) for s in list(bin(i)[2:].zfill(numvars)) ]


        kz = dict(zip(keys,binstr))
        #print('kz', kz)

        # Loop all things
        rowdata = p.binstrappend(kz)

        binstr += rowdata
        #for c in components:
        #    binstr += [c[1].compute(kz, p)]

        # compile k-map yes or no
        kdata[i] = rowdata[-1]

        df.loc[i] = binstr

    print('=' * min(50, len(p._original)*2))
    print('Parsed: {o} => {s}'.format(o=p._original, s=p.s))
    print(p.ph_stack)
    print('=' * min(50, len(p._original)*2))

    if opts.fmt.startswith('b'):
        data = df
    elif opts.fmt == 'tf':
        data = df
    else:
        data = df.astype(int)

    data = data.head(opts.limit)
    print(tabulate(data, headers=allcolumns, tablefmt=opts.tablefmt))

    if opts.kmap:
        kmap(kdata, list(keys))

def kmap(data, keys):
    numvars = len(keys)
    maxrow = len(data)

    if numvars != 4:
        print('ERROR: k-map only supports 4 values')
        return

    sqt = int(math.sqrt(maxrow))
    
    if sqt % 2 != 0:
        raise Exception("Need a square number of values")

    npkm = np.array(range(0, 2**numvars)).reshape(sqt, sqt)
    km = pd.DataFrame(npkm)

    #print(km)
    # Then min-sop
    def cellcheck(c):
        return '' if data[c] == False else 1

    # Switch rows and cols (only for 4-var but whatever)
    km[[2,3]] = km[[3,2]]
    b, c = km.iloc[2].copy(), km.iloc[3]
    km.iloc[2] = c
    km.iloc[3] = b

    km = km.applymap(cellcheck)

    t = tabulate(km)

    # Make my own table cause tabulate won't work great
    # Just do 4-var for now
    """
    Slack brute force template instead of generating it    
    """
    kmap_template = """
               {v[2]}  
   +---+---+---+---+
   | {0} | {1} | {2} | {3} |
   +---+---+---+---+
   | {4} | {5} | {6} | {7} |
   +---+---+---+---+ {v[1]}
   | {8} | {9} | {10} | {11} |
 {v[0]} +---+---+---+---+
   | {12} | {13} | {14} | {15} |
   +---+---+---+---+
           {v[3]}
"""
    colors = ['red', 'blue', 'green', 'yellow']
    flatten = [' ' if x == '' else x for x in list(np.array(km).flat)]
    vs = tuple([ getattr(crayons, colors[i])(k.upper()) for i,k in enumerate(keys) ])
    print(kmap_template.format(*flatten, v=vs))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Truth Table', prog='tt')
    parser.add_argument('--fmt', default='int', nargs='?', help='int (default), [b]ool, tf (T or F)')
    parser.add_argument('--limit', default=32, help='Number of rows (default 32)')
    parser.add_argument('--tablefmt', default='pipe', help='Tabulate table format (default: pipe)')
    parser.add_argument('--quiet', '-q', action='count', default=0)
    parser.add_argument('--kmap', '-k', action='store_true', default=False, help='Also show k-map')
    parser.add_argument('s', help='String to parse')
   
    opts = parser.parse_args()

    main(opts.s, opts)