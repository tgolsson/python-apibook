"""Generates markdown from Python docstrings."""

import argparse
import ast
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import docstring_parser
from rich.console import Console
from rich.logging import RichHandler

console = Console()


FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

logger = logging.getLogger(__name__)

_VISIBLE_FUNCTIONS = ["__init__", "__call__"]


@dataclass
class Signature:
    args: list
    returns: list
    docstring: str


def _parse_method_docstring(docs: str) -> Signature:
    """Parse a method docstring, just like this one.

    Args:
       docs: the docstring to parse

    Returns:
        a Signature object
    """

    doc = docstring_parser.parse(docs.replace("\\", "\\\\"))

    args = {}
    returns = []

    for param in doc.params:
        if "(" in param.arg_name or "." in param.arg_name:
            args[param.type_name] = param.description
        else:
            args[param.arg_name] = param.description

    if doc.returns:
        returns.append(doc.returns.description)

    docstring_frags = []

    if doc.short_description:
        docstring_frags.append(doc.short_description)

    if doc.long_description:
        docstring_frags.append(doc.long_description)

    return Signature(args, returns, "\n".join(docstring_frags))


@dataclass
class Args:
    """Class to hold command line arguments."""

    root_dir: str
    output_dir: str
    summary_template_file: str | None = None

    def parse() -> "Args":
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description="Generate markdown from Python docstrings.")
        parser.add_argument("root_dir", help="Root directory to search for Python files.")
        parser.add_argument("output_dir", help="Output directory for markdown files.")
        parser.add_argument(
            "--summary-template-file",
            help="Path to a file containing a summary template.",
            default=None,
        )
        args = parser.parse_args()
        return Args(args.root_dir, args.output_dir, args.summary_template_file)


@dataclass
class Class:
    """Class to hold class information."""

    name: str
    bases: list
    methods: list
    fields: list
    docstring: str

    @property
    def _visible_methods(self):
        return [m for m in self.methods if not m.name.startswith("_") or m.name in _VISIBLE_FUNCTIONS]

    @property
    def _visible_fields(self):
        return [f for f in self.fields if not f.name.startswith("_")]

    def to_md(self):
        """Convert class to markdown."""
        if self.name.startswith("_"):
            return ""

        bases = ""
        if self.bases:
            bases = f"({', '.join(self.bases)})"

        md = f"### `class {self.name}{bases}:`\n\n"
        md += '<div style="padding-left: 20px;">\n\n'
        if self.docstring:
            signature = _parse_method_docstring(self.docstring)
            md += f"{signature.docstring}\n\n"

        if self._visible_fields:
            md += "#### Fields\n\n"
            for field in self._visible_fields:
                default_info = ""
                if field.default:
                    default_info = f" = `{field.default}`"

                md += f"- `{field.name}`: `{field.type}`{default_info}\n\n"

        if self._visible_methods:
            md += "#### Methods\n\n"
            for method in self._visible_methods:
                extra_signature = None

                if method.name == "__init__" and self.docstring:
                    extra_signature = signature
                md += method.to_md(True, extra_signature)

        md += "</div>\n\n"
        return md


@dataclass
class Method:
    """Class to hold method information."""

    name: str
    args: list
    kwonlyargs: list
    returns: str
    docstring: str

    def to_md(self, is_method, extra_signature: Signature = None):
        """Convert method to markdown."""

        arg_string = ", ".join(arg.name for arg in self.args)
        ret_string = f" -> {self.returns}"
        if len(arg_string) + len(self.name) + len(ret_string) > 80:
            arg_string = "\n    " + ",\n    ".join(arg.name for arg in self.args) + "\n"

        md = "```python\n"
        md += f"def {self.name}("
        md += arg_string
        md += f"){ret_string}\n```\n\n"

        if self.docstring or extra_signature:
            signature = _parse_method_docstring(self.docstring or "")

            if signature.docstring:
                md += f"{signature.docstring}\n\n"

            if self.args or self.kwonlyargs:
                md += "**Arguments**:"
                arg = None
                all_args = (signature.args or {}) | (extra_signature and extra_signature.args or {})
                for arg in self.args:
                    if arg.name == "self":
                        continue

                    docstring_info = all_args.get(arg.name, None)

                    type_info = "`"

                    type = arg.type
                    if not type and docstring_info:
                        type = docstring_info.type
                    if type:
                        type_info = f"({type})`"

                    default_info = ""
                    if arg.default:
                        default_info = f" (_default: {arg.default}_)"

                    desc = ""
                    if docstring_info:
                        desc = f": {docstring_info}"
                    md += f"\n- `{arg.name}{type_info}{desc}{default_info}"

            if signature.returns:
                md += "\n\n**Returns**:"
                for ret in signature.returns:
                    md += f"\n- {ret}\n"

            md += "\n\n"
        return md


