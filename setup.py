from setuptools import setup, find_packages

setup(
    name='pyfitsserver',
    version='v0.0.2-alpha',
    description='A lightweight server to facilitate the rendering and previewing of FITS files.',
    author='Gilly',
    author_email='gilly@swri.org',
    url='https://github.com/GillySpace27/pyFitsServer',
    readme="README.md",
    packages=find_packages(),
    install_requires=[
        "Flask",
        "numpy",
        "astropy",
        "matplotlib",
        "parse",
        "Pillow",
        "requests",
        "scipy",
    ],
    entry_points={
        'console_scripts': [
            'pyfitsserver=fits_preview_server.server:main',
        ],
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.8',
)
