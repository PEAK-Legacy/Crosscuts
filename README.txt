===============================================
Invisible Parameter Passing using ``Crosscuts``
===============================================

Have you ever found yourself needing to refactor massive amounts of code just
to make sure that one stupid parameter got passed all the way down from the
place it was defined, to another place where it was needed, even though none
of the functions in between needed to use it?  Or have you found yourself
gritting your teeth and giving in to the urge to use a global or thread-local
variable because the alternatives were just too painful, or because some of
the code involved was part of another package?

The ``peak.util.crosscuts`` module provides a simple alternative, often found
in other dynamic languages and AOP toolkits: dynamically-scoped variables.  In
essence, they're a way to pass an "invisible parameter" through the call stack,
without actually changing any functions or adding any call-time overhead.  A
simple (and slightly stupid) example::

    >>> from peak.util import crosscuts

Here, we define a receiver function to obtain the current Request object::
    
    >>> @crosscuts.receiver
    ... def current_request():
    ...     raise RuntimeError("No current request")

Next, we mark the `request` local variable in this function as containing the
``current_request`` value for this function and its callees:
    
    >>> @crosscuts.export(request=current_request)
    ... def wsgi_app(environ, start_response=None):
    ...     request = Request(environ)
    ...     for cb in callbacks: cb()   # look ma, no parameters

And make a zero-argument callback that uses the receiver function to get
the current request::
    
    >>> def some_callback():
    ...     print current_request()

Now, by default, the receiver function runs its original, default body if
there's no current value on the call stack::
    
    >>> some_callback()
    Traceback (most recent call last):
      ...
    RuntimeError: No current request

But, once everything's set up and we actually run the exporting function,
the receiver returns the nearest active value on the call stack::

    >>> callbacks = [some_callback]

    >>> class Request:
    ...     def __init__(self, environ): self.environ = environ
    ...     def __repr__(self): return 'Request(%r)' % (self.environ,)

    >>> wsgi_app({'x':'y'})
    Request({'x': 'y'})
    
    >>> wsgi_app({1:2})
    Request({1: 2})

But then things go back to normal once there are no running exporters::
    
    >>> some_callback()
    Traceback (most recent call last):
      ...
    RuntimeError: No current request


Multiple receivers and exporters can be in use at the same time, and the
call stack is searched upward until a matching exporter is found for the called
receiver::

    >>> @crosscuts.receiver
    ... def database():
    ...     raise RuntimeError("No database")

    >>> @crosscuts.export(db=database)
    ... def using_db(db, func, *args, **kw):
    ...     return func(*args, **kw)

    >>> def another_callback():
    ...     print "Current database:", database()

    >>> another_callback()
    Traceback (most recent call last):
      ...
    RuntimeError: No database
    
    >>> callbacks.append(another_callback)

    >>> using_db(123, wsgi_app, {4:5})
    Request({4: 5})
    Current database: 123

Notice, by the way, that if you're writing a framework that needs to pass its
objects (requests, connections, whatever) around, your clients' code need not
know about the crosscuts module: users can just import your receiver functions,
and call them as they would any comparable API.  Your code can simply export
local variables from selected functions, instead of mucking around with global
variables.

For more on the features, limitations, API details, and other cool stuff,
please consult the complete `Crosscuts developer's guide`_.  Questions,
comments, and bug reports for this package should be directed to the
`PEAK mailing list`_.

.. _Crosscuts developer's guide: http://peak.telecommunity.com/DevCenter/Crosscuts#toc
.. _PEAK mailing list: http://www.eby-sarna.com/mailman/listinfo/peak/

.. _toc:

.. contents:: **Table of Contents**


-----------------
Developer's Guide
-----------------


API Reference
=============


``@crosscuts.receiver``
-----------------------

Define a receiving function for exported variables.  Example usage::

    >>> @crosscuts.receiver
    ... def current_request():
    ...     raise RuntimeError("No current request")

Returns a receiver function that can be used as a ``@crosscuts.export()``
target.  Calling the receiver function will return the value of "nearest"
matching exported local variable defined on the call stack.

