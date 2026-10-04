from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'ens160_sensors'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Valeria Vallebueno Ayzikova / TFG integration',
    maintainer_email='vvalleay94@alumnes.ub.edu',
    description='ENS160 serial acquisition, CSV logging and eCO2 point-cloud nodes.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'ens160_sensors_hw_exec = ens160_sensors.sensor_pose_node_hw:main',
            'ens160_sensors_sw_exec = ens160_sensors.sensor_pose_node_sw:main',
            'csv_logger_exec = ens160_sensors.csv_logger:main',
            'csv_logger_co2cloud_exec = ens160_sensors.csv_logger_co2cloud:main',
            'eco2_cloud_exec = ens160_sensors.eco2_cloud:main',
        ],
    },
)
