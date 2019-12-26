#!/usr/bin/env python3

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))


# Get the long description from the README file
with open(path.join(here, "README.en.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sysbus",
    version="0.0.4",
    description="Control by script your Livebox 2,3,4",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://rene-d.github.io/sysbus",
    author="Rene Devichi",
    author_email="rene.github@gmail.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Environment :: Console",
        "Topic :: Home Automation",
        "Intended Audience :: Telecommunications Industry",
        "Intended Audience :: Science/Research",
    ],
    keywords="livebox sysbus",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.5",
    install_requires=["requests", "graphviz", "qrcode"],
    package_data={"sysbus": ["manuf"]},
    entry_points={"console_scripts": ["sysbus=sysbus.sysbus:main"]},
    project_urls={
        "Source": "https://github.com/rene-d/sysbus",
        "Bug Reports": "https://github.com/rene-d/sysbus/issues",
    },
)
