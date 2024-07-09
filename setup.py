from setuptools import setup, find_packages

setup(
    name='translator_po',
    version='0.3.2',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'polib==1.2.0',
        'deep-translator==1.11.4',
        'tqdm==4.66.1',
        'colorlog==6.8.2',
        'termcolor==2.4.0',
    ],
    author='Zahfron Adani Kautsar',
    author_email='zhafronadani@gmail.com',
    description='This project is a command-line tool for translating `.po` and `.pot` files using various translation '
    'services. It supports multiple translators and can handle placeholders in the text.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tickernelz/translator_po',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'translator_po=translator_po.main:main',
        ],
    },
)
