"""
Elementwise provides a conveniece proxy object on an iterable which transforms
operator behavior, function and methods into vectorized versions which operate
on all members of the iterable.
"""
from decorator import decorator
import collections
import inspect
import itertools
import operator
import types

__author__ = 'Nathan Rice <nathan.alexander.rice@gmail.com>'


# Provides additional late binding support
_iterable = lambda x: object.__getattribute__(x, "iterable")

def _cacheable(proxy):
    try:
        return object.__getattribute__(proxy, "__cacheable__")
    except AttributeError:
        return False

def create_cell(obj):
        return (lambda: obj).func_closure[0]

def copy_func(f, code=None, globals_=None, name=None, argdefs=None, closure=None):
    return types.FunctionType(
        code or f.func_code,
        globals_ or f.func_globals,
        name or f.func_name,
        argdefs or f.func_defaults,
        closure or f.func_closure
    )

def graphmap(f, graph):
        """
        Depth first graph traversal and function application.
        """
        visited = set()
        def traverse_branch(branch):
            for node in branch:
                if id(node) in visited:
                    continue
                if isinstance(node, (collections.Sequence, collections.Set)) and \
                   not isinstance(node, basestring):
                    # We are at a branch
                    visited.add(id(node))
                    yield traverse_branch(node)
                else:
                    # We are at a leaf
                    yield f(node)
        for n in traverse_branch(graph):
            yield n

class IteratorProxy(object):
    """
    """

    def __init__(self, iterable, cacheable=False):
        self._cache = []
        self.cacheable = cacheable
        self.iterable = iterable

    def __iter__(self):
        if not self.cache:
            if isinstance(self.iterable, types.FunctionType):
                iterable = self.iterable()
            else:
                iterable = self.iterable
            for item in iterable:
                yield item
                self.cache.append(item)
        else:
            if isinstance(self.cache, types.FunctionType):
                iterable = self.cache()
            else:
                iterable = self.cache
            for item in iterable:
                yield item

    @property
    def cache(self):
        if not self.cacheable:
            return self.iterable
        else:
            return self._cache

    def __getitem__(self, key):
        """
        Respect the getitem attribute on the parent if it exists
        """
        iterable_getitem = getattr(self.iterable, "__getitem__", None)
        if iterable_getitem:
            return iterable_getitem(key)
        elif isinstance(key, types.SliceType):
            return itertools.islice(self, key.start, key.stop, key.step)
        else:
            return itertools.islice(self, key, key + 1)

    def __add__(self, other):
        return itertools.chain(self, other)

    def __mul__(self, other):
        if isinstance(other, int):
            return itertools.product(self, repeat=other)
        else:
            return itertools.product(self, other)


@decorator
def chainable(f, self, *args, **kwargs):
    """Chainable functions return OperationProxy objects."""
    return type(self)(f(self, *args, **kwargs), self)


@decorator
def cacheable(f, self, *args, **kwargs):
    """
    Cacheable functions have their return iterable wrapped in an
    IterableProxy.  If `self`.__cacheable__ evaluates to True, the
    IterableProxy will cache results as it is iterated over.
    """
    iteratable = f(self, *args, **kwargs)
    return IteratorProxy(iteratable, _cacheable(self))


class ProxyMixin(object):
    """Base class for Proxy Mixins"""


class ElementwiseProxyMixin(ProxyMixin):
    """
    Provides iterable objects with a proxy that broadcasts operations to
    member elements.
    """

    @property
    def each(self):
        """Syntactic sugar for ElementwiseProxy(self)"""
        return ElementwiseProxy(self)


class RecursiveProxyMixin(ProxyMixin):
    """
    Provides iterable objects with a proxy that broadcasts operations recursively
    to member elements.
    """

    @property
    def recurse(self):
        """Syntactic sugar for RecursiveElementwiseProxy(self)"""
        return RecursiveElementwiseProxy(self)


