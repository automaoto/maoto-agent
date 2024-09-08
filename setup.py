from setuptools import setup, find_packages
from Cython.Build import cythonize
import os

# Automatically find Python files in the /src/maoto_agent directory
def find_py_modules(package_dir):
    py_files = []
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                py_files.append(os.path.join(root, file))
    return py_files

# Specify the source directory
cython_modules = cythonize(find_py_modules('src/maoto_agent'))

setup(
    name='maoto_agent',
    use_scm_version=True,  # Automatically fetches the version from Git tags
    setup_requires=['setuptools-scm'],  # Required to use setuptools-scm
    ext_modules=cython_modules,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
)