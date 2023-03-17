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

import struct
import base64
import numpy as np
import warnings
import xml.etree.ElementTree as ET
import re
from abc import ABC

import logging


class ABC_parser(ABC):
    @classmethod
    def parse(cls, path):
        raise NotImplementedError


#### DICE Parser

class DICe_Parser(ABC_parser):
    @classmethod
    def parse(cls, path):
        raise RuntimeError


#### Aramis Parser

MAX_UINT = 2 ** 32 - 1
LEN_INT = struct.calcsize("<I")
LEN_DOUBLE = struct.calcsize("<d")
LEN_CHAR = struct.calcsize("<c")
LEN_FLOAT = struct.calcsize("<f")


class ARAMIS_XML_Parser:
    """
    Parser for XML Aramis binary output file
    """
    version = 0.1

    @classmethod
    def parse(csl, path_xml):

        logging.debug("start reading XML data")
        header_read, nominal_read, measured_read = read_file(path_xml)
        logging.debug("start writing hdf5")

        rel_time = []
        stage_id = []
        stage_name = []

        length_unit_factor, time_unit_factor, angle_unit_factor, force_unit_factor = header_read[1]

        """For not unis factor ar not in use"""

        for stage in header_read[0]:
            rel_time.append(float(stage["rel_time"]))
            stage_name.append(str(stage["name"]))
            stage_id.append(stage["id"])

        triangle, geometry = measured_read

        comparison_surface_list, dimension_list = nominal_read
        force_values = [float(dimension_list[0][i][1]) for i in range(len(dimension_list[0]))]

        list_epsilon = list(comparison_surface_list.keys())

        eps_xx_key = None
        eps_yy_key = None
        eps_xy_key = None

        re_epx_xy = "^.*epsXY.*$"
        re_eps_xx = "^.*epsX.*$"
        re_eps_yy = "^.*epsY.*$"

        for i in range(3):
            if re.match(re_epx_xy, list_epsilon[i]):
                eps_xy_key = i
                break

        for i in range(3):
            if re.match(re_eps_yy, list_epsilon[i]):
                eps_yy_key = i
                break

        for i in range(3):
            if re.match(re_eps_xx, list_epsilon[i]):
                if not re.match(re_epx_xy, list_epsilon[i]):
                    eps_xx_key = i
                    break

        force = dict(zip(stage_id, force_values))
        time = dict(zip(stage_id, rel_time))

        mesh = np.array(triangle)

        coords = geometry
        strains = dict()

        strains["eps_xx"] = comparison_surface_list[list_epsilon[eps_xx_key]]
        strains["eps_yy"] = comparison_surface_list[list_epsilon[eps_yy_key]]
        strains["eps_xy"] = comparison_surface_list[list_epsilon[eps_xy_key]]

        logging.debug("Done parsing xml")

        return coords, strains, force, time, mesh


def read_file(path):
    tree = ET.parse(path)
    root = tree.getroot()

    header_read, nominal_read, measured_read = None, None, None

    for an_el in root:
        if an_el.tag == "header":
            logging.debug("start reading header")
            header_el = an_el
            header_read = read_header(header_el)
            logging.debug("done reading header")
        elif an_el.tag == "nominal":
            logging.debug("start reading nominal")
            nominal_el = an_el
            nominal_read = read_nominal(nominal_el)
            logging.debug("done reading nominal")
        elif an_el.tag == "measured":
            logging.debug("start reading measured")
            measured_el = an_el
            measured_read = read_measured(measured_el)
            logging.debug("done reading measured")

    logging.debug("done reading file")

    return header_read, nominal_read, measured_read


def read_nominal(nominal_el):
    comparison_surface_list = dict()
    dimension_list = []
    for an_el in nominal_el:
        if an_el.tag == "comparison_surface_component":
            surf_comp_name = an_el.attrib["name"]
            buff_surf_comp = {}
            for under_el in an_el:
                if under_el.tag == "actual":
                    pass
                elif under_el.tag == "stage":
                    buff_surf_comp[under_el.attrib["id"]] = None
                elif under_el.tag == "result":
                    for u_u_el in under_el:
                        if u_u_el.tag == "stage":
                            the_id = u_u_el.attrib["id"]
                            if the_id in buff_surf_comp.keys():
                                bytes_b64 = ""
                                for chunk in u_u_el:
                                    bytes_b64 += chunk.text
                                buff_surf_comp[the_id] = read_surface_component_scalar(bytes_b64)
                            else:
                                raise ValueError(
                                    "Invalid stage in results of comparison surface component " + str(surf_comp_name))
                elif under_el.tag == "strain_semantic":
                    pass
                else:
                    logging.error(under_el)
                    raise ValueError("Uknnown element in comparison surface component  " + str(surf_comp_name))
            comparison_surface_list[surf_comp_name] = buff_surf_comp
        elif an_el.tag == "dimension":
            buff_dimension = []
            for under_el in an_el:
                if under_el.tag == "result":
                    for u_u_el in under_el:
                        if u_u_el.tag == "stage":
                            buff_time = float(u_u_el.attrib["rel_time"])
                            buff_force = float(u_u_el[0][2].attrib["value"])
                        buff_dimension.append((buff_time, buff_force))
            dimension_list.append(buff_dimension)
    return comparison_surface_list, dimension_list


