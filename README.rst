Elementwise - Lazy operation proxies for iterables
==================================================

Elementwise provides convenient, fully lazy, abstract programming behavior for
interacting with iterable objects.  All attempts at attribute access on
OperationProxy objects return generator factories wrapped in OperationProxy
objects.  This means that you can generatively build up complex operation chains
and apply these chains of operations repeatedly, to different source iterables.
Additionally, each OperationProxy object has a reference to its parent
OperationProxy, allowing you to traverse up the function tree, undoing
operations or modying previous processes.

Elementwise provides three proxy objects:

1.) ElementwiseProxy
    This broadcasts all operations performed on the proxy to every member of the
    proxied iterable.

2.) PairwiseProxy
    This treats the arguments of all operations performed as iterables which
    emit the correct argument value for the operation on the element from the
    proxied iterable with the same index.  For example::
        
        >>> PairwiseProxy([1, 2, 3, 4]) + [1, 2, 3, 4]
        PairwiseProxy([2, 4, 6, 8])

3.) RecursiveElementwiseProxy
    This behaves like ElementwiseProxy, with the notable exception that
    when a member value is a non string iterable, it will recursively try to
    apply the operation to child nodes.  This proxy is capable of arbitrary
    graph traversal in a depth first fashion, and will not visit a node twice.

Each of the proxy objects can mutate into any of the other types by calling a
mutator method.

* ElementwiseProxyMixin.each
    mutates the current proxy into an ElementwiseProxy.
    
* PairwiseProxyMixin.each
    mutates the current proxy into a PairwiseProxy.
    
* RecursiveElementwiseProxyMixin.recurse
    mutates the current proxy into a RecursiveElementwiseProxy.
    
When you would like to perform the operation chain represented by your proxy,
simply iterate over it. The easiest way to do this is probably to call list with
the proxy as the argument.

If you would like to perform the same operation chain on another iterable,
all OperationProxy subclasses support OperationProxy.replicate
which takes an iterable and generates a new chain, which is a duplicate of the
current chain with that iterable as the base data source.

If for some reason you would like to undo an operation, all OperationProxy
subclasses support OperationProxy.undo, which accepts an integer number
of operations that should be undone (defaulting to 1) and returns a reference to
the OperationProxy representing that step in the chain.
    
Note::
    
    There are some exceptions to the broadcasting behavior that can not be
    circumvented.  This includes most methods uesd by builtin types that were
    formerly functions, such as __str__ and __nonzero__. When you need to
    broadcast these operations, use ElementwiseProxy.apply. 