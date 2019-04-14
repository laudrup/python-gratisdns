from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='python-gratisdns',
    version='0.2',
    author='Mads Sülau Jørgensen, Kasper Laudrup',
    author_email='mads@sulau.dk, laudrup@stacktrace.dk',
    url='https://github.com/laudrup/python-gratisdns',
    packages=[
        'python_gratisdns',
    ],
    license='MIT',
    description='Unofficial library for interfacing with the gratisdns.dk web interface',
    long_description=readme(),
    long_description_content_type='text/markdown',
    install_requires=[
        'requests',
        'wheel',
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose'
    ],
    keywords='gratisdns, dns',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
    ],
)
