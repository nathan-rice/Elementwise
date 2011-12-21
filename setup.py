"""
Elementwise provides a convenient proxy object on an iterable which transforms
operator behavior, function and methods into vectorized versions which operate
on all members of the iterable.
"""

from distutils.core import setup

setup(
    name="elementwise",
    py_modules=["elementwise"],
    author="Nathan Rice",
    author_email="nathan.alexander.rice@gmail.com",
    version="0.111220c",
    license="BSD 2 clause",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],

)
