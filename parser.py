import re
import numpy as np

__all__ = ['Parse', 'Item', 'contains', 'AND', 'OR', 'strip_fully_surrounded']

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
    def compute_key(self, k, lookup):
        ph_key_match = r"(\$ph\d+)"
        while has_ph(k):
            # Match and replace
            for mnum, match in enumerate(re.finditer(ph_key_match, k, re.MULTILINE)):
                #print('Match {mnum} on s={s} was found: {g}'.format(mnum=mnum, s=k, g=match.groups()))
                g = match.group(0)
                newlabel = '({})'.format(lookup[g].label())
                if type(lookup[g]).__name__ == 'NOT':
                    newlabel = strip_fully_surrounded(newlabel)
                k = strip_fully_surrounded(re.sub(re.escape(g), newlabel, k))
        return k

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
        if ph is not None:
            k1 = self.compute_key(k1, ph)
            k2 = self.compute_key(k2, ph)
        return np.logical_and(kz[k1], kz[k2])
class OR(Item):
    def __init__(self, a, b):
        super().__init__(a,b)
    compute_fn = np.logical_or # maybe use this, quicker
    def compute(self, kz, ph=None):
        k1 = str(self.a)
        k2 = str(self.b)
        if ph is not None:
            k1 = self.compute_key(k1, ph)
            k2 = self.compute_key(k2, ph)
        #print('OR kz', type(kz), k1, ' + ', k2)
        #print(kz)
        # kz: dict of key: binary value, {'q': 0, 'p': 1, 's': 0}
        return np.logical_or(kz[k1], kz[k2])
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

        # Run clean first to match all the simple NOTs
        if contains('~', self.s):
            self.s = self.clean(self.s)

        while contains('(', self.s):
            self.s = self.parseholder(self.s)

        self.s = self.clean(self.s)

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
            return s

            # Replace the NOTs with the placeholders
        elif re.search(_or, s):
            m = self.match(_or, s)
            return OR(*m)
        elif re.match(_and, s):
            #print('checkin and')
            m = self.match(_and, s)
            return AND(*m)
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
            #print('=n', type(c).__name__, c, label)
            label = self.resolve_label(c.label())

            all_labels[key] = label

            r.append((label, c))

        # Sort based on label length
        r = sorted(r, key=lambda x: len(x[0]))

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
                        other_key = self.ph_stack[phkey]
                        if type(other_key).__name__ in ['AND', 'OR']:
                            new_label = '(' + other_key.label() + ')'
                        else:
                            new_label = other_key.label()
                        s = re.sub(re.escape(phkey), new_label, s)
        return s

    def binstrappend(self, kz):
        # return all the calculated columns
        binstr = []
        for c in self.components():
            val = c[1].compute(kz, ph=self.ph_stack)
            kz[c[0]] = val
            binstr.append(val)
        return binstr

