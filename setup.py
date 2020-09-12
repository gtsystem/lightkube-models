import os
import sys
import json
from setuptools import setup

PATCH_VERSION = 0

try:
    SPECFILE = os.environ["SPECFILE"]
except KeyError:
    print("Environment variable SPECFILE not set")
    sys.exit(-1)


def get_version(fname):
    with open(fname) as f:
        schema = json.load(f)
        k8s_version = schema["info"]["version"].lstrip('v')

    return f"{k8s_version}.{PATCH_VERSION}"


setup(
    name='lightkube-models',
    version=get_version(SPECFILE),
    description='Models and Resources for lightkube module',
    long_description='Models and Resources for lightkube module',
    author='Giuseppe Tribulato',
    author_email='gtsystem@gmail.com',
    license='Apache Software License',
    url='https://github.com/gtsystem/lightkube-models',
    packages=['lightkube.models', 'lightkube.resources'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ]
)
