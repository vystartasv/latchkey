from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="latchkey",
    version="0.1.0",
    description="Encrypted credential store for autonomous AI agents — agents let themselves in",
    long_description=(Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=["cryptography"],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "latchkey=latchkey.cli:main",
        ],
    },
)
