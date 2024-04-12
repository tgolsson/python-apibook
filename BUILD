resources(name="package_data", sources=["pyproject.toml", "README.md", "LICENSE-MIT.txt", "CHANGELOG.md"])

python_requirements(
    name="root",
    source="pyproject.toml",
)

python_distribution(
    name="package",
    dependencies=[
        ":package_data",
        "//python_apibook:python_apibook",
    ],
    provides=python_artifact(
        name="python-apibook",
        version="0.1.0",
        long_description_content_type="markdown",
    ),
    long_description_path="README.md",
    repositories=["@pypi"],
    entry_points={
        "python-apibook": {
            "my-script": "python_apibook.cli:main",
        }
    },
)
