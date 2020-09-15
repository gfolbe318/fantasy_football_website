from setuptools import find_packages, setup

setup(
    name="ff_website",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "autopep8",
        "click",
        "Flask",
        "flask-CLI",
        "itsdangerous",
        "jinja2",
        "MarkupSafe",
        "pip",
        "pycodestyle",
        "setuptools",
        "toml",
        "Werkzeug"
    ],
)
