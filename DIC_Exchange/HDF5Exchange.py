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
from typing import NoReturn
from DIC_Exchange import mesh_utils


class DIC_Result:
    """
    Class providing the data models and input output methods for handling DIC results for material testing
    """

    def __init__(self, coords: np.ndarray, strains: np.ndarray, force: np.ndarray, time: np.ndarray, mesh: np.ndarray, node_normal:np.ndarray=None):
        """
        Initiating a DIC_Result object, vectorize or not,
        with n timestep, m points and q elements
        :param np.ndarray coords: coordinate array of shape (n,m,3) in order x,y,z
        :param np.ndarray strains: strains array of shape (n,m,3) in order (e_xx, e_yy, e_xy)
        :param np.ndarray force: time series of the force in an array (n,)
        :param np.ndarray time: value of the time in an array (n,)
        :param np.ndarray mesh: mesh represented by an array of shape (q, 3) with the value corresponding to coords and strains
        :param np.ndarray node_normal: local normal at node, will be computed if not provided
        """


        assert isinstance(coords, np.ndarray)
        assert isinstance(strains, np.ndarray)
        assert isinstance(coords, np.ndarray)
        assert isinstance(force, np.ndarray)
        assert isinstance(time, np.ndarray)
        assert isinstance(mesh, np.ndarray)
        assert isinstance(mesh, np.ndarray) or mesh is None

        self.strains = strains
        """Strains array shape=(n_timesteps, n_points, [eps_xx, eps_yy, eps_xy])"""
        self.coords = coords
        """Coordinate array shape=(n_timesteps, n_points, [x, y, z])"""
        self.force = force
        """Value of the force as an array shape=(n_timesteps,)"""
        self.time = time
        """Value of the time as an array shape=(n_timesteps,)"""
        self._mesh = mesh
        """private attribute containing the mesh"""

        self.meta_data = {"version": "0.1"}
        """Some metadata which are accesible to the users and can will be written in the file"""

        self.node_normals = node_normal
        if self.node_normals is None:
            self._compute_node_normal()
        """normal to the surface at the node coordinnates, usefull to handle local coordinate systems"""

        self._init_mesh_property()

    def get_mesh(self):
        return self._mesh

    def set_mesh(self, mesh):
        self._mesh = mesh
        self._init_mesh_property()

    mesh = property(get_mesh, set_mesh, doc="""mesh array shape=(n_elements, 3)""")

    def _init_mesh_property(self):
        self.mesh_holes = mesh_utils.mesh_holes(self._mesh)
        self.has_mesh_holes = len(self.mesh_holes) > 1

    def _compute_node_normal(self):
        self.node_normals = mesh_utils.node_surface_normal(self._mesh, self.coords)

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
            hdf5["scalar"].create_dataset("force", data=self.force)

            # Saving the vector information
            hdf5.create_group("vector")
            hdf5["vector"].create_dataset("strains", data=self.strains)
            hdf5["vector"].create_dataset("coordinates", data=self.coords)
            hdf5["vector"].create_dataset("node_normals", data=self.node_normals)

            # Saving the mesh
            hdf5.create_dataset("mesh", data=self._mesh)

    @classmethod
    def load_from_hdf5(cls, path: str) -> "DIC_Result":
        """
        Load a hdf5 file representing an DIC_Result object
        :param str path: path of the file to write
        :return DIC_Result: content of the hdf5 file in a DIC_Result object
        """

        with h5py.File(path, "r") as h5file:
            # read meta data

            buff_meta_data = {}

            for el in h5file.attrs:
                buff_meta_data[el] = h5file.attrs[el]

            # read scalar

            force = np.array(h5file["scalar"]["time"])
            time = np.array(h5file["scalar"]["force"])

            # read vector
            coords = np.array(h5file["vector"]["coordinates"])
            strains = np.array(h5file["vector"]["strains"])
            try:
                node_normals = np.array(h5file["vector"]["node_normals"])
            except KeyError:
                node_normals = None

            # read mesh
            mesh = np.array(h5file["mesh"])

            load_hdf5 = cls(coords, strains, force, time, mesh, node_normals)
            load_hdf5.meta_data = buff_meta_data

        return load_hdf5

    def __getitem__(self, item: str) -> np.ndarray:

        """
        Get specific value of strain or coords
        :param item:
        :return:
        """

        if type(item) == str:
            if "eps" in item:
                # strain
                if item == "eps":
                    return self.strains
                elif item == "eps_xx":
                    return self.strains[:, :, 0]
                elif item == "eps_yy":
                    return self.strains[:, :, 1]
                elif item == "eps_xy":
                    return self.strains[:, :, 2]
                elif item == "eps_1":
                    return self.get_principal_strains(which=1)
                elif item == "eps_2":
                    return self.get_principal_strains(which=2)
            elif item == "x":
                return self.coords[:, :, 0]
            elif item == "y":
                return self.coords[:, :, 1]
            elif item == "z":
                return self.coords[:, :, 2]
            elif item == "force":
                return self.force
            elif item == "time":
                return self.time
        raise KeyError(str(item) + " is not a valuable key")

    def get_principal_strains(self, which: int = 1) -> np.ndarray:
        """
        Compute the principal strain
        :param int which: 1 or 2 to get first or second principal strain
        :return: computed principal strain
        """
        if which == 1:
            return (self.strains[:, :, 0] + self.strains[:, :, 1]) / 2 + \
            np.sqrt(((self.strains[:, :, 0] + self.strains[:, :, 1]) ** 2) / 2 - self.strains[:, :, 2] ** 2)
        elif which == 2:
            return (self.strains[:, :, 0] + self.strains[:, :, 1]) / 2 - \
            np.sqrt(((self.strains[:, :, 0] + self.strains[:, :, 1]) ** 2) / 2 - self.strains[:, :, 2] ** 2)
        else:
            raise KeyError("There are only two principal strain, 1 and 2")

    def translate(self, vector: "np.ndarray(shape=(3,))") -> NoReturn:
        """
        Translate the coordinate system
        :param np.ndarray vector: translation vector
        """

        self.coords + vector


    def rotate(self, matrix: 'np.ndarray(shape=(3,3))'):
        """
        Translate the coordinate system
        :param np.ndarray matrix: rotation matrix
        """

        # rotating the coordinate is just a matrix product
        self.coords = np.einsum("ik, ...k->...i", matrix, self.coords)

        # However rotating the strain is more complicated because the strain
        # must be computed in the local coordinate system
        old_e_x = np.cross(self.node_normals, np.array([0, 1, 0]), axis=-1)
        norm_old_e_x = np.linalg.norm(old_e_x, axis=-1)
        old_e_x[:, :, 0] /= norm_old_e_x
        old_e_x[:, :, 1] /= norm_old_e_x
        old_e_x[:, :, 2] /= norm_old_e_x
        new_e_x = np.einsum("ik, ...k -> ...i", matrix, old_e_x)

        cos_th = np.einsum("...i, ...i -> ...", old_e_x, new_e_x)

        cp_e_x = np.cross(old_e_x, new_e_x, axis=-1)
        sgn_th = np.sign(np.einsum("...i, ...j -> ...", cp_e_x, self.node_normals))
        sin_th = np.linalg.norm(cp_e_x, axis=-1) * sgn_th

        new_strains = np.zeros_like(self.strains)
        new_strains[:, :, 0] = self.strains[:, :, 0]*cos_th**2 \
                               + self.strains[:, :, 1]*sin_th**2 \
                               + self.strains[:, :, 2]*sin_th*cos_th

        new_strains[:, :, 1] = self.strains[:, :, 0]*sin_th**2 \
                               + self.strains[:, :, 1]*cos_th**2 \
                               - self.strains[:, :, 2]*sin_th*cos_th

        new_strains[:, :, 2] = 2*(self.strains[:, :, 0] - self.strains[:, :, 1])*sin_th*cos_th \
                               + self.strains[:, :, 2]*(cos_th**2 - sin_th**2)

        self.strains = new_strains
        self.node_normals = np.einsum("ik, ...k -> ...i", matrix, self.node_normals)
