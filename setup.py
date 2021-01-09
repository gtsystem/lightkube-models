from setuptools import setup
from pathlib import Path

from lightkube.models import __version__


setup(
    name='lightkube-models',
    version=__version__,
    description='Models and Resources for lightkube module',
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    author='Giuseppe Tribulato',
    author_email='gtsystem@gmail.com',
    license='Apache Software License',
    url='https://github.com/gtsystem/lightkube-models',
    packages=['lightkube.models', 'lightkube.resources'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
