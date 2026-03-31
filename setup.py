from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="datascreeniq",
    version="1.0.3",
    description="Real-time data quality screening API — PASS / WARN / BLOCK in under 10ms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DataScreenIQ",
    author_email="app@datascreeniq.com",
    url="https://datascreeniq.com",
    project_urls={
        "Documentation": "https://datascreeniq.com/docs",
        "Source":        "https://github.com/datascreeniq/datascreeniq-python",
        "Tracker":       "https://github.com/datascreeniq/datascreeniq-python/issues",
    },
    license="MIT",
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "pandas": ["pandas>=1.3.0"],
        "excel":  ["openpyxl>=3.0.0"],
        "all":    ["pandas>=1.3.0", "openpyxl>=3.0.0"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    keywords=[
        "data quality", "data validation", "schema drift",
        "data pipeline", "etl", "data engineering",
    ],
)
