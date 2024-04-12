resource(
    name="template",
    source="./SUMMARY.tmpl",
)

pex_binary(
    name="apibook",
    entry_point="apibook.cli:main",
    dependencies=["//apibook/cli.py"],
)

adhoc_tool(
    name="build-apibook",
    runnable=":apibook",
    args=["../apibook", "src", "--summary-template-file", "SUMMARY.tmpl"],
    execution_dependencies=[
        ":template",
        "//apibook/cli.py",
    ],
    log_output=True,
    output_directories=["src"],
    root_output_directory="/",
)

md_book(
    sources=["book.toml", "src/*.md"],
    dependencies=[
        "//:package_data",
        ":build-apibook",
    ],
)
