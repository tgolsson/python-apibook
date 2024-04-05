import ast

from .data import (
    Arg,
    Class,
    ClassField,
    FromImport,
    Method,
    Module,
    NakedImport,
    TypeAlias,
    Variable,
)


class AstVisitor(ast.NodeVisitor):
    def __init__(self, module):
        self._module = module

        self._docstring = None
        self._classes = []
        self._functions = []
        self._imports = []
        self._aliases = []
        self._variables = []
        self._all_exports = []

    def visit_Assign(self, node):
        # we look for __all__ = [...] assignments to determine what is exported
        if len(node.targets) == 1 and node.targets[0].id == "__all__":
            self._all_exports = [n.s for n in node.value.elts]

        else:
            self._variables.append(Variable(ast.unparse(node.targets[0]), ast.unparse(node.value)))

    def visit_AnnAssign(self, node):
        visitor = TypeAliasVisitor()
        visitor.visit(node)
        self._aliases.append(visitor.finish())

    def visit_Import(self, node):
        self._imports.append(NakedImport(node.names[0].name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self._imports.append(FromImport(node.module, [n.name for n in node.names], relative=node.level))
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        visitor = AstClassVisitor(self._imports)
        visitor.visit(node)
        self._classes.append(visitor.finish())

    def visit_FunctionDef(self, node):
        visitor = AstFunctionVisitor(self._imports)
        visitor.visit(node)
        self._functions.append(visitor.finish())

    def visit_Module(self, node):
        self._docstring = ast.get_docstring(node)
        self.generic_visit(node)

    def finish(self):
        return Module(
            self._module,
            self._docstring,
            self._classes,
            self._functions,
            self._variables,
            self._aliases,
            self._all_exports,
            self._imports,
        )


class AstClassVisitor(ast.NodeVisitor):
    """Visitor for class declarations."""

    def __init__(self, imports):
        self._imports = imports
        self._name = None
        self._bases = []
        self._methods = []
        self._docstring = None
        self._decorators = []
        self._fields = []

    def visit_ClassDef(self, node):
        self._name = node.name
        bases = []
        for base in node.bases:
            bases.append(ast.unparse(base))
        self._bases = bases

        self._docstring = ast.get_docstring(node)

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        visitor = ClassFieldVisitor()
        visitor.visit(node)
        self._fields.append(visitor.finish())

    def visit_Decorator(self, node):
        self._decorators.append(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        visitor = AstFunctionVisitor(self._imports)
        visitor.visit(node)
        self._methods.append(visitor.finish())

    def finish(self):
        return Class(self._name, self._bases, self._methods, self._fields, self._docstring)


class ArgsVisitor(ast.NodeVisitor):
    def __init__(self):
        self._name = None
        self._type = None
        self._default = None

    def visit_arg(self, node):
        self._name = node.arg

        if node.annotation:
            self.visit_(node.annotation)

    def visit_(self, node):
        self._type = ast.unparse(node)

    def finish(self, default):
        if default:
            if isinstance(default, ast.Constant):
                self._default = default.value

            elif isinstance(default, ast.Tuple):
                self._default = ", ".join(str(d.value) for d in default.elts)

        return Arg(self._name, self._type, self._default)


class ClassFieldVisitor(ast.NodeVisitor):
    def __init__(self):
        self._name = None
        self._type = None
        self._default = None

    def visit_AnnAssign(self, node):
        self._name = node.target.id
        self._type = str(ast.unparse(node.annotation))

        if node.value:
            self._default = node.value

    def finish(self):
        return ClassField(self._name, self._type, self._default)


class TypeAliasVisitor(ast.NodeVisitor):
    def __init__(self):
        self._name = None
        self._type = None

    def visit_AnnAssign(self, node):
        self._name = node.target.id
        self._type = str(ast.unparse(node.value))

    def finish(self):
        return TypeAlias(self._name, self._type)


class AstFunctionVisitor(ast.NodeVisitor):
    def __init__(self, imports: list):
        self._imports = imports

        self._name = None
        self._args = []
        self._returns = None
        self._docstring = None
        self._kwonlyargs = None

    def visit_FunctionDef(self, node):
        self._name = node.name

        defaults = node.args.defaults

        seen_self = 0
        default_start_idx = len(node.args.args) - len(defaults)
        for idx, arg in enumerate(node.args.args):
            default = None
            if idx >= default_start_idx:
                default = defaults.pop(0)

            visitor = ArgsVisitor()
            visitor.visit(arg)

            if visitor._name == "self" and idx == 0:
                seen_self += 1
            self._args.append(visitor.finish(default))

        kwonlydefaults = node.args.kw_defaults
        kwonlyargs = []

        if node.name == "deprecated":
            print(ast.dump(node.returns, indent=4))
        for idx, (arg, default) in enumerate(zip(node.args.kwonlyargs, kwonlydefaults)):
            visitor = ArgsVisitor()
            visitor.visit(arg)
            if default is not None:
                match default:
                    case ast.Constant(value, _):
                        default = value
                    case ast.Name(id, _):
                        default = id
                    case ast.Attribute(_, _, _):
                        default = ast.unparse(default)
                    case ast.Lambda(_, _):
                        default = "<lambda ...>"

                    case _:
                        raise ValueError(
                            f"Unknown default value in function {self._name!r} for arg"
                            f" {ast.dump(arg)!r} {default=}"
                        )

            kwonlyargs.append(visitor.finish(default))

        match node.returns:
            case ast.Name(id, _):
                self._returns = id
            case ast.Subscript(_, _, _):
                self._returns = ast.unparse(node.returns)
            case ast.Attribute(_, _, _):
                self._returns = ast.unparse(node.returns)
            case ast.Constant(value):
                self._returns = value
            case None | ast.Constant(value=None):
                self._returns = None
            case ast.BinOp(_, _, _):
                self._returns = ast.unparse(node.returns)

            case ast.Tuple(_):
                self._returns = ast.unparse(node.returns)
            case _:
                raise ValueError(f"Unknown return value {ast.dump(node.returns)=}")

        self._docstring = ast.get_docstring(node)
        self._kwonlyargs = kwonlyargs

    def finish(self):
        return Method(self._name, self._args, self._kwonlyargs, self._returns, self._docstring)