class PairwiseProxyMixin(ProxyMixin):
    """
    Provides iterable objects with a proxy that performs pairwise operations
    using elements of supplied iterables.
    """

    @property
    def pair(self):
        """Syntactic sugar for PairwiseProxy(self)"""
        return RecursiveElementwiseProxy(self)


class OperationProxy(object):
    """
    Base class for Proxy objects.
    """

    def __init__(self, iterable=tuple(), parent=None):
        self.iterable = iterable
        self.parent = parent

    def replicate(self, iterable):
        """
        Creates a copy of this operation chain, applied to `iterable`.
        """
        def ancestors():
            current = self
            while current is not None:
                yield current
                current = object.__getattribute__(current, "parent")
        ancestor_list = list(ancestors())
        parent = type(ancestor_list[-1])(iterable)
        for ancestor in reversed(ancestor_list[:-1]):
            # Every ancester after the first will have an IteratorProxy that
            # wraps a function.
            iterable = object.__getattribute__(ancestor, "iterable").iterable
            # The only thing we need to do is get the "self" name in the closure
            # to point to the new OperationProxy.
            new_closure = (create_cell(parent),) + iterable.func_closure[1:]
            new_iterable = copy_func(iterable, closure=new_closure)
            iterator_proxy = IteratorProxy(new_iterable, _cacheable(self))
            # Here we build up the chain.
            new_ancestor = type(ancestor)(iterator_proxy, parent)
            parent = new_ancestor
        # Now return parent, which is a copy of this, with references to copies
        # of all chain members.
        return parent

    def undo(self, steps=1):
        """
        Starting from the current operation, undo the previous `steps`
        operations in the chain.
        
        :parameter steps:
            The number of operations to undo.
        
        :type steps:
            int
            
        :returns:
            A new chain reprenseting the state of the chain `steps` operations
            prior.
            
        :rtype:
            `OperationProxy` (or a subclass thereof)
        """
        current = self
        for step in range(steps):
            parent = object.__getattribute__(current, "parent")
            if parent:
                current = parent
            else:
                break
        return current

    def __getattribute__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            iterable = IteratorProxy(_iterable(self), _cacheable(self))
            return type(self)((e.__getattribute__(item) for e in iterable), self)

    def __iter__(self):
        return iter(_iterable(self))

    def __nonzero__(self):
        return bool(_iterable(self))

    def __str__(self):
        return ", ".join(str(e) for e in _iterable(self))

    def __repr__(self):
        return ", ".join(repr(e) for e in _iterable(self))

    def __unicode__(self):
        return u", ".join(unicode(e) for e in _iterable(self))

    @chainable
    def __reversed__(self):
        return lambda: reversed(_iterable(self))

    @chainable
    def __getitem__(self, item):
        return lambda: _iterable(self)[item]

    @chainable
    @cacheable
    def __hash__(self):
        return lambda: (hash(e) for e in _iterable(self))

    @chainable
    @cacheable
    def __invert__(self):
        return lambda: (~e for e in _iterable(self))

    @chainable
    @cacheable
    def __index__(self):
        return lambda: (operator.index(e) for e in _iterable(self))

    @chainable
    @cacheable
    def __neg__(self):
        return lambda: (-e for e in _iterable(self))

    @chainable
    @cacheable
    def __pos__(self):
        return lambda: (+e for e in _iterable(self))

    @chainable
    @cacheable
    def __abs__(self):
        return lambda: (e.__abs__() for e in _iterable(self))


