from setuptools import setup
from addon_submitter import __version__

setup(
    name='addon-submitter',
    version=__version__,
    author='Roman V.M.',
    license='GPL v.3',
    packages=['addon_submitter'],
    package_data={'addon_submitter': ['pr-template.md']},
    entry_points={
        'console_scripts': ['submit-addon=addon_submitter.__main__:main'],
    },
    install_requires=['requests'],
    zip_safe=False,
)
