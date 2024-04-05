import logging
from dataclasses import dataclass

import docstring_parser

logger = logging.getLogger(__name__)

_VISIBLE_FUNCTIONS = ["__init__", "__call__"]


@dataclass
class Arg:
    name: str
    type: str
    default: str | None = None
    docstring: str = None


@dataclass
class Signature:
    args: list
    returns: list
    docstring: str


def _parse_method_docstring(docs: str) -> Signature:
    doc = docstring_parser.parse(docs.replace("\\", "\\\\"))

    args = {}
    returns = []

    for param in doc.params:
        if "(" in param.arg_name or "." in param.arg_name:
            args[param.type_name] = Arg(param.type_name, param.arg_name, param.default, param.description)
        else:
            args[param.arg_name] = Arg(param.arg_name, param.type_name, param.default, param.description)

    if doc.returns:
        returns.append(doc.returns.description)

    docstring_frags = []

    if doc.short_description:
        docstring_frags.append(doc.short_description)

    if doc.long_description:
        docstring_frags.append(doc.long_description)

    return Signature(args, returns, "\n".join(docstring_frags))


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
        if self.kwonlyargs:
            arg_string += ", *" + ", ".join(arg.name for arg in self.kwonlyargs)
        ret_string = f" -> {self.returns}"
        if len(arg_string) + len(self.name) + len(ret_string) > 80:
            arg_string = "\n    " + ",\n    ".join(arg.name for arg in self.args) + "\n"
            if self.kwonlyargs:
                arg_string += ",\n    *" + ",\n    ".join(arg.name for arg in self.kwonlyargs) + "\n"

        md = "```python\n"
        md += f"def {self.name}("
        md += arg_string
        md += f"){ret_string}\n```\n\n"
        md += '<div style="padding-left: 20px;">\n\n'
        if self.docstring or extra_signature:
            signature = _parse_method_docstring(self.docstring or "")

            if signature.docstring:
                md += f"{signature.docstring}\n\n"

            non_self_args = [arg for arg in self.args if arg.name != "self"]
            if non_self_args or self.kwonlyargs:
                md += "**Arguments**:"
                arg = None
                all_args = (signature.args or {}) | (extra_signature and extra_signature.args or {})

                def emit_arg(arg):
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
                    elif docstring_info and docstring_info.default:
                        default_info = f" (_default: {docstring_info.default}_)"

                    desc = ""
                    if docstring_info and docstring_info.docstring:
                        desc = f": {docstring_info.docstring}"

                    return f"\n- `{arg.name}{type_info}{desc}{default_info}"

                for arg in self.args:
                    if arg.name == "self":
                        continue
                    md += emit_arg(arg)

                for arg in self.kwonlyargs:
                    md += emit_arg(arg)

            if signature.returns:
                md += "\n\n**Returns**:"
                for ret in signature.returns:
                    md += f"\n- {ret}\n"

            md += "\n\n"

        md += "</div>\n\n"
        return md


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


@dataclass
class ClassField:
    name: str
    type: str
    default: str | None


@dataclass
class Variable:
    name: str
    value: str
