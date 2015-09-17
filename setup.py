#!/usr/bin/env python

from setuptools import setup, find_packages


# Read long description
with open('README.rst') as f:
    long_description = f.read()

setup(
    name='s3-deploy-website',
    version='0.0.1',
    license='MIT',
    author='Jon Lund Steffensen',
    author_email='jonlst@gmail.com',

    description='S3 website deployment tool',
    long_description=long_description,

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            's3-deploy-website = s3_deploy.deploy:main'
        ]
    },
    test_suite='s3_deploy.tests',
    install_requires=[
        'boto', 'PyYAML', 'six'
    ])
