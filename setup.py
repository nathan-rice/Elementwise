"""
Elementwise provides convenient proxy objects which build operation chains 
generatively. create chain on an iterable which transforms
operator behavior, function and methods into vectorized versions which operate
on all members of the iterable.
"""

from distutils.core import setup

setup(
    name="elementwise",
    py_modules=["elementwise"],
    author="Nathan Rice",
    author_email="nathan.alexander.rice@gmail.com",
    version="0.120114",
    license="BSD 2 clause",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],

)
