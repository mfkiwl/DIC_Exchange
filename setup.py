#  Standardised exchange file format for 2D/3D-DIC results, based on HDF5
#  Copyright (c) 2022. Chair of Forming and Machining Processes, TU Dresden
#  This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.

from setuptools import setup

setup(
    name='DIC_Exchange',
    version='0.1a',
    packages=['DIC_Exchange'],
    url='',
    license='AGPL v3.0',
    author='Chair of Forming and Machining Processes, TU Dresden',
    author_email='remi.lafarge@tu-dresden.de',
    description='A proposition for a standardised exchange file format for 2D/3D-DIC'
                ' results for material testing purposes, based on HDF5'
)
