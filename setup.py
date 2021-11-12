# MIT License
#
# Copyright (c) 2021 Keisuke Sehara
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import setuptools

setuptools.setup(
    name='ks-lab-grab',
    version="0.5.0",
    description='a grabber for ImagingSource cameras equipped with the optional NVenc encoder.',
    url='https://github.com/gwappa/python-lab-grab',
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
        'lab_grab': ["enctest/*.jpg"],
    },
    entry_points={
        'console_scripts': [ 'lab-grab=lab_grab:parse_commandline', ],
    }
)
