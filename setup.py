#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='s3-deploy-website',
    version='0.0.1',
    license='MIT',
    author='Jon Lund Steffensen',
    author_email='jonlst@gmail.com',

    description='S3 website deployment tool',

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
