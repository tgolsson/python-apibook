"""Generates markdown from Python docstrings."""

import ast
import io
import logging
import os
from pathlib import Path

from ._ast import AstVisitor
from .data import Class, FromImport, Method, Module, NakedImport, TypeAlias, Variable

logger = logging.getLogger(__name__)


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
        logger.info("Fixing up reexports for '%s'", mod)
        for alias in content.all_exports:
            module, item = content.resolve_import(alias)

            if module == mod:
                continue  # Don't reexport from the same module

            if docs.get(f"{module}.{item}"):
                continue

            for candidate in [module, f"{module}.__init__"]:
                source_doc = docs.get(candidate)

                logger.info(f"Checking {candidate} for {item}")

                if source_doc:
                    logger.info(f"Resolving {source_doc.name}.{item}")
                    found_item = source_doc.resolve_export(item)
                    logger.debug(f"For {mod}.{item} found {found_item}")

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
                    f"Could not find module {module} or {module}.__init__ - known modules:\n{known_modules}"
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
                    out_file.write("  " * level + f"- [`{mod}`]({newpath}.md)\n\n")

                write_toc(out_file, newpath, value, level + 1)
            else:
                out_file.write("  " * level + f"- [`{mod}`]({newpath}.md)\n\n")

    toc_content = io.StringIO()
    write_toc(toc_content, "", toc)

    if summary_output_template:
        with open(summary_output_template, "r") as tmpl:
            tmpl = tmpl.read()
    else:
        tmpl = """# SUMMARY
# API Reference

{{apibook_toc}}
"""
    with open(os.path.join(output_dir, "SUMMARY.md"), "w") as f:
        f.write(tmpl.replace("{{apibook_toc}}", toc_content.getvalue()))
