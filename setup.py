from setuptools import setup
from addon_submitter import __version__

setup(
    name='addon-submitter',
    version=__version__,
    author='Roman V.M.',
    packages=['addon_submitter'],
    entry_points={
        'console_scripts': ['submit-addon=addon_submitter.__main__:main'],
    },
    install_requires=['requests'],
    zip_safe=False,
)
