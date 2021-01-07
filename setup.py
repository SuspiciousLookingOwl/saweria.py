import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="saweria",
    version="0.0.1",
    author="SuspiciousLookingOwl",
    author_email="me@vincentjonathan.com",
    description="Python API Wrapper for Saweria",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SuspiciousLookingOwl/saweria.py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)