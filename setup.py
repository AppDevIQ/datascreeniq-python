from setuptools import setup, find_packages

setup(
    name="datascreeniq",
    version="1.0.8",  # MUST match pyproject.toml
    packages=find_packages(exclude=["tests*", "examples*"]),
    install_requires=[
        "requests>=2.28.0",
        "certifi>=2023.0.0"
    ],
    extras_require={
        "pandas": ["pandas>=1.3.0"],
        "excel": ["openpyxl>=3.0.0"],
        "truststore": ["truststore>=0.10.0"],
        "windows": ["certifi-win32>=1.6.1"],
        "all": [
            "pandas>=1.3.0",
            "openpyxl>=3.0.0",
            "truststore>=0.10.0",
            "certifi-win32>=1.6.1"
        ],
    },
)