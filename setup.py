from setuptools import setup, find_namespace_packages

setup(
    name="agent-config-init",
    version="0.1.0",
    description="Initialize and merge agent configuration files",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.8",
    scripts=["cmd/agent-config-init"],
    data_files=[
        ("etc/agent-config-init/claude", ["config/claude/settings.json"]),
    ],
)
