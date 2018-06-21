import types
from functools import singledispatch

import docopt


def add_command_name(f, name):
    f._command_name = name
    return f


@singledispatch
def command(arg):
    def wrap(f):
        def wrapped(*args, **kwargs):
            return f(*args, **kwargs)
        wrapped.__doc__ = f.__doc__
        return add_command_name(wrapped, arg)
    return wrap


@command.register(types.FunctionType)
def _(f):
    return add_command_name(f, f.__name__)


def commands(scope):
    """Return all commands in target scope (i.e. module or function)"""

    return {
        func._command_name: func
        for func in scope.values()
        if hasattr(func, '_command_name')
    }


def normalize(args, exclude):
    return {
        key.lstrip('-').lower(): value
        for key, value in args.items()
        if key not in exclude
    }


def parse(doc, argv):
    head = argv.copy()
    tail = []

    while head:
        try:
            return docopt.docopt(doc, argv=head), tail
        except docopt.DocoptExit as e:
            tail = [head.pop()] + tail

    return docopt.docopt(doc, argv=head), tail


def run(root, argv, **kwargs):
    tail = argv
    target = root
    stack = []

    while True:
        args, tail = parse(target.__doc__, stack + tail)
        res = target(**{**normalize(args, stack + ['COMMAND']), **kwargs})
        # Don't pass kwargs of root further
        # they are available through closure
        kwargs = {}

        command = args.get('COMMAND', None)

        if not command and tail:
            raise ValueError(f'Invalid arguments: {" ".join(tail)}')

        if not command and not tail:
            return res

        target = commands(res).get(command, None)

        if not target:
            raise ValueError(f'Invalid command: {command}')

        stack += [command]