@dataclass
class Arg:
    name: str
    type: str
    default: str | None = None


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


@dataclass
class Module:
    """Class to hold module information."""

    name: str
    docstring: str
    classes: list
    functions: list
    variables: list
    aliases: list
    all_exports: list
    imports: list

    def resolve_export(self, item) -> str:
        """Resolve an export to a module + item."""
        for c in self.classes:
            if c.name == item:
                return c

        for f in self.functions:
            if f.name == item:
                return f

        for v in self.variables:
            if v.name == item:
                return v

        for a in self.aliases:
            if a.name == item:
                return a

        for import_ in self.imports:
            if isinstance(import_, FromImport):
                if item in import_.names:
                    return import_

            elif isinstance(import_, NakedImport):
                if item == import_.module:
                    return import_

        return None

    def resolve_import(self, item: str) -> (str, str):
        """Resolve an import to a module + item.

        Args:
            item: the item to resolve

        Returns:
            the module containing the item
            the item queried
        """

        for import_ in self.imports:
            if isinstance(import_, FromImport):
                if item in import_.names:
                    if import_.relative == 0:
                        return import_.module, item

                    # resolve relative imports.
                    # If we are in foo.bar.baz and we import from .qux import item
                    # we need to resolve to foo.bar.qux.item
                    if import_.module is None:
                        return self.name, item

                    parts = self.name.split(".")
                    parts = parts[: -import_.relative]
                    parts.append(import_.module)

                    return ".".join(parts), item

            elif isinstance(import_, NakedImport):
                if item == import_.module:
                    return item

        logger.warning(f"Could not resolve import {item} from {self.name}")
        return None

    @property
    def _visible_functions(self):
        return [m for m in self.functions if not m.name.startswith("_")]

    @property
    def _visible_classes(self):
        return [c for c in self.classes if not c.name.startswith("_")]

    def to_md(self):
        """Convert module to markdown."""
        if self.name.endswith("__init__"):
            md = f"# package `{self.name[:-9]}`\n\n"

        else:
            md = f"# module `{self.name}`\n\n"

        if self.docstring:
            md += f"{self.docstring}\n\n"

        if self.aliases:
            md += "## Type Aliases\n\n"
            for alias in self.aliases:
                md += alias.to_md()

        if self._visible_functions:
            md += "## Functions\n\n"
            for func in self._visible_functions:
                md += func.to_md(False)

        if self._visible_classes:
            md += "## Classes\n\n"
            for cls in self._visible_classes:
                md += cls.to_md()

        return md


@dataclass
class NakedImport:
    module: str

    def to_md(self):
        return f"import {self._module}\n"


@dataclass
class FromImport:
    module: str
    names: list
    relative: int

    def to_md(self):
        return f"import {self._module}\n"


@dataclass
class TypeAlias:
    name: str
    type: str

    def to_md(self):
        return f"`type {self.name}`: `{self.type}`\n"


class TypeAliasVisitor(ast.NodeVisitor):
    def __init__(self):
        self._name = None
        self._type = None

    def visit_AnnAssign(self, node):
        self._name = node.target.id
        self._type = str(ast.unparse(node.value))

    def finish(self):
        return TypeAlias(self._name, self._type)


@dataclass
class ClassField:
    name: str
    type: str
    default: str | None


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


@dataclass
class Variable:
    name: str
    value: str


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


def root_module(root: str) -> str:
    """Get the root module name from a path.

    Args:
        root: the root path

    Returns:
        the root module name
    """
    return Path(root).name


