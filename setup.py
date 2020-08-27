from setuptools import setup, find_packages

setup(
    name="GitIssueBot",
    version="0.1",
    packages=find_packages(),
    scripts=['bin/clean_issues'],
)
