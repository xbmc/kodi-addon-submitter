from setuptools import setup

setup(
    name='deploy-addon',
    author='Roman V.M.',
    packages=['deploy_addon'],
    entry_points={
        'console_scripts': ['deploy-addon=deploy_addon.__main__:main'],
    },
    install_requires=['requests'],
    zip_safe=False,
)
