from setuptools import setup, find_packages

setup(
    name="SpectraChirp",
    version="1.0.0",
    author="ByteBuilder",
    author_email="your-email@example.com",  # Placeholder
    description="A robust acoustic modem for transmitting data through sound using MFSK.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/saas-erp-hub/SpectraChirp",
    project_urls={
        "Bug Tracker": "https://github.com/saas-erp-hub/SpectraChirp/issues",
    },
    packages=find_packages(),
    py_modules=["cli"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Communications",
        "Topic :: Multimedia :: Sound/Audio",
    ],
    python_requires='>=3.8',
    install_requires=open('backend/requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': [
            'spectrachirp=cli:app',
        ],
    },
)
