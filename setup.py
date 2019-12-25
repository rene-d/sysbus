import sys
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))


# Get the long description from the README file
with open(path.join(here, "README.en.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sysbus",
    version="0.0.2",
    description="Control by script your Livebox 2,3,4",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rene-d/sysbus",
    author="Rene Devichi",
    author_email="rene.github@gmail.com",
    classifiers=[
        'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="livebox sysbus",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.5, <4",
    install_requires=["requests"],

    package_data={  # Optional
        'sysbus': ['manuf'],
    },

    entry_points={"console_scripts": ["sysbus=sysbus.sysbus:main"]},
    project_urls={
        "Source": "https://github.com/rene-d/sysbus",
        "Bug Reports": "https://github.com/rene-d/sysbus/issues",
    },
)
