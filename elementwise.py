"""
Elementwise provides a conveniece proxy object on an iterable which transforms
operator behavior, function and methods into vectorized versions which operate
on all members of the iterable.
"""

__author__ = 'Nathan Rice <nathan.alexander.rice@gmail.com>'

import operator
import itertools
import types

class ElementwiseProxyMixin(object):
    """
    Provides iterable objects with a proxy that broadcasts operations to
    member elements.
    """

    @property
    def each(self):
        return ElementwiseProxy(self)


class ElementwiseProxy(object):
    """
    Provides elementwise operator behavior, attribute access and method calls
    over a parent iterable.
    """

    def __init__(self, iterable, ancestor=None):
        self.iterable = iterable
        if ancestor is not None:
            self.ancestor = ancestor
        else:
            self.ancestor = self

    @property
    def iterable(self):
        iterable = object.__getattribute__(self, "_iterable")
        if isinstance(iterable, types.GeneratorType):
            # Should probably look into a better way to do this
            return itertools.tee(iterable, 1)[0]
        else:
            return iterable

    @iterable.setter
    def iterable(self, iterable):
        self._iterable = iterable

    # Go ahead and shadow apply in this name space, it's deprecated.
    def apply(self, func, *args, **kwargs):
        return ElementwiseProxy((func(e, *args, **kwargs) for e in object.__getattribute__(self, "iterable")), self)

    def __getattribute__(self, item):
        if item in {"apply"}:
            return object.__getattribute__(self, item)
        else:
            return ElementwiseProxy((
                e.__getattribute__(item) for e in object.__getattribute__(self, "iterable")), self)

    def __call__(self, *args, **kwargs):
        return ElementwiseProxy((e(*args, **kwargs) for e in object.__getattribute__(self,
            "iterable")), self)

    def __iter__(self):
        return iter(object.__getattribute__(self, "iterable"))

    def __nonzero__(self):
        return bool(object.__getattribute__(self, "iterable"))

    def __str__(self):
        return ", ".join(e.__str__() for e in object.__getattribute__(self, "iterable"))

    def __repr__(self):
        return ", ".join(e.__repr__() for e in object.__getattribute__(self, "iterable"))

    def __unicode__(self):
        return object.__unicode__(str(self))

    def __index__(self):
        return ElementwiseProxy((operator.index(e) for e in object.__getattribute__(self, "iterable")), self)

    def __reversed__(self):
        return ElementwiseProxy((reversed(e) for e in object.__getattribute__(self, "iterable")), self)

    def __getitem__(self, item):
        return ElementwiseProxy((e.__getitem__(item) for e in object.__getattribute__(self, "iterable")), self)

    def __setitem__(self, key, value):
        return ElementwiseProxy((e.__setitem__(key, value) for e in object.__getattribute__(self,
            "iterable")), self)

    def __delitem__(self, key):
        return ElementwiseProxy((e.__delitem__(key) for e in object.__getattribute__(self, "iterable")), self)

    def __neg__(self):
        return ElementwiseProxy((-e for e in object.__getattribute__(self, "iterable")), self)

    def __pos__(self):
        return ElementwiseProxy((+e for e in object.__getattribute__(self, "iterable")), self)

    def __abs__(self):
        return ElementwiseProxy((e.__abs__() for e in object.__getattribute__(self, "iterable")), self)

    def __invert__(self):
        return ElementwiseProxy((~e for e in object.__getattribute__(self, "iterable")), self)

    def __add__(self, other):
        return ElementwiseProxy((
            e + other for e in object.__getattribute__(self, "iterable")), self)

    def __sub__(self, other):
        return ElementwiseProxy((e - other for e in object.__getattribute__(self, "iterable")), self)

    def __mul__(self, other):
        return ElementwiseProxy((e * other for e in object.__getattribute__(self, "iterable")), self)

    def __floordiv__(self, other):
        return ElementwiseProxy((e // other for e in object.__getattribute__(self, "iterable")), self)

    def __mod__(self, other):
        return ElementwiseProxy((e % other for e in object.__getattribute__(self, "iterable")), self)

    def __divmod__(self, other):
        return ElementwiseProxy((divmod(e, other) for e in object.__getattribute__(self, "iterable")), self)

    def __pow__(self, other, modulo=None):
        return ElementwiseProxy((pow(e, modulo) for e in object.__getattribute__(self, "iterable")), self)

    def __lshift__(self, other):
        return ElementwiseProxy((e << other for e in object.__getattribute__(self, "iterable")), self)

    def __rshift__(self, other):
        return ElementwiseProxy((e >> other for e in object.__getattribute__(self, "iterable")), self)

    def __div__(self, other):
        return ElementwiseProxy((e / other for e in object.__getattribute__(self, "iterable")), self)

    def __truediv__(self, other):
        return ElementwiseProxy((e.__truediv__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __radd__(self, other):
        return ElementwiseProxy((
            other + e for e in object.__getattribute__(self, "iterable")), self)

    def __rand__(self, other):
        return ElementwiseProxy((
            other & e for e in object.__getattribute__(self, "iterable")), self)

    def __rdiv__(self, other):
        return ElementwiseProxy((
            other / e for e in object.__getattribute__(self, "iterable")), self)

    def __rdivmod__(self, other):
        return ElementwiseProxy((
            divmod(other, e) for e in object.__getattribute__(self, "iterable")), self)

    def __rfloordiv__(self, other):
        return ElementwiseProxy((
            other // e for e in object.__getattribute__(self, "iterable")), self)

    def __rlshift__(self, other):
        return ElementwiseProxy((
            other << e for e in object.__getattribute__(self, "iterable")), self)

    def __rmod__(self, other):
        return ElementwiseProxy((
            other % e for e in object.__getattribute__(self, "iterable")), self)

    def __rmul__(self, other):
        return ElementwiseProxy((
            other * e for e in object.__getattribute__(self, "iterable")), self)

    def __ror__(self, other):
        return ElementwiseProxy((
            other | e for e in object.__getattribute__(self, "iterable")), self)

    def __rpow__(self, other):
        return ElementwiseProxy((
            pow(other, e) for e in object.__getattribute__(self, "iterable")), self)

    def __rrshift__(self, other):
        return ElementwiseProxy((
            other >> e for e in object.__getattribute__(self, "iterable")), self)

    def __rsub__(self, other):
        return ElementwiseProxy((
            other - e for e in object.__getattribute__(self, "iterable")), self)

    def __rtruediv__(self, other):
        return ElementwiseProxy((
            e.__rtruediv__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __rxor__(self, other):
        return ElementwiseProxy((
            other ^ e for e in object.__getattribute__(self, "iterable")), self)

    def __contains__(self, item):
        return ElementwiseProxy((item in e for e in object.__getattribute__(self, "iterable")), self)

    def __hash__(self):
        return ElementwiseProxy((hash(e) for e in object.__getattribute__(self, "iterable")), self)

    def __eq__(self, other):
        return ElementwiseProxy((e == other for e in object.__getattribute__(self, "iterable")), self)

    def __ne__(self, other):
        return ElementwiseProxy((e != other for e in object.__getattribute__(self, "iterable")), self)

    def __le__(self, other):
        return ElementwiseProxy((e <= other for e in object.__getattribute__(self, "iterable")), self)

    def __lt__(self, other):
        return ElementwiseProxy((e < other for e in object.__getattribute__(self, "iterable")), self)

    def __gt__(self, other):
        return ElementwiseProxy((e > other for e in object.__getattribute__(self, "iterable")), self)

    def __ge__(self, other):
        return ElementwiseProxy((e >= other for e in object.__getattribute__(self, "iterable")), self)

    def __cmp__(self, other):
        return ElementwiseProxy((e.__cmp__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __and__(self, other):
        return ElementwiseProxy((e & other for e in object.__getattribute__(self, "iterable")), self)

    def __xor__(self, other):
        return ElementwiseProxy((e ^ other for e in object.__getattribute__(self, "iterable")), self)

    def __or__(self, other):
        return ElementwiseProxy((e | other for e in object.__getattribute__(self, "iterable")), self)

    def __iand__(self, other):
        return ElementwiseProxy((e.__iand__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __ixor__(self, other):
        return ElementwiseProxy((e.__ixor__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __ior__(self, other):
        return ElementwiseProxy((e.__ior__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __iadd__(self, other):
        return ElementwiseProxy((e.__iadd__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __isub__(self, other):
        return ElementwiseProxy((e.__isub__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __imul__(self, other):
        return ElementwiseProxy((e.__imul__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __idiv__(self, other):
        return ElementwiseProxy((e.__idiv__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __itruediv__(self, other):
        return ElementwiseProxy((e.__itruediv__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __ifloordiv__(self, other):
        return ElementwiseProxy((e.__ifloordiv__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __imod__(self, other):
        return ElementwiseProxy((e.__imod__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __ipow__(self, other, modulo=None):
        return ElementwiseProxy((e.__ipow__(other, modulo) for e in object.__getattribute__(self,
            "iterable")), self)

    def __ilshift__(self, other):
        return ElementwiseProxy((e.__ilshift__(other) for e in object.__getattribute__(self, "iterable")), self)

    def __irshift__(self, other):
        return ElementwiseProxy((e.__irshift__(other) for e in object.__getattribute__(self, "iterable")), self)


if __name__ == "__main__":
    class ExampleList(ElementwiseProxyMixin, list):
        def __new__(cls, iterable):
            return list.__new__(cls, iterable)
    # You can also get a foo via ElementwiseProxy(iterable)
    foo = ExampleList([1, 2, 3, 4])
    efoo = foo.each
    assert list(efoo.bit_length()) == [1, 2, 2, 3]
    print "bit length: ", list(efoo.bit_length())
    assert list(efoo + 1) == [2, 3, 4, 5]
    print "with addition of 1: ", list(efoo + 1)
    assert list(efoo * 2) == [2, 4, 6, 8]
    print "with multiplication by 2: ", list(efoo * 2)
    assert list(efoo == 2) == [False, True, False, False]
    print "testing equality: ", efoo == 2
    assert list((efoo + 1) * 2 + 3) == [7, 9, 11, 13]
    print "chaining addition and multiplication: ", ((efoo + 1) * 2 + 3).apply(float)
    print "some function calls are supported, like abs() for instance: ", abs(efoo)
    assert list((efoo.apply(float) + 0.0001).apply(round, 2)) == [1.0, 2.0, 3.0, 4.0]
