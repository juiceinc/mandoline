from distutils.core import setup

setup(
    name='Mandoline',
    version='0.3.0',
    author='Chris Gemignani',
    author_email='chris.gemignani@juiceanalytics.com',
    packages=['mandoline',],
    scripts=[],
    url='http://www.juiceanalytics.com',
    license='LICENSE.txt',
    description='Cleaning tool for slice.',
    long_description=open('README.txt').read(),
    install_requires=[
        "boto >= 2.0",
        "openpyxl == 1.6.2",
        "requests == 1.2.2",
        "nose == 1.3.0",
    ],
)
