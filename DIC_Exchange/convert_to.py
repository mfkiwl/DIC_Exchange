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

import DIC_Exchange.HDF5Exchange
from DIC_Exchange import parsers
import numpy as np


def load_from(path: str, file_type: str = "ARAMIS_XML",
              thinning: int = None, last_time_step: int = None, first_timestep: int = None,
              force_rupture_ratio: float = None, offset_force_rupture_ratio: int = 0,
              force_max: float = None, offset_force_max: int = 0,
              force_min: float = None, offset_force_min: int = 0,
              time_min: float = None, offset_time_min: int = 0,
              time_max: float = None, offset_time_max: int = 0,
              verbose: bool = False):

    if file_type == "ARAMIS_XML":
        coords, strains, force, time, mesh = parsers.ARAMIS_XML_Parser.parse(path_xml=path, verbose=verbose)
    else:
        raise NotImplementedError("No Parser for file_type="+file_type)

    the_first_time_step = 0
    the_last_time_step = len(coords.keys())

    force_values = np.array(list(force.values()))
    time_values = np.array(list(time.values()))

    if last_time_step is not None:
        the_last_time_step = min(last_time_step, the_last_time_step)

    if first_timestep is not None:
        the_first_time_step = max(first_timestep, the_first_time_step)

    if force_rupture_ratio is not None:
        threshold = force_rupture_ratio * force_values.max()
        rupture = np.max(np.where(force_values >= threshold))
        rupture += offset_force_rupture_ratio
        the_last_time_step = min(rupture, the_last_time_step)

    if force_max is not None:
        threshold = force_max
        rupture = np.max(np.where(force_values <= threshold))
        rupture += offset_force_max
        the_last_time_step = min(rupture, the_last_time_step)

    if force_min is not None:
        threshold = force_min
        rupture = np.min(np.where(force_values >= threshold))
        rupture += offset_force_min
        the_first_time_step = max(rupture, the_first_time_step)

    if time_min is not None:
        threshold = time_min
        start_time = np.min(np.where(time_values >= threshold))
        start_time += offset_time_min
        the_first_time_step = max(start_time, the_first_time_step)

    if time_max is not None:
        threshold = time_max
        stop_time = np.min(np.where(time_values >= threshold))
        stop_time += offset_time_max
        the_last_time_step = min(stop_time, the_last_time_step)

    coords_a, strains_a, force_a, time_a, mesh_a = _numpyfi(coords, strains, force, time, mesh,
                                                            fstep=the_first_time_step,
                                                            lstep=the_last_time_step, step=thinning)

    return DIC_Exchange.HDF5Exchange.DIC_Result(coords_a, strains_a, force_a, time_a, mesh_a)


def _numpyfi(coords_o, strains_o, force_o, time_o, mesh_o, fstep=0, lstep=-1, step=1):
    # get_the set of element

    list_stage = list(time_o.keys())
    list_stage = list_stage[fstep:lstep:step]
    element_set = set(coords_o[list_stage[0]].keys())
    for a_stage in list_stage:
        a_coord = coords_o[a_stage]
        element_set = element_set.intersection(set(a_coord.keys()))

    element_set = list(element_set)  # order preservation

    # clean the mesh
    mesh_buff = []
    for el in mesh_o:
        if all([el[i] in element_set for i in range(3)]):
            mesh_buff.append([element_set.index(el[i]) for i in range(3)])
    mesh = np.array(mesh_buff)

    element_set = list(element_set)
    # stacking the coordinates
    coords_np = []
    for a_stage in list_stage:
        buff_coords = []
        for a_el in element_set:
            buff_coords.append(coords_o[a_stage][a_el])
        coords_np.append(buff_coords)
    coords = np.array(coords_np)

    # stacking the strains
    strains_np = []
    for a_stage in list_stage:

        buff = []
        for a_el in element_set:
            buff.append(np.array([strains_o["eps_xx"][a_stage][a_el],
                                  strains_o["eps_yy"][a_stage][a_el],
                                  strains_o["eps_xx"][a_stage][a_el]]))
        strains_np.append(buff)
    strains = np.array(strains_np)[:, :, :, 0]

    # turn force and time in arrays
    time = []
    force = []
    for a_stage in list_stage:
        time.append(time_o[a_stage])
        force.append(force_o[a_stage])

    time = np.array(time)
    force = np.array(force)

    return coords, strains, force, time, mesh
