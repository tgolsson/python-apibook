resources(name="package_data", sources=["pyproject.toml", "README.md", "LICENSE-MIT.txt", "CHANGELOG.md"])

python_requirements(
    name="root",
    source="pyproject.toml",
)

python_distribution(
    name="package",
    dependencies=[
        ":package_data",
        "//apibook:apibook",
    ],
    provides=python_artifact(
        name="apibook",
        version="0.1.2",
        long_description_content_type="markdown",
    ),
    long_description_path="README.md",
    repositories=["@pypi"],
    entry_points={
        "python-apibook": {
            "my-script": "apibook.cli:main",
        }
    },
)
