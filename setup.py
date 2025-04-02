#!/usr/bin/env python
"""
Setup script for the pocksup package.
"""

import os
import re
from setuptools import setup, find_packages

# Get version from pocksup/version.py
with open(os.path.join('pocksup', 'version.py'), 'r') as f:
    version_file = f.read()
    version_match = re.search(r"__version__ = ['\"]([^'\"]*)['\"]", version_file)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")

# Read long description from README.md
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='pocksup',
    version=version,
    description='A modern Python library for WhatsApp connectivity',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Pocksup Team',
    author_email='mdanut159@gmail.com',
    url='https://github.com/gyovannyvpn123/Pocksup-lib',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.11',
    install_requires=[
        'requests>=2.25.0',
        'websocket-client>=1.2.0',
        'protobuf>=4.0.0',
        'cryptography>=3.4.0',
        'Flask>=2.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.12.0',
            'black>=21.5b2',
            'isort>=5.9.0',
            'mypy>=0.812',
            'flake8>=3.9.0',
        ],
        'web': [
            'Flask>=2.0.0',
            'Flask-Cors>=3.0.10',
        ],
    },
    entry_points={
        'console_scripts': [
            'pocksup-chat=examples.chat_client:main',
            'pocksup-media=examples.media_sender:main',
            'pocksup-api=examples.web_api:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Communications :: Chat',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='whatsapp, messaging, chat, communication, yowsup',
    project_urls={
        'Documentation': 'https://github.com/gyovannyvpn123/Pocksup-lib',
        'Source': 'https://github.com/gyovannyvpn123/Pocksup-lib',
        'Issues': 'https://github.com/gyovannyvpn123/Pocksup-lib/issues',
    },
)
