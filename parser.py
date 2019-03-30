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
        else:
            return self.__repr__()

class AND(Item):
    def __init__(self, a, b):
        super().__init__(a,b)
    def update(self, **kwargs):
        print(self.a, self.b, '5 on it')
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
        if ph is not None:
            if k2.startswith('$ph'):
                # Check ph stack, then use
                k2 = ph[k2].label()
            if k1.startswith('$ph'):
                k1 = ph[k1].label()

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
        #print('kz', type(kz), kz[self.x], kz[self.y])
        # kz: dict of key: binary value, {'q': 0, 'p': 1, 's': 0}
        return np.logical_or(kz[k1], kz[k2])

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

        while contains('(', self.s):
            self.s = self.parseholder(self.s)

        self.s = self.clean(self.s)

        print('Parsed: {o} => {s}'.format(o=self._original, s=self.s))
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
        if re.match(_or, s):
            m = self.match(_or, s)
            return OR(*m)#'OR:{},{}'.format(*m)
            #print('Match vars {s}={m}'.format(s=s, m=m))
        elif re.match(_and, s):
            m = self.match(_and, s)
            return AND(*m)#'AND:{},{}'.format(*m)
        return s

    def match(self, r, s):
        for mnum, match in enumerate(re.finditer(r, s, re.MULTILINE)):
            #print('Match {mnum} was found: {g}'.format(mnum=mnum, g=match.groups()))
            # use str for now until return an object
            return match.groups()

    def components(self):
        # Return basically all the placeholders in rev order or well some order
        # tuple pair (label, object)
        _or = r"(\w|\$ph.?)\s?\+\s?(\w|\$ph.?)"
        _and = r"(\w|\$ph.?)\s?\.\s?(\w|\$ph.?)"
        r = []
        ph_key_match = r"(\$ph.+)"
        #print('stack', self.ph_stack)
        for key, c in sorted(self.ph_stack.items(), reverse=True):
            n = type(c).__name__
            label = c.label()
            while True:
                if '$ph' not in label:
                    break
                else:
                    # Get it out bro
                    matches = self.match(_and, label)
                    #print('matchez', matches)
                    for phkey in matches:
                        if phkey.startswith('$ph'):
                            label = re.sub(ph_key_match, '(' + self.ph_stack[phkey].label() + ')', label)
                            #print('match', matches, label)
                    if n == 'AND':
                        # Also update object with new value? do earlier better
                        pass
                        #c.update(ph='ph2', ph2=self.ph_stack[phkey])
                        #print('AND', c.compute({'q': True, 'p':True, '$ph2': True}))
                    elif n == 'OR':
                        pass
            #print('shard', key, c.label(), c)#
            r.append((label, c))

        # Sort based on label length
        r = sorted(r, key=lambda x: len(x[0]))
        #print('rrrrrrr', r)
        for t in r:
            label, c = t
            #print(label, ',', c, ':', c.has_ph)

        # Finally, add on overall thing
        # Fix label on this
        r.append((self.s.label(), self.s))
        return r

    def resolve_label(self, k, kz=None):
        pass

    def binstrappend(self, kz):
        # return all the calculated columns
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