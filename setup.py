from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import setuptools

__version__ = '0.1.0'

class get_pybind_include(object):
    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)

ext_modules = [
    Extension(
        'match_engine',
        ['src/lob/match_engine.cpp'],
        include_dirs=[
            get_pybind_include(),
            get_pybind_include(user=True),
        ],
        language='c++',
        extra_compile_args=['-std=c++17']
    ),
]

setup(
    name='market_maker',
    version=__version__,
    ext_modules=ext_modules,
    setup_requires=['pybind11>=2.10.0'],
    install_requires=['pybind11>=2.10.0'],
    zip_safe=False,
) 