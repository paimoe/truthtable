import re
import numpy as np

__all__ = ['Parse', 'Item', 'contains', 'AND', 'OR']

a = 'p + q . r'
b = '~p + q'
c = '(a + b) . c'
d = '(a + b) . (c . d)'
e = '(a + b . (~e . f))'

def contains(needle, stack): 
    return needle in stack
def has_ph(key):
    return contains('$ph', key)
def strip_fully_surrounded(s):
    """
    ((a + b) . c) = (a + b) . c
    (a) + (b) = (a) + (b)
    """
    if not s.startswith('(') or not s.endswith(')'):
        return s
    total = s.count('(') + s.count(')')
    to_brackets = [c for c in s if c in ['(', ')']]
    i = 0
    counter = 0
    for k in to_brackets:
        counter += 1
        if k == '(':
            i += 1
        if k == ')':
            i -= 1
        #print('i', i, k, counter, total)
        if i <= 0 and counter != total:
            # Leave outermost
            return s
    #print('Converting', s, ' => ', s[1:-1])
    return s[1:-1]

def resolver(s, lookup):
    pass

class Item(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.has_ph = a.startswith('$ph') or b.startswith('$ph')
    def __repr__(self):
        return '{cls}({a},{b})'.format(cls=self.__class__.__name__, a=self.a, b=self.b)
    def label(self):
        n = self.__class__.__name__
        if n == 'AND':
            return '{a} . {b}'.format(a=self.a, b=self.b)
        elif n == 'OR':
            return '{a} + {b}'.format(a=self.a, b=self.b)
        elif n == 'NOT':
            return '~{a}'.format(a=self.a)
        else:
            return self.__repr__()

class AND(Item):
    def __init__(self, a, b):
        super().__init__(a,b)
    def update(self, **kwargs):
        #print(self.a, self.b, '5 on it')
        if str(self.a).endswith(kwargs['ph']):
            self.a = kwargs[self.a]
        elif str(self.b).endswith(kwargs['ph']):
            self.b = kwargs['ph2']
    def compute(self, kz, ph=None):
        #print('kz', type(kz), kz[self.a], kz[self.b])
        # kz: dict of key: binary value, {'q': 0, 'p': 1, 's': 0}
        #print('kz', kz)
        k1 = str(self.a)
        k2 = str(self.b)
        ph_key_match = r"(\$ph\d+)"
        if ph is not None:
            while has_ph(k2):
                # Match and replace
                for mnum, match in enumerate(re.finditer(ph_key_match, k2, re.MULTILINE)):
                    g = match.group(0)
                    newlabel = '({})'.format(ph[g].label())
                    k2 = strip_fully_surrounded(re.sub(ph_key_match, newlabel, k2))
            while has_ph(k1):
                # Match and replace
                for mnum, match in enumerate(re.finditer(ph_key_match, k1, re.MULTILINE)):
                    g = match.group(0)
                    newlabel = '({})'.format(ph[g].label())
                    k1 = strip_fully_surrounded(re.sub(ph_key_match, newlabel, k1))

        return np.logical_and(kz[k1], kz[k2])
class OR(Item):
    def __init__(self, a, b):
        super().__init__(a,b)
    def compute(self, kz, ph=None):
        k1 = str(self.a)
        k2 = str(self.b)
        ph_key_match = r"(\$ph\d+)"
        if ph is not None:
            while has_ph(k2):
                # Match and replace
                for mnum, match in enumerate(re.finditer(ph_key_match, k2, re.MULTILINE)):
                    g = match.group(0)
                    newlabel = '({})'.format(ph[g].label())
                    k2 = strip_fully_surrounded(re.sub(ph_key_match, newlabel, k2))
            while has_ph(k1):
                # Match and replace
                for mnum, match in enumerate(re.finditer(ph_key_match, k1, re.MULTILINE)):
                    g = match.group(0)
                    newlabel = '({})'.format(ph[g].label())
                    k1 = strip_fully_surrounded(re.sub(ph_key_match, newlabel, k1))
        #print('OR kz', type(kz), k1, ' + ', k2)
        #print(kz)
        # kz: dict of key: binary value, {'q': 0, 'p': 1, 's': 0}
        zb = np.logical_or(kz[k1], kz[k2])
        #print('Returning ', zb)
        return zb
class NOT(Item):
    def __init__(self, a):
        super().__init__(a.lstrip('~'), b='')
    def compute(self, kz, ph=None):
        k1 = str(self.a)
        return np.logical_not(kz[k1])

class Parse(object):

    s = None
    ph_id = 0
    ph_stack = {}
    _original = None

    def __init__(self, s):
        self.s = s
        self._original = s

    def parseholder(self, s):
        if contains('(', s) is False: 
            print('false')
            return s

        # Split string on first close brace, then backtrack
        sp = s.split(')', 1)

        init = sp[0]

        block = init.rsplit('(', 1)

        innermost = block[1]
        #print(init, block)
        remainder_left = block[0]

        self.ph_id += 1
        phkey = '$ph{}'.format(self.ph_id)
        self.ph_stack[phkey] = self.clean(innermost)

        remainder_right = sp[1]

        return remainder_left + phkey + remainder_right
        return s

    def parse(self):
        if self.s.count('(') != self.s.count(')'):
            raise Exception("Unbalanced brackets")
        #t = t.replace('}', ' } ').replace('{', ' { ').replace('=', ' = ').replace("\n", " ")

        # Run clean first to match all the simple NOTs
        self.s = self.clean(self.s)

        while contains('(', self.s):
            self.s = self.parseholder(self.s)

        self.s = self.clean(self.s)

        print('=== Parsed: {o} => {s}'.format(o=self._original, s=self.s))
        #print(self.ph_stack)

    def clean(self, s):
        """
        Like c. d = c.d
        a+    b = a+b
        """
        return self.wrap(s)

    def wrap(self, s):
        #if re.match()
        _or = r"(\w|\$ph.?)\s?\+\s?(\w|\$ph.?)"
        _and = r"(\w|\$ph.?)\s?\.\s?(\w|\$ph.?)"
        _not = r"(~\w)+"
        #print('our s', repr(s), _not, re.search(_or, s))
        # Just simple NOTs. parsed will be $ph1 + ~$ph2 which we can get later
        if re.search(_not, s):
            #print('checking not')
            m = self.match(_not, s, simple=False)
            for k in m:
                # Set placeholder?
                self.ph_id += 1
                phkey = '$ph{}'.format(self.ph_id)
                self.ph_stack[phkey] = NOT(k)
                srch = re.search(k, s).start()

                s = s[0:srch] + phkey + s[srch+len(k):]
            #print('returning s', s, self.ph_stack)
            #assert False
            return s

            # Replace the NOTs with the placeholders
        elif re.search(_or, s):
            m = self.match(_or, s)
            #assert False
            #print('checkin or', m, self.ph_stack)
            #assert False
            return OR(*m)#'OR:{},{}'.format(*m)
            #print('Match vars {s}={m}'.format(s=s, m=m))
        elif re.match(_and, s):
            #print('checkin and')
            m = self.match(_and, s)
            return AND(*m)#'AND:{},{}'.format(*m)
        return s

    def match(self, r, s, simple=True):
        g = []
        #print('s', r, s)
        for mnum, match in enumerate(re.finditer(r, s, re.MULTILINE)):
            #print('Match {mnum} on s={s} was found: {g}'.format(mnum=mnum, s=s, g=match.groups()))
            # use str for now until return an object
            if simple:
                return match.groups()
            else:
                g.append(match.group(0))
        return tuple(g)

    def components(self):
        # Return basically all the placeholders in rev order or well some order
        # tuple pair (label, object)
        # Think its being run for every row? so we'll need to cache it? oh nah can't
        _or = r"(\w|\$ph.?)\s?\+\s?(\w|\$ph.?)"
        _and = r"(\w|\$ph.?)\s?\.\s?(\w|\$ph.?)"
        r = []
        ph_key_match = r"(\$ph\d+)"
        #print('components() stack', self.ph_stack, self.s.label())
        #self.ph_stack['$ph{}'.format(len(self.ph_stack) + 1)] = self.s
        all_labels = {}
        for key, c in sorted(self.ph_stack.items(), reverse=False):
            n = type(c).__name__
            label = c.label()
            #print('=n', n, c, label)
            while True:
                if '$ph' not in label:
                    all_labels[key] = label
                    break
                else:
                    # uh do i need this or just use resolve_label
                    regex_use = _and if n == 'AND' else _or
                    matches = self.match(regex_use, label)
                    #print('matchez', matches, label)
                    for phkey in matches:
                        if phkey.startswith('$ph'):
                            old_label = label
                            #print('NNNNNN',n, n in ['AND', 'OR'])
                            if n in ['AND', 'OR']:
                                new_label = '(' + self.ph_stack[phkey].label() + ')'
                            else:
                                new_label = self.ph_stack[phkey].label()
                                print('new label', new_label)
                            label = re.sub(ph_key_match, new_label, label)
                            #print('new label match', old_label, ' => ', label)
                    
            #print('shard', key, c.label(), c)#
            r.append((label, c))

        #print('all labels', all_labels)
        # Sort based on label length
        r = sorted(r, key=lambda x: len(x[0]))
        #print('rrrrrrr', r)
        for t in r:
            label, c = t
            #print(label, ',', c, ':', c.has_ph)

        # Finally, add on overall thing
        r.append((self.resolve_label(self.s.label()), self.s))
        return r

    def resolve_label(self, s):
        # Just for like the column headers basically
        ph_key_match = r"(\$ph\d+)"
        while True:
            if '$ph' not in s:
                break
            else:
                m = self.match(ph_key_match, s, simple=False)
                for phkey in m:
                    if phkey.startswith('$ph'):
                        new_label = '(' + self.ph_stack[phkey].label() + ')'
                        s = re.sub(re.escape(phkey), new_label, s)
        return s

    def binstrappend(self, kz):
        # return all the calculated columns
        #print('Stack', self.ph_stack)
        binstr = []
        for c in self.components():
            val = c[1].compute(kz, ph=self.ph_stack)
            kz[c[0]] = val
            binstr.append(val)
        #print(binstr)
        return binstr


#Parse(c).parse()
#Parse(d).parse()
#Parse(e).parse()

#re_and = re.finditer(r"(\w'?)\s?\.\s?(~?\w\'?)", s, re.MULTILINE)