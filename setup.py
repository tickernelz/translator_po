from setuptools import setup, find_packages

setup(
    name='translator_po',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'polib==1.2.0',
        'deep-translator==1.11.4',
        'tqdm==4.66.1',
    ],
    author='Zahfron Adani Kautsar',
    author_email='zhafronadani@gmail.com',
    description='Translator PO is a Python-based tool designed to translate .po and .pot files using various '
    'translation services. It supports multiple translators like Google, Microsoft, Deepl, and more, '
    'allowing for flexible and efficient translation of localization files.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tickernelz/translator_po',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
