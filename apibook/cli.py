"""Main entrypoint for the CLI usage.

This module provides a command line interface for the `apibook` package. The CLI
 accepts the following arguments:

- `root_dir`: the root directory to search for Python files
- `output_dir`: the output directory for markdown files
- `summary_template_file`: Optional path to a file containing a summary template.

Example usage:
```bash
python -m apibook.cli my_package/ doc/src --summary-template-file doc/SUMMARY.tmpl
```

Running the above command will generate markdown files for all Python files in the `my_package`, and
write them to the `doc/src` directory. The `SUMMARY.md` file will be generated using the template
found in `doc/SUMMARY.tmpl`.

An example template file might look like this:
```markdown
# SUMMARY

[Introduction](README.md)

# Usage

- [Quickstart](quickstart.md)
- [Advanced Usage](advanced.md)

# API Reference

{{apibook_toc}}
```
"""

import argparse
import logging
from dataclasses import dataclass

from rich.console import Console
from rich.logging import RichHandler

from .main import run

console = Console()


@dataclass
class Args:
    """Class to hold command line arguments."""

    root_dir: str
    output_dir: str
    summary_template_file: str | None = None
    verbose: bool = False

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
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Enable verbose logging.",
        )

        args = parser.parse_args()
        return Args(
            args.root_dir,
            args.output_dir,
            args.summary_template_file,
            args.verbose,
        )


def main():
    args = Args.parse()
    FORMAT = "%(message)s"

    level = "DEBUG" if args.verbose else "INFO"
    logging.basicConfig(level=level, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

    try:
        run(args.root_dir, args.output_dir, args.summary_template_file)
    except:  # noqa: E722
        if args.verbose:
            console.print_exception(show_locals=True)

        raise


if __name__ == "__main__":
    main()