class ElementwiseProxy(OperationProxy):
    """
    Provides elementwise operator behavior, attribute access and method calls
    over a parent iterable.
    
    .. testsetup::
    
       nums = ElementwiseProxy([1, 2, 3, 4])
       
    First, create an ElementwiseProxy from any iterable, like so::
    
        nums = ElementwiseProxy([1, 2, 3, 4])
        
    Now you can perform a large vareity of operations on the proxy, and it will
    create a chain of operations to be applied to the contents of the iterable
    being proxied.  The proxy is fully lazy, so none of the operations will be
    applied until you begin to request values from the proxy by iterating over
    it.
    
    For example:
    
    >>> print nums.bit_length()
    1, 2, 2, 3
    
    >>> nums + 1
    2, 3, 4, 5
    
    >>> print nums * 2
    2, 4, 6, 8
    
    >>> print nums == 2
    False, True, False, False
    
    >>> print ((nums + 1) * 2 + 3).apply(float)
    7.0, 9.0, 11.0, 13.0
    
    >>> print (nums.apply(float) + 0.0001).apply(round, 2)
    1.0, 2.0, 3.0, 4.0
    
    >>> print abs(nums - 3)
    2, 1, 0, 1
    
    >>> print (nums * 2 + 3) / 4
    >>> list(efoo2.undo(3))
    1, 2, 3, 4
    
    >>> print ((nums * 2 + 3) / 4).replicate([2, 2, 3, 3])
    1, 1, 2, 2
   
    >>> words = ElementwiseProxy(["one", "two", "three", "four"])
    >>> print (words + " little indians").upper().split(" ").apply(reversed).apply("_".join) * 2
    'INDIANS_LITTLE_ONEINDIANS_LITTLE_ONE', 'INDIANS_LITTLE_TWOINDIANS_LITTLE_TWO', 'INDIANS_LITTLE_THREEINDIANS_LITTLE_THREE', 'INDIANS_LITTLE_FOURINDIANS_LITTLE_FOUR'
    """

    @chainable
    @cacheable
    def apply(self, func, *args, **kwargs):
        """
        :parameter func:
            The function to be applied.
            
        :returns:
            A function which returns (func(e, *args, **kwargs) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (func(e, *args, **kwargs) for e in _iterable(self))

    @chainable
    @cacheable
    def __call__(self, *args, **kwargs):
        """            
        :returns:
            A function which returns (e(*args, **kwargs) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e(*args, **kwargs) for e in _iterable(self))

    @chainable
    @cacheable
    def __add__(self, other):
        """            
        :returns:
            A function which returns (e + other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e + other for e in _iterable(self))

    @chainable
    @cacheable
    def __sub__(self, other):
        """            
        :returns:
            A function which returns (e - other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e - other for e in _iterable(self))

    @chainable
    @cacheable
    def __mul__(self, other):
        """            
        :returns:
            A function which returns (e * other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e * other for e in _iterable(self))

    @chainable
    @cacheable
    def __floordiv__(self, other):
        """            
        :returns:
            A function which returns (e // other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e // other for e in _iterable(self))

    @chainable
    @cacheable
    def __mod__(self, other):
        """            
        :returns:
            A function which returns (e % other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e % other for e in _iterable(self))

    @chainable
    @cacheable
    def __divmod__(self, other):
        """            
        :returns:
            A function which returns (divmod(e, other) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (divmod(e, other) for e in _iterable(self))

    @chainable
    @cacheable
    def __pow__(self, other, modulo=None):
        """            
        :returns:
            A function which returns (pow(e, other, modulo) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (pow(e, other, modulo) for e in _iterable(self))

    @chainable
    @cacheable
    def __lshift__(self, other):
        """            
        :returns:
            A function which returns (e << other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e << other for e in _iterable(self))

    @chainable
    @cacheable
    def __rshift__(self, other):
        """            
        :returns:
            A function which returns (e >> other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e >> other for e in _iterable(self))

    @chainable
    @cacheable
    def __div__(self, other):
        """            
        :returns:
            A function which returns (e / other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e / other for e in _iterable(self))

    @chainable
    @cacheable
    def __truediv__(self, other):
        """            
        :returns:
            A function which returns (e / other for e in self), using truediv.
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e.__truediv__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __radd__(self, other):
        """            
        :returns:
            A function which returns (other + e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other + e for e in _iterable(self))

    @chainable
    @cacheable
    def __rand__(self, other):
        """            
        :returns:
            A function which returns (other & e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other & e for e in _iterable(self))

    @chainable
    @cacheable
    def __rdiv__(self, other):
        """            
        :returns:
            A function which returns (other / e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other / e for e in _iterable(self))

    @chainable
    @cacheable
    def __rdivmod__(self, other):
        """            
        :returns:
            A function which returns (divmod(other, e) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (divmod(other, e) for e in _iterable(self))

    @chainable
    @cacheable
    def __rfloordiv__(self, other):
        """            
        :returns:
            A function which returns (other // e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other // e for e in _iterable(self))

    @chainable
    @cacheable
    def __rlshift__(self, other):
        """            
        :returns:
            A function which returns (other << e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other << e for e in _iterable(self))

    @chainable
    @cacheable
    def __rmod__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e % other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other % e for e in _iterable(self))

    @chainable
    @cacheable
    def __rmul__(self, other):
        """            
        :returns:
            A function which returns (other * e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other * e for e in _iterable(self))

    @chainable
    @cacheable
    def __ror__(self, other):
        """            
        :returns:
            A function which returns (other | e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other | e for e in _iterable(self))

    @chainable
    @cacheable
    def __rpow__(self, other):
        """            
        :returns:
            A function which returns::
            
                (pow(other, e) for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (pow(other, e) for e in _iterable(self))

    @chainable
    @cacheable
    def __rrshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other >> e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other >> e for e in _iterable(self))

    @chainable
    @cacheable
    def __rsub__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other - e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other - e for e in _iterable(self))

    @chainable
    @cacheable
    def __rtruediv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other / e for e in self)
                
            using truediv.
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e.__rtruediv__(other) for e in _iterable(self))

    @chainable
    @cacheable

    def __rxor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other ^ e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (other ^ e for e in _iterable(self))

    @chainable
    @cacheable
    def __contains__(self, item):
        """            
        :returns:
            A function which returns::
            
                (item in e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (item in e for e in _iterable(self))

    @chainable
    @cacheable
    def __eq__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e == other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e == other for e in _iterable(self))

    @chainable
    @cacheable
    def __ne__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e != other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e != other for e in _iterable(self))

    @chainable
    @cacheable
    def __le__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e <= other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e <= other for e in _iterable(self))

    @chainable
    @cacheable
    def __lt__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e < other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e < other for e in _iterable(self))

    @chainable
    @cacheable
    def __gt__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e > other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e > other for e in _iterable(self))

    @chainable
    @cacheable
    def __ge__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e >= other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e >= other for e in _iterable(self))

    @chainable
    @cacheable
    def __cmp__(self, other):
        """            
        :returns:
            A function which returns::
            
                (cmp(e, other) for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (cmp(e, other) for e in _iterable(self))

    @chainable
    @cacheable
    def __and__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e & other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e & other for e in _iterable(self))

    @chainable
    @cacheable
    def __xor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e ^ other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e ^ other for e in _iterable(self))

    @chainable
    @cacheable
    def __or__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e | other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: (e | other for e in _iterable(self))

    @chainable
    @cacheable
    def __iand__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e &= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__iand__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __ixor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e =^ other for e in self)
            
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__ixor__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __ior__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e |= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__ior__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __iadd__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e |= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__iadd__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __isub__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e -= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__isub__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __imul__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e *= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__imul__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __idiv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e /= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__idiv__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __itruediv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e |= other for e in self)
                
            using truediv.
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__itruediv__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __ifloordiv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e //= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__ifloordiv__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __imod__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e %= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__imod__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __ipow__(self, other, modulo=None):
        """            
        :returns:
            A function which returns::
            
                (e **= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__ipow__(other, modulo) for e in _iterable(self))

    @chainable
    @cacheable
    def __ilshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e <<= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__ilshift__(other) for e in _iterable(self))

    @chainable
    @cacheable
    def __irshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e >>= other for e in self)
                        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: (e.__irshift__(other) for e in _iterable(self))


class RecursiveElementwiseProxy(ElementwiseProxy):
    """
    """

    def __str__(self):
        return ", ".join(str(e) for e in _iterable(self))

    def __repr__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join(repr(e) for e in _iterable(self))
        )

    def __unicode__(self):
        return u", ".join(unicode(e) for e in _iterable(self))


    @chainable
    @cacheable
    def apply(self, f, *args, **kwargs):
        """
        Depth first graph traversal and function application.
        """
        return lambda: graphmap(lambda e: f(e, *args, **kwargs), self.iterable)

    @chainable
    @cacheable
    def __call__(self, *args, **kwargs):
        """            
        :returns:
            A function which returns (e(*args, **kwargs) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e(*args, **kwargs), self.iterable)

    @chainable
    @cacheable
    def __add__(self, other):
        """            
        :returns:
            A function which returns (e + other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e + other, self.iterable)

    @chainable
    @cacheable
    def __sub__(self, other):
        """            
        :returns:
            A function which returns (e - other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e - other, self.iterable)

    @chainable
    @cacheable
    def __mul__(self, other):
        """            
        :returns:
            A function which returns (e * other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e * other, self.iterable)

    @chainable
    @cacheable
    def __floordiv__(self, other):
        """            
        :returns:
            A function which returns (e // other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e // other, self.iterable)

    @chainable
    @cacheable
    def __mod__(self, other):
        """            
        :returns:
            A function which returns (e % other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e % other, self.iterable)

    @chainable
    @cacheable
    def __divmod__(self, other):
        """            
        :returns:
            A function which returns (divmod(e, other) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: divmod(e, other), self.iterable)

    @chainable
    @cacheable
    def __pow__(self, other, modulo=None):
        """            
        :returns:
            A function which returns (pow(e, other, modulo) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: pow(e, other, modulo), self.iterable)

    @chainable
    @cacheable
    def __lshift__(self, other):
        """            
        :returns:
            A function which returns (e << other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e << other, self.iterable)

    @chainable
    @cacheable
    def __rshift__(self, other):
        """            
        :returns:
            A function which returns (e >> other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e >> other, self.iterable)

    @chainable
    @cacheable
    def __div__(self, other):
        """            
        :returns:
            A function which returns (e / other for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e / other, self.iterable)

    @chainable
    @cacheable
    def __truediv__(self, other):
        """            
        :returns:
            A function which returns (e / other for e in self), using truediv.
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e.__truediv__(other), self.iterable)

    @chainable
    @cacheable
    def __radd__(self, other):
        """            
        :returns:
            A function which returns (other + e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other + e, self.iterable)

    @chainable
    @cacheable
    def __rand__(self, other):
        """            
        :returns:
            A function which returns (other & e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other & e, self.iterable)

    @chainable
    @cacheable
    def __rdiv__(self, other):
        """            
        :returns:
            A function which returns (other / e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other / e, self.iterable)

    @chainable
    @cacheable
    def __rdivmod__(self, other):
        """            
        :returns:
            A function which returns (divmod(other, e) for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: divmod(other, e), self.iterable)

    @chainable
    @cacheable
    def __rfloordiv__(self, other):
        """            
        :returns:
            A function which returns (other // e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other // e, self.iterable)

    @chainable
    @cacheable
    def __rlshift__(self, other):
        """            
        :returns:
            A function which returns (other << e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other << e, self.iterable)

    @chainable
    @cacheable
    def __rmod__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e % other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other % e, self.iterable)

    @chainable
    @cacheable
    def __rmul__(self, other):
        """            
        :returns:
            A function which returns (other * e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other * e, self.iterable)

    @chainable
    @cacheable
    def __ror__(self, other):
        """            
        :returns:
            A function which returns (other | e for e in self).
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e | other, self.iterable)

    @chainable
    @cacheable
    def __rpow__(self, other):
        """            
        :returns:
            A function which returns::
            
                (pow(other, e) for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: pow(other, e), self.iterable)

    @chainable
    @cacheable
    def __rrshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other >> e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other >> e, self.iterable)

    @chainable
    @cacheable
    def __rsub__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other - e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: other - e, self.iterable)

    @chainable
    @cacheable
    def __rtruediv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other / e for e in self)
                
            using truediv.
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e.__rtruediv__(other), self.iterable)

    @chainable
    @cacheable

    def __rxor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (other ^ e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e ^ other, self.iterable)

    @chainable
    @cacheable
    def __contains__(self, item):
        """            
        :returns:
            A function which returns::
            
                (item in e for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: item in e, self.iterable)

    @chainable
    @cacheable
    def __eq__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e == other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e == other, self.iterable)

    @chainable
    @cacheable
    def __ne__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e != other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e != other, self.iterable)

    @chainable
    @cacheable
    def __le__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e <= other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e <= other, self.iterable)

    @chainable
    @cacheable
    def __lt__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e < other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e < other, self.iterable)

    @chainable
    @cacheable
    def __gt__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e > other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e > other, self.iterable)

    @chainable
    @cacheable
    def __ge__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e >= other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e >= other, self.iterable)

    @chainable
    @cacheable
    def __cmp__(self, other):
        """            
        :returns:
            A function which returns::
            
                (cmp(e, other) for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: cmp(e, other), self.iterable)

    @chainable
    @cacheable
    def __and__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e & other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e & other, self.iterable)

    @chainable
    @cacheable
    def __xor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e ^ other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e ^ other, self.iterable)

    @chainable
    @cacheable
    def __or__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e | other for e in self)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        return lambda: graphmap(lambda e: e | other, self.iterable)

    @chainable
    @cacheable
    def __iand__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e &= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__iand__(other), self.iterable)

    @chainable
    @cacheable
    def __ixor__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e =^ other for e in self)
            
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__ixor__(other), self.iterable)

    @chainable
    @cacheable
    def __ior__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e |= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__ior__(other), self.iterable)

    @chainable
    @cacheable
    def __iadd__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e += other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__iadd__(other), self.iterable)

    @chainable
    @cacheable
    def __isub__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e -= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__isub__(other), self.iterable)

    @chainable
    @cacheable
    def __imul__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e *= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__imul__(other), self.iterable)

    @chainable
    @cacheable
    def __idiv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e /= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__idiv__(other), self.iterable)

    @chainable
    @cacheable
    def __itruediv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e |= other for e in self)
                
            using truediv.
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__itruediv__(other), self.iterable)

    @chainable
    @cacheable
    def __ifloordiv__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e //= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__ifloordiv__(other), self.iterable)

    @chainable
    @cacheable
    def __imod__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e %= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__imod__(other), self.iterable)

    @chainable
    @cacheable
    def __ipow__(self, other, modulo=None):
        """            
        :returns:
            A function which returns::
            
                (e **= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__ipow__(other, modulo), self.iterable)

    @chainable
    @cacheable
    def __ilshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e <<= other for e in self)
                
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__ilshift__(other), self.iterable)

    @chainable
    @cacheable
    def __irshift__(self, other):
        """            
        :returns:
            A function which returns::
            
                (e >>= other for e in self)
                        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        return lambda: graphmap(lambda e: e.__irshift__(other), self.iterable)


