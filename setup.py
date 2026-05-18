"""Minimal setup.py for the paper_braincoder benchmarking project.

Conda handles all heavy deps via create_env/environment_*.yml.
This file just makes `pip install -e .` work for editable installs,
exposing the `prfbench` package to importers.
"""
from setuptools import setup, find_packages

setup(
    name='prfbench',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.10',
    install_requires=[],  # all deps in conda env
)
