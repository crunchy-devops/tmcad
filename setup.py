from setuptools import setup

setup(
    name='tmcad',
    version='0.1',
    description='Memory-efficient terrain point management system',
    author='Your Name',
    author_email='your.email@example.com',
    packages=['tmcad'],
    install_requires=[
        'numpy>=1.21.0',
        'scipy>=1.7.0'
    ],
    python_requires='>=3.7'
)