def read_header(header_el):
    stages_list = []
    for an_el in header_el:

        if an_el.tag == "version":
            logging.info("Version of the XML file is " + an_el.text)

        elif an_el.tag == "length_unit":
            logging.info("Length unit of the document is " + an_el.text)
            if an_el.text == "mm":
                length_unit_factor = 1
            else:
                raise ValueError("Unknown length unit format")

        elif an_el.tag == "time_unit":
            logging.info("Time unit of the document is " + an_el.text)
            if an_el.text == "s":
                time_unit_factor = 1
            else:
                raise ValueError("Unknown time unit format")

        elif an_el.tag == "force_unit":
            logging.info("Force unit of the document is " + an_el.text)
            if an_el.text == "N":
                force_unit_factor = 1
            elif an_el.text == "kN":
                force_unit_factor = 1e3
            else:
                raise ValueError("Unknown force unit format")

        elif an_el.tag == "angle_unit":
            logging.info("Angle unit of the document is " + an_el.text)
            if an_el.text == "deg":
                angle_unit_factor = 1
            elif an_el.text == "rad":
                angle_unit_factor = 2 * np.pi / 360
            else:
                raise ValueError("Unknown angle unit format")

        elif an_el.tag == "stage":
            stages_list.append(an_el.attrib)
        else:
            raise ValueError("Unknown element in Header")

    logging.debug("Found {the_len} stage(s)".format(the_len=len(stages_list)))

    return stages_list, (length_unit_factor, time_unit_factor, angle_unit_factor, force_unit_factor)


def read_measured(measured_el):
    buff_triangle = None
    buff_stages_surface = dict()
    for el in measured_el[0]:
        if el.tag == "triangles":
            buff_triangle = read_surface_component_triangles(el.text)
        elif el.tag == "stage":
            buff_stages_surface[el.attrib["id"]] = read_surface_component_vertices(el[1][0].text)
    return buff_triangle, buff_stages_surface


def read_surface_component_scalar(string_binary):
    base64_bytes = string_binary.encode('utf-8')
    message_bytes = base64.b64decode(base64_bytes)
    off = 0
    version = struct.unpack("<I", message_bytes[:LEN_INT])[0]
    off += LEN_INT
    unit_name = None
    if version >= 1:
        len_string = struct.unpack("<I", message_bytes[off: off + LEN_INT])[0]
        off += LEN_INT
        unit_name = struct.unpack("<" + str(len_string) + "s",
                                  message_bytes[off: off + len_string * LEN_CHAR])[0].decode("latin-1")
        off += len_string * LEN_CHAR

    n_vertices = struct.unpack("<I", message_bytes[off: off + LEN_INT])[0]
    off += LEN_INT

    dire_vect_flag = 0
    if version >= 2:
        dire_vect_flag = struct.unpack("<B", message_bytes[off: off + LEN_CHAR])[0]
        off += LEN_CHAR

    indexes = []
    buff_scalar = {}
    buff_vector = {}
    for i in range(n_vertices):
        valid = struct.unpack("<B", message_bytes[off:off + LEN_CHAR])[0]
        off += LEN_CHAR
        if valid == 1:
            indexes.append(i)
            buff_scalar[i] = struct.unpack("<f", message_bytes[off:off + LEN_FLOAT])
            off += LEN_FLOAT
            if dire_vect_flag == 1:
                buff_vector[i] = struct.unpack("<fff", message_bytes[off:off + 3 * LEN_FLOAT])
                off += 3 * LEN_FLOAT
        elif valid == 0:
            continue
        else:
            raise RuntimeError("Error in decoding stage geometry, invalid Flag")

    if unit_name != 'log_strain':
        logging.warning("strain is not log strain, but " + unit_name)

    if dire_vect_flag == 1:
        return buff_scalar, buff_vector
    else:
        return buff_scalar


def read_surface_component_triangles(string_binary):
    base64_bytes = string_binary.encode('utf-8')
    message_bytes = base64.b64decode(base64_bytes)
    len(message_bytes)

    len_chain = len(message_bytes)
    n_triangle = int((len_chain - 2 * LEN_INT) / (3 * LEN_INT))
    triangle_unpack = struct.unpack("<II" + str(3 * n_triangle) + "I", message_bytes)
    triangle_buff = []
    for i in range(triangle_unpack[1]):
        triangle_buff.append((triangle_unpack[2 + i * 3],
                              triangle_unpack[2 + i * 3 + 1],
                              triangle_unpack[2 + i * 3 + 2],))

    return triangle_buff


def read_surface_component_vertices(string_binary):
    base64_bytes = string_binary.encode('utf-8')
    message_bytes = base64.b64decode(base64_bytes)
    offset_header = struct.calcsize("<I6dI")
    header = struct.unpack("<I6dI", message_bytes[:offset_header])
    min_corner = np.array(header[1:4])
    max_corner = np.array(header[4:7])
    n_vertices = header[-1]
    off = offset_header
    vertices_cords_i = []
    indexes = []
    for i in range(n_vertices):
        valid = struct.unpack("<B", message_bytes[off:off + 1])[0]
        off += 1
        if valid == 1:
            indexes.append(i)
            buff_vertices = struct.unpack("<III", message_bytes[off:off + 12])
            vertices_cords_i.append((buff_vertices[0],
                                     buff_vertices[1],
                                     buff_vertices[2]))
            off = off + 3 * LEN_INT
        elif valid == 0:
            continue
        else:
            raise RuntimeError("Error in decoding stage geometry, invalid Flag")

    if off != len(message_bytes):
        raise RuntimeError("Error in decoding stage geometry, invalid binary message length")

    vertices_cords_i = np.array(vertices_cords_i)
    vertices_cords_f = vertices_cords_i / MAX_UINT
    if n_vertices != 0:
        vertices_cords = np.array(
            [(max_corner[i] - min_corner[i]) * vertices_cords_f[:, i] + min_corner[i] for i in range(3)])

    vertices_dict = {}
    for i in range(len(indexes)):
        vertices_dict[indexes[i]] = vertices_cords[:, i]

    return vertices_dict
