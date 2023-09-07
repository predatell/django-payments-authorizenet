#!/usr/bin/env python
from setuptools import setup


PACKAGES = [
    'payments_authorizenet',
]

REQUIREMENTS = [
    'Django',
    'django-payments',
    'authorizenet',
    'authorizenet-pyxb-new',
    'requests',
]

setup(
    name='django-payments-authorizenet',
    author_email='predatell@disroot.org',
    description='A django-payments backend for the Authorize.Net payment gateway',
    version='0.1',
    url='https://github.com/predatell/django-payments-authorizenet',
    packages=PACKAGES,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.11',
        'Framework :: Django',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=REQUIREMENTS,
    zip_safe=False)