def path_to_module(root: str, file: str) -> str:
    """Convert a path to a module name.

    Args:
        root: the parent directory of the file
        file: the module name

    Returns:
        the dotted module name
    """

    path = os.path.join(root_module(root), file).replace(".py", "")
    components = path.replace("/./", "/").split("/")
    return ".".join(components)


def fixup_reexports(root_module: str, docs: dict[str, Module]):
    """Inlines items that are reexported from other modules via '__all__'
    lists."""
    for mod, content in docs.items():
        print(f"Fixing up reexports for {mod}")
        for alias in content.all_exports:
            mod, item = content.resolve_import(alias)

            if docs.get(f"{mod}.{item}"):
                continue

            for candidate in [mod, f"{mod}.__init__"]:
                source_doc = docs.get(candidate)

                logger.info(f"Checking {candidate} for {item} - {source_doc}")

                if source_doc:
                    print(f"Resolving {source_doc.name}.{item}")
                    found_item = source_doc.resolve_export(item)
                    logger.info(f"For {mod}.{item} found {found_item}")

                    match found_item:
                        case Class(_, _, _, _):
                            content.classes.append(found_item)
                            break
                        case Method(_, _, _, _):
                            content.functions.append(found_item)
                            break
                        case TypeAlias(_):
                            content.aliases.append(found_item)
                            break
                        case NakedImport(_) | FromImport(_):
                            content.imports.append(item)
                            break
                        case Variable(_):
                            content.variables.append(item)
                            break
                        case None:
                            print(f"Could not find {mod}.{item}")

            else:
                known_modules = "\t" + "\n\t".join(f'"{k}"' for k in docs.keys())
                raise ValueError(
                    f"Could not find module {mod} or {mod}.__init__ - known modules:\n{known_modules}"
                )


def run(root_dir: str, output_dir: str, summary_output_template: str | None):
    """Run the docstring generator."""
    docs = {}
    for root, _, files in os.walk(root_dir):
        relative_root = os.path.relpath(root, root_dir)
        for file in files:
            if file.endswith(".py"):
                logger.info(f"Processing {file}")
                with open(os.path.join(root, file), "r") as f:
                    code = f.read()
                tree = ast.parse(code)

                visitor = AstVisitor(path_to_module(root_dir, os.path.join(relative_root, file)))
                visitor.visit(tree)

                docs[visitor._module] = visitor.finish()

    fixup_reexports(root_module(root), docs)
    os.makedirs(output_dir, exist_ok=True)

    for mod, content in docs.items():
        mod = mod.removesuffix(".__init__")

        parts = mod.split(".")
        for part in parts:
            if part.startswith("_"):
                continue

        with open(os.path.join(output_dir, f"{mod}.md"), "w") as f:
            f.write(content.to_md())

    toc = {}
    # Generated a nested toc
    for mod, content in docs.items():
        parts = mod.split(".")

        current = toc
        for part in parts:
            if part.startswith("_"):
                continue

            current = current.setdefault(part, {})

        current["__init__"] = content

    def write_toc(out_file: file, path: str, toc: dict, level: int = 0):
        for mod in sorted(toc.keys()):
            value = toc[mod]

            newpath = f"{path}.{mod}" if path else mod
            if isinstance(value, dict):
                if value.pop("__init__", {}):
                    out_file.write("  " * level + f"- [{mod}]({newpath}.md)\n\n")

                write_toc(out_file, newpath, value, level + 1)
            else:
                out_file.write("  " * level + f"- [{mod}]({newpath}.md)\n\n")

    toc_content = io.StringIO()
    write_toc(toc_content, "", toc)

    if summary_output_template:
        with open(summary_output_template, "r") as tmpl:
            tmpl = tmpl.read()
    else:
        tmpl = """# SUMMARY
# API Reference

{{toc}}
"""

    with open(os.path.join(output_dir, "SUMMARY.md"), "w") as f:
        f.write(tmpl.replace("{{toc}}", toc_content.getvalue()))


if __name__ == "__main__":
    args = Args.parse()
    run(args.root_dir, args.output_dir, args.summary_template_file)
