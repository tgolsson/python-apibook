"""`python-apibook` is a tool that generates markdown documentation directly
from your Python source code.

It uses the `ast` module to parse your code and extract docstrings,
and then writes the documentation to markdown files. While using the
`ast` for parsing comes with a lot of limitations, it also means no
code is executed, and no dependencies have to be installed. This makes
`python-apibook` very lightweight and easy to use.

The goal of the tool is to integrate seamlessly into your existing
`mdbook` documentation, but you can provide a custom summary template
if you want to use another system.
"""
