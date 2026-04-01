from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="datascreeniq",
    version="1.0.7",
    description="Real-time data quality screening API — PASS / WARN / BLOCK in milli seconds",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DataScreenIQ",
    author_email="app@datascreeniq.com",
    url="https://datascreeniq.com",
    project_urls={
        "Homepage":      "https://datascreeniq.com",
        "Documentation": "https://datascreeniq.com/docs",
        "Source":        "https://github.com/AppDevIQ/datascreeniq-python",
        "Tracker":       "https://github.com/AppDevIQ/datascreeniq-python/issues",
        "Privacy":       "https://datascreeniq.com/privacy",
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
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Database",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "data quality", "data validation", "schema drift", "schema validation",
        "data pipeline", "etl", "data engineering", "airflow", "prefect",
        "data observability", "null detection", "type validation", "dbt",
        "cloudflare workers", "real-time validation", "data quality api",
        "pipeline validation", "data integrity", "schema monitoring",
    ],
)