That is, when the receiver is called, lookup proceeds from the caller of
the function that invoked it, until a matching, exported, curently-defined
local variable is found, or until the call stack is exhausted.  If no match
is found, the original decorated function is called, and its return value
is returned as a default.  (That function, of course, is also free to raise
an error instead, as in the example above.)

Note, by the way, that a receiver's default function must take exactly zero
arguments::

    >>> @crosscuts.receiver
    ... def dummy(a):
    ...     pass
    Traceback (most recent call last):
      ...
    AssertionError: Receivers can't take arguments


``@crosscuts.export(**kw)``
---------------------------

Mark a function's local variable(s) as providing values for the corresponding
receivers.  Example usage::

    @crosscuts.export(request=current_request)
    def wsgi_app(environ, start_response):
        request = Request(environ)
        # From here on (unless you 'del request' or the function is exited)
        # any functions called from this frame will receive the value of
        # `request` when they call `current_request()`.  However,
        # `current_request()` will still return its old value if it's
        # called *directly* from this function, regardless of the contents
        # of `request`.  (i.e., the new value is ONLY exported to callees.)
            
Each keyword argument links an argument or local variable name in the
function to a ``crosscuts.receiver`` object, such that calling the receiver
will return the value of the linked local variable, if it's defined on the
current call stack.  (That is, whenever the function is executing and the
local variable is defined, its value is exported as the receiver's return
value.)

Multiple variables can be exported in a single ``export()`` call, but they
must all be referenced in the function's definition, and you cannot link two
different names to the same receiver, even across multiple calls::

    >>> @crosscuts.export(something=current_request)
    ... def dummy():
    ...     pass
    Traceback (most recent call last):
      ...
    TypeError: <function dummy...> has no local variable or argument 'something'

    >>> @crosscuts.export(x=current_request, y=current_request)
    ... def dummy(x, y):
    ...     pass
    Traceback (most recent call last):
      ...
    TypeError: <...current_request...> is already exposed by 'y' in <...dummy...>

    >>> @crosscuts.export(x=current_request)
    ... @crosscuts.export(y=current_request)
    ... def dummy(x, y):
    ...     pass
    Traceback (most recent call last):
      ...
    TypeError: <...current_request...> is already exposed by 'y' in <...dummy...>

You can, however, export the same name to two different receivers, if you
use multiple export calls::

    >>> @crosscuts.export(x=current_request)
    ... @crosscuts.export(x=database)
    ... def dummy(x):
    ...     def nested():
    ...         print current_request(), database()
    ...     nested()

    >>> dummy(42)
    42 42

But of course, they have to be receivers defined with ``@crosscuts.receiver``!
::

    >>> @crosscuts.export(x=dummy)
    ... def dummy2(x):
    ...     pass
    Traceback (most recent call last):
      ...
    TypeError: ('Not a crosscuts.receiver', <function dummy...>)


Performance Considerations
==========================

Note that calling a receiver function can be resource intensive if there is
a long stack distance between the receiver's caller, and the nearest exporter
of that variable.  If you notice a performance issue in a tight loop, you may
wish to re-export a variable closer to where it's actually used, to cut down
on the lookup distance, or in an extreme case, add and pass explicit parameters
to the functions involved.

(For new code, though, it's generally going to be better to use crosscuts than
to duplicate parameters through multiple calling levels that don't actually use
or touch them, at least until you're sure there's a performance hit.)



-------------------
Internals and Tests
-------------------

Verify that unbound exported variables are skipped during traversal::

    >>> @crosscuts.export(request=current_request, db=database)
    ... def wsgi_app(environ, start_response=None):
    ...     request = Request(environ)
    ...     for cb in callbacks: cb()   # look ma, no parameters
    ...     db = None   # it's a variable, but not bound at callback time

    >>> using_db(123, wsgi_app, {4:5})
    Request({4: 5})
    Current database: 123

    >>> wsgi_app({1:2})
    Traceback (most recent call last):
      ...
    RuntimeError: No database

Verify that nested scope variables are also usable::

    >>> def outer(x):
    ...     @crosscuts.export(x=database)
    ...     @crosscuts.export(x=current_request)
    ...     def inner():
    ...         x
    ...         for cb in callbacks: cb()
    ...     return inner

    >>> outer(23)()
    23
    Current database: 23

