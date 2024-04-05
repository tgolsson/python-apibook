resource(
    name="template",
    source="./SUMMARY.tmpl",
)

pex_binary(
    name="apidoc",
    entry_point="python_apibook.cli:main",
    dependencies=["//python_apibook/cli.py"],
)

adhoc_tool(
    name="build-apidoc",
    runnable=":apidoc",
    args=["../python_apibook", "src", "--summary-template-file", "SUMMARY.tmpl"],
    execution_dependencies=[
        ":template",
        "//python_apibook/cli.py",
    ],
    log_output=True,
    output_directories=["src"],
    root_output_directory="/",
)

md_book(
    sources=["book.toml", "src/*.md"],
    dependencies=[
        "//:readme",
        ":build-apidoc",
    ],
)
