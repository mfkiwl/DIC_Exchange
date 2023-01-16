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

import numpy as np
import h5py
import os


class DIC_Result():

    """
    Class providing the data models and input output methods for handling DIC results for material testing
    """


    def __init__(self, coords: np.ndarray, strains: np.ndarray, force: np.ndarray, time: np.ndarray, mesh: np.ndarray):
        """
        Initiating a DIC_Result object, vectorize or not,
        with n timestep, m points and q elements
        :param np.ndarray coords: coordinate array of shape (n,m,3) in order x,y,z
        :param np.ndarray strains: strains array of shape (n,m,3) in order (e_xx, e_yy, e_xy)
        :param np.ndarray force: time series of the force in an array (n,)
        :param np.ndarray time: value of the time in an array (n,)
        :param np.ndarray mesh: mesh represented by an array of shape (q, 3) with the value corresponding to coords and strains
        """

        assert isinstance(coords, np.ndarray)
        assert isinstance(strains, np.ndarray)
        assert isinstance(coords, np.ndarray)
        assert isinstance(force, np.ndarray)
        assert isinstance(time, np.ndarray)
        assert isinstance(mesh, np.ndarray)

        self.strains = strains
        self.coords = coords
        self.force = force
        self.time = time
        self.mesh = mesh
        self.vectorize = False
        self.meta_data = {"version": "0.1"}

    def save_to_hdf5(self, path_h5: str) -> None:
        """
        Save the Dic Result in a hdf5 file
        :param str path_h5: path to write the file
        """
        with h5py.File(path_h5, "w") as hdf5:

            # Saving metadata
            for a_meta_key in self.meta_data.keys():
                hdf5.attrs[a_meta_key] = self.meta_data[a_meta_key]

            # Saving the scalars
            hdf5.create_group("scalar")
            hdf5["scalar"].create_dataset("time", data=self.time)
            hdf5["scalar"].create_dataset("force", data=self.time)

            # Saving the vector information
            hdf5.create_group("vector")
            hdf5["vector"].create_dataset("strains", data=self.strains)
            hdf5["vector"].create_dataset("coordinates", data=self.coords)

            # Saving the mesh
            hdf5.create_dataset("mesh", data=self.mesh)

    @classmethod
    def load_from_hdf5(cls, path: str) -> "DIC_Result":
        """
        Load an hdf5 file representing an DIC_Result object
        :param str path: path of the file to write
        :return DIC_Result: content of the hdf5 file in a DIC_Result object
        """

        with h5py.File(path, "r") as h5file:

            # read meta data

            buff_meta_data = {}

            for el in h5file:
                buff_meta_data[el] = h5file.attrs[el]

            # read scalar

            force = np.array(h5file["scalar"]["time"])
            time = np.array(h5file["scalar"]["force"])

            # read vector
            coords = np.array(h5file["scalar"]["coordinates"])
            strains = np.array(h5file["scalar"]["strains"])

            # read mesh
            mesh = np.array(h5file["mesh"])

            load_hdf5 = cls(coords, strains, force, time, mesh)
            load_hdf5.meta_data = buff_meta_data

        return load_hdf5
