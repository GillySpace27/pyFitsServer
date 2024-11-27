from setuptools import setup, find_packages

setup(
    name='pyfitsserver',
    version='v0.0.15',
    description='A lightweight server to facilitate the rendering and previewing of FITS files.',
    long_description=open("README.md").read(),  # Reads the content of your README.md
    long_description_content_type="text/markdown",  # Specifies that README is in Markdown format
    author='Gilly',
    author_email='gilly@swri.org',
    url='https://github.com/GillySpace27/pyFitsServer',
    packages=find_packages(),
    install_requires=[
        "Flask>=2.0,<3.0",
        "numpy",
        "astropy",
        "matplotlib",
        "parse",
        "Pillow",
        "requests",
        "Werkzeug==2.2.2",  # Explicitly pinned version
    ],
    entry_points={
        'console_scripts': [
            'pyfitsserver=pyfitsserver.server:main',
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