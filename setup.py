from setuptools import setup
from deploy_addon import __version__

setup(
    name='deploy-addon',
    version=__version__,
    author='Roman V.M.',
    packages=['deploy_addon'],
    entry_points={
        'console_scripts': ['deploy-addon=deploy_addon.__main__:main'],
    },
    install_requires=['requests'],
    zip_safe=False,
)
