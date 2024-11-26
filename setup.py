from setuptools import setup, find_packages

setup(
    name='pyfitsserver',
    version='0.1.0',
    description='A lightweight server to facilitate the rendering and previewing of FITS files.',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/GillySpace27/pyFitsServer',
    packages=find_packages(),
    install_requires=[
        "Flask",
        "numpy",
        "astropy",
        "matplotlib",
        "parse",
        "Pillow",
        "requests"
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
