import json
import os
from setuptools import setup


def get_version(fname):
    with open(fname) as f:
        schema = json.load(f)
        k8s_version = schema["info"]["version"].lstrip('v')

    patch = os.environ.get('GITHUB_RUN_ID', 'dev0')
    return f"{k8s_version}.{patch}"


setup(
    name='lightkube-models',
    version=get_version("openapi/swagger.json"),
    description='Models and Resources for lightkube module',
    long_description='Models and Resources for lightkube module',
    author='Giuseppe Tribulato',
    author_email='gtsystem@gmail.com',
    license='Apache Software License',
    url='https://github.com/gtsystem/lightkube-models',
    packages=['lightkube.models', 'lightkube.resources', 'lightkube.base'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ]
)