class PairwiseProxy(OperationProxy):
    """
    Provides pairwise operator behavior, attribute access and method calls
    over a parent iterable.
    
    .. testsetup::
    
       nums = PairProxy([1, 2, 3, 4])
       
    First, create an PairProxy from any iterable, like so::
    
        nums = PairProxy([1, 2, 3, 4])
        
    Now you can perform a large vareity of operations on the proxy, and it will
    create a chain of operations to be applied to the contents of the iterable
    being proxied.  The proxy is completely lazy, so none of the operations will be
    applied until you begin to request values from the proxy by iterating over
    it.
    
    For example:
    
    >>> print nums + [1, 2, 3, 4]
    2, 4, 6, 8
    
    >>> print print nums * [2, 2, 3, 3]
    2, 4, 9, 12
    
    >>> print nums == [2, 2, 3, 5]
    False, True, True, False
    
    >>> print ((nums + 1) * 2 + 3).apply(float)
    7.0, 9.0, 11.0, 13.0
    
    >>> print (nums.apply(float) + 0.0001).apply(round, 2)
    1.0, 2.0, 3.0, 4.0
    
    >>> print abs(nums - 3)
    2, 1, 0, 1
    
    >>> print (nums * 2 + 3) / 4
    >>> list(efoo2.undo(3))
    1, 2, 3, 4
    
    >>> print ((nums * 2 + 3) / 4).replicate([2, 2, 3, 3])
    1, 1, 2, 2
    
    """

    @chainable
    @cacheable
    def apply(self, func, *args, **kwargs):
        """
        :parameter func:
            The function to be applied.
        
        :parameter args:
            The positional arguments for each element of the PairwiseProxy
        
        :type args:
            Sequence
        
        :parameter kwargs:
            The keyword arguments for each element of the PairwiseProxy
        
        :type kwargs:
            Sequence
        
        :returns:
            A function which returns::
            
            imap(func, self, args, kwargs)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y, z: func(x, *y, **z), iterable, args, kwargs)

    @chainable
    @cacheable
    def __call__(self, *args, **kwargs):
        """
        :parameter args:
            The positional arguments for each element of the PairwiseProxy
        
        :type args:
            Sequence
        
        :parameter kwargs:
            The keyword arguments for each element of the PairwiseProxy
        
        :type kwargs:
            Sequence
        
        :returns:
            A function which returns::
            
            imap(self, self, args, kwargs)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y, z: x(*y, **z), iterable, args, kwargs)

    @chainable
    @cacheable
    def __add__(self, other):
        """            
        :returns:
            A function which returns::
            
                imap(lambda x, y: x + y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x + y, iterable, other)

    @chainable
    @cacheable
    def __sub__(self, other):
        """ 
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
                   
        :returns:
            A function which returns::
            
                imap(lambda x, y: x - y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x - y, iterable, other)

    @chainable
    @cacheable
    def __mul__(self, other):
        """
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
                        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x * y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x * y, iterable, other)

    @chainable
    @cacheable
    def __floordiv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
        
            A function which returns::
            
                imap(lambda x, y: x // y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x // y, iterable, other)

    @chainable
    @cacheable
    def __mod__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x % y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x % y, iterable, other)

    @chainable
    @cacheable
    def __divmod__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x % y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(divmod, iterable, other)

    @chainable
    @cacheable
    def __pow__(self, other, modulo=None):
        """            
        :parameter others:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x + y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: pow(x, y, modulo), iterable, other)

    @chainable
    @cacheable
    def __lshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x << y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x << y, iterable, other)

    @chainable
    @cacheable
    def __rshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x >> y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x >> y, iterable, other)

    @chainable
    @cacheable
    def __div__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x / y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x / y, iterable, other)

    @chainable
    @cacheable
    def __truediv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x / y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__truediv__(y), iterable, other)

    @chainable
    @cacheable
    def __radd__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y + x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y + x, iterable, other)

    @chainable
    @cacheable
    def __rand__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y & x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y & x, iterable, other)

    @chainable
    @cacheable
    def __rdiv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y / x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y / x, iterable, other)

    @chainable
    @cacheable
    def __rdivmod__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: divmod(y, x), self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: divmod(y, x), iterable, other)

    @chainable
    @cacheable
    def __rfloordiv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y // x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y // x, iterable, other)

    @chainable
    @cacheable
    def __rlshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y << x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y << x, iterable, other)

    @chainable
    @cacheable
    def __rmod__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y % x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y % x, iterable, other)

    @chainable
    @cacheable
    def __rmul__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y * x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y * x, iterable, other)

    @chainable
    @cacheable
    def __ror__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y | x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y | x, iterable, other)

    @chainable
    @cacheable
    def __rpow__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y ** x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y ** x, iterable, other)

    @chainable
    @cacheable
    def __rrshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y >> x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y >> x, iterable, other)

    @chainable
    @cacheable
    def __rsub__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y - x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y - x, iterable, other)

    @chainable
    @cacheable
    def __rtruediv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y / x, self, other)
                
            using truediv.
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__rtruediv__(y), iterable, other)

    @chainable
    @cacheable
    def __rxor__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y ^ x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y ^ x, iterable, other)

    @chainable
    @cacheable
    def __contains__(self, item):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y in x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: y in x, iterable, item)

    @chainable
    @cacheable
    def __eq__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x == y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x == y, iterable, other)

    @chainable
    @cacheable
    def __ne__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x != y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x != y, iterable, other)

    @chainable
    @cacheable
    def __le__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x <= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x <= y, iterable, other)

    @chainable
    @cacheable
    def __lt__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x < y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x < y, iterable, other)

    @chainable
    @cacheable
    def __gt__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x > y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x > y, iterable, other)

    @chainable
    @cacheable
    def __ge__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: y / x, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x >= y, iterable, other)

    @chainable
    @cacheable
    def __cmp__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(cmp, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__cmp__(y), iterable, other)

    @chainable
    @cacheable
    def __and__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x & y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x & y, iterable, other)

    @chainable
    @cacheable
    def __xor__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x ^ y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x ^ y, iterable, other)

    @chainable
    @cacheable
    def __or__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x | y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x | y, iterable, other)

    @chainable
    @cacheable
    def __iand__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x &= y, self, other)
                
        .. warning:: This operations can not be undone once finalized.
        
        :rtype:
            FunctionType -> GeneratorType
        
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__iand__(y), iterable, other)

    @chainable
    @cacheable
    def __ixor__(self, other):
        """            
        :returns:
            A function which returns::
            
                imap(lambda x, y: x ^= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__ixor__(y), iterable, other)

    @chainable
    @cacheable
    def __ior__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x |= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__ior__(y), iterable, other)

    @chainable
    @cacheable
    def __iadd__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x += y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__iadd__(y), iterable, other)

    @chainable
    @cacheable
    def __isub__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x -= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__isub__(y), iterable, other)

    @chainable
    @cacheable
    def __imul__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x *= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__imul__(y), iterable, other)

    @chainable
    @cacheable
    def __idiv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x /= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__idiv__(y), iterable, other)

    @chainable
    @cacheable
    def __itruediv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x /= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__itrue__(y), iterable, other)

    @chainable
    @cacheable
    def __ifloordiv__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x // y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__ifloordiv__(y), iterable, other)

    @chainable
    @cacheable
    def __imod__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x % y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
        
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__imod__(y), iterable, other)

    @chainable
    @cacheable
    def __ipow__(self, other, modulo=None):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: pow(x, y, modulo), self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y, z: x.__ipow__(y, modulo), iterable, other)

    @chainable
    @cacheable
    def __ilshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x <<= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__ilshift__(y), iterable, other)

    @chainable
    @cacheable
    def __irshift__(self, other):
        """            
        :parameter other:
            The other object to use for each element of the PairwiseProxy
        
        :type others:
            Sequence
        
        :returns:
            A function which returns::
            
                imap(lambda x, y: x >>= y, self, other)
        
        :rtype:
            FunctionType -> GeneratorType
            
        .. warning:: This operations can not be undone once finalized.
        """
        iterable = object.__getattribute__(self, "iterable")
        return lambda: itertools.imap(lambda x, y: x.__irshift__(y), iterable, other)


if __name__ == "__main__":
    nums = PairwiseProxy([1, 2, 3, 4])
    print (nums.apply(itertools.repeat(float)) + itertools.repeat(0.0001)).apply(itertools.repeat(round), itertools.repeat(2))
    print abs(nums - [3, 2, 1, 1])
    print (nums * [2, 2, 1, 5] + [3, 5, 9, 0]) / [4, 1, 2, 3]
    print ((nums * itertools.repeat(2) + itertools.repeat(3)) / itertools.repeat(4)).replicate([2, 2, 3, 3])
    print ((nums * [2, 3, 4, 5]) > [5, 6, 7, 8]) != [True, True, False, True]
    treenums = RecursiveElementwiseProxy([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    print treenums * 2

