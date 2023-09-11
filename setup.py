from setuptools import find_packages, setup
import pipreqs

# https://pypi.org/project/pipreqs/
# https://stackoverflow.com/questions/8161617/how-can-i-specify-library-versions-in-setup-py
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="ff_website",
    version="1.0.0",
    packages=find_packages(),
    install_requires=required,
)
