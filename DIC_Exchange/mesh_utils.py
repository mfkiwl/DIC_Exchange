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
import time

import numpy as np

def node_surface_normal(mesh, coords):
    nodes = np.arange(coords.shape[1])

    node_connection = dict()
    for a_node in nodes:
        is_in_el = np.sum(np.isin(mesh, a_node), axis=1, dtype=bool)
        node_connection[a_node] = np.unique(mesh[is_in_el])

    n_ts, n_node, _ = coords.shape

    matrix = []

    for i_node in range(n_node):
        points = [coords[:, i_node, :], ]
        for a_node in node_connection[i_node]:
            points.append(coords[:, a_node, :])
        points = np.array(points)
        center = np.mean(points, axis=0)
        points = points - center
        points = points.swapaxes(0,1)

        matrix_series = np.matmul(points.swapaxes(-1, 1), points)
        matrix.append(matrix_series)

    matrix = np.array(matrix)

    u, d, vh = np.linalg.svd(matrix, hermitian=True)
    normals = u[:, :, :, -1].swapaxes(0,1)

    norm = np.linalg.norm(normals, axis=-1)
    normals[:, :, 0] /= norm
    normals[:, :, 1] /= norm
    normals[:, :, 2] /= norm

    return normals


def mesh_boundaries(mesh: "np.ndarray(shape=q, 3)") -> list:
    """
    Find the boundaries of a given mesh
    :param "np.ndarray(shape=q, 3)" mesh: array representing the mesh indexes (with q elements)
    :return: unique half edges of the mesh (boundaries)
    """
    unique_half_edges = []
    for el in mesh:

        half_edges = [frozenset({el[0], el[1]}),
                      frozenset({el[1], el[2]}),
                      frozenset({el[0], el[2]})]

        for an_half_edge in half_edges:
            if an_half_edge in unique_half_edges:
                unique_half_edges.remove(an_half_edge)
            else:
                unique_half_edges.append(an_half_edge)
    return unique_half_edges


def mesh_holes(mesh: "np.ndarray(shape=q, 3)") -> list[list]:
    """
    Find closed boundaries in the mesh, usualy DIC results have one continuous boundary plus one for every hole.
    :param "np.ndarray(shape=q, 3)" mesh: array representing the mesh indexes (with q elements)
    :return: list of continuous boundary segment
    """
    unique_half_edges = mesh_boundaries(mesh)
    holes = []
    unique_half_edges_set = set(unique_half_edges)
    while len(unique_half_edges_set) != 0:
        buff_hole = []
        start_link = list(unique_half_edges_set.pop())
        buff_hole.append(start_link)
        next_summit = start_link[1]
        end_summit = start_link[0]
        link_running = True

        while link_running:
            unique_half_edges_set_to_remove = []
            for an_half_edges in unique_half_edges_set:
                if next_summit in an_half_edges:
                    an_half_edges_l = list(an_half_edges)
                    unique_half_edges_set_to_remove.append(an_half_edges)

                    if an_half_edges_l[0] == next_summit:
                        next_summit = an_half_edges_l[1]
                        buff_hole.append(an_half_edges_l)
                    else:
                        next_summit = an_half_edges_l[0]
                        buff_hole.append(an_half_edges_l[::-1])

                    if end_summit in an_half_edges:
                        link_running = False
                        break
            for an_half_edges_to_remove in unique_half_edges_set_to_remove:
                unique_half_edges_set.remove(an_half_edges_to_remove)

        holes.append(buff_hole)
        return holes


def has_mesh_hole(mesh: "np.ndarray(shape=q, 3)") -> bool:
    """
    Test if the mesh have more than one contineous boundary
    :param "np.ndarray(shape=q, 3)" mesh: array representing the mesh indexes (with q elements)
    :return bool: boolean True if the mesh has only one continuous boundary
    """
    holes = mesh_holes(mesh)
    return len(holes) > 1
