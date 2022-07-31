from setuptools import find_packages
from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="safeworder",
    version="1.0.0",
    description="Replace dirty strings with clean ones",
    author="Tommel",
    package_data={
      'safeworder': ['*'],
    },
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(),
    install_requires=required
)