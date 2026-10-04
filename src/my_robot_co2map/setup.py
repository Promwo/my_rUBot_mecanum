from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'my_robot_co2map'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'reference_maps'), glob('reference_maps/*')),
    ],
    scripts=glob('scripts/*.py'),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Valeria Vallebueno Ayzikova / TFG integration',
    maintainer_email='vvalleay94@alumnes.ub.edu',
    description='Offline eCO2 mapping and live ENS160 plotting tools.',
    license='Apache-2.0',
)
