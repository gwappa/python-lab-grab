import setuptools

setuptools.setup(
    name='ks-ic-grab',
    version="0.4.1",
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
    packages=setuptools.find_packages(),
    package_data={
        'ic_grab.ui': ["enctest/*.jpg"],
    },
    entry_points={
        'console_scripts': [ 'ic-grab=ic_grab:parse_commandline', ],
    }
)
