# `python-apibook`

Are you tired of fighting Sphinx to get it to do what you want? Do you want to write your documentation in Markdown? Do you want to easily combine prose with API docs? Then this is the tool for you!

`python-apibook` uses the AST module to parse your code and generate API documentation in Markdown format, and can easily be merged into your existing `mdbook` `SUMMARY.md` file.

## Installation

```bash
pip install git+https://github.com/tgolsson/python-apibook.git
```

## Usage

To see the available options, run:
```bash
python -m apibook --help
```

To generate API documentation for a package, run:
```bash
python_apibook my_package doc/src --summary-template-file doc/SUMMARY.tmpl
```

This will generate all markdown sources and a `SUMMARY.md` file in the `doc/src` directory, which you can include in your `mdbook` project. _Hint_: Combine this with `mdbook serve doc` to see the results in real-time.
