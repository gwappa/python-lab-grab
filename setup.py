import setuptools

setuptools.setup(
    name='ks-ic-grab',
    version="0.1",
    description='a grabber for ImagingSource cameras equipped with the optional NVenc encoder.',
    url='https://github.com/gwappa/python-IC-grab',
    author='Keisuke Sehara',
    author_email='keisuke.sehara@gmail.com',
    license='MIT',
    python_requires=">=3.7",
    install_requires=[
        'ks-tisgrabber',
        # python-opencv-headless,
        # pyqtgraph
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        ],
    packages=['ic_grab',],
    package_data={
        # nothing for the time being
    },
    entry_points={
        'console_scripts': [ 'ic-grab=ic_grab:parse_commandline', ],
    }
)
