__all__ = ['export', 'receiver']

import sys

def export(**kw):
    """Mark function's local variable(s) as values for specified receivers

    Usage::
        @crosscuts.receiver
        def current_request():
            raise RuntimeError("No current request")
            
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
    function to a `crosscuts.receiver` object, such that calling the receiver
    will return the value of the linked local variable, if it's defined on the
    current call stack.  (That is, whenever the function is executing and the
    local variable is defined, its value is exported as the receiver's return
    value.)
    """
    def decorate(func):
        code = func.func_code
        _export(func, code, kw)
        return func
    return decorate







def receiver(func):
    """Define a receiving function for exported variables

    Usage::
        @crosscuts.receiver
        def current_request():
            raise RuntimeError("No current request")

    Returns a receiver function that can be used as a ``@crosscuts.export()``
    target.  Calling the receiver function will return the value of "nearest"
    matching exported local variable defined on the call stack.

    That is, when the receiver is called, lookup proceeds from the caller of
    the function that invoked it, until a matching, exported, curently-defined
    local variable is found, or until the call stack is exhausted.  If no match
    is found, the original decorated function is called, and its return value
    is returned as a default.  (That function, of course, is also free to raise
    an error instead, as in the example above.)
    """
    assert func.func_code.co_argcount==0, "Receivers can't take arguments"
    code_vars = {}
    get_var = code_vars.get
    _sentinel = object()
    def get():
        frame = sys._getframe(1)    # begin with caller's frame
        while frame:
            var = get_var(frame.f_code)
            if var:
                val = frame.f_locals.get(var, _sentinel)
                if val is not _sentinel:
                    return val
            frame = frame.f_back
        return func()

    get.__name__  = func.__name__
    get.__doc__   = func.__doc__
    get.__dict__  = func.__dict__
    get.code_vars = code_vars
    get.set = set
    return get

def _export(func, code, kw):
    names = dict.fromkeys(code.co_varnames+code.co_freevars+code.co_cellvars)
    for k, v in kw.items():
        if not hasattr(v, 'code_vars'):
            raise TypeError('Not a crosscuts.receiver', v)
        if k not in names:
            raise TypeError(
                "%s has no local variable or argument %r" % (func,k)
            )
        old = v.code_vars.setdefault(code, k)
        if old != k:
            raise TypeError(
                "%s is already exposed by %r in %s" % (v,old,func)
            )

def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        '../../README.txt',
        optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
    )
    



















