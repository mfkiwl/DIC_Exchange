#  Standardised exchange file format for 2D/3D-DIC results, based on HDF5
#  Copyright (c) 2023. Chair of Forming and Machining Processes, TU Dresden
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


import os
import sys

from DIC_Exchange.convert_to import load_from

path_dir = r"D:\HDD_Documents\Projet\ZugVersuch\CodeBase\Cut_Line_GUI\data_test"

for a_path in os.listdir(path_dir):
    if "hdf5" not in a_path:
        dic_res = load_from(os.path.join(path_dir, a_path), force_rupture_ratio=.8)
        dic_res.save_to_hdf5(os.path.join(path_dir, a_path[:-4] + ".hdf5"))
        print("saved " + str(os.path.join(path_dir, a_path[:-4] + ".hdf5")))