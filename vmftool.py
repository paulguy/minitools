#!/usr/bin/env python3

import io
import sys
import pathlib
from typing import Optional
from enum import Enum, auto
from dataclasses import dataclass
from collections import namedtuple
import pprint
import copy
import itertools
from math import pi, tau, sin, cos, tan, hypot

DEFAULT_MATERIAL = "BLACK_OUTLINE"

DEFAULT_VERSIONINFO : dict[str, str | list] = {
	"editorversion": "400",
	"editorbuild": "8870",
	"mapversion": "0",
	"formatversion": "100",
	"prefab": "0"
}

DEFAULT_WORLD : dict[str, str | list] = {
	"id": "1",
	"mapversion": "1",
	"classname": "worldspawn",
	"detailmaterial": "detail/detailsprites",
	"detailvbsp": "detail.vbsp",
	"maxpropscreenwidth": "-1",
	"skyname": "sky_day01_01"
}
	
DEFAULT_SIDE : dict[str, str | list] = {
    "uaxis": "[1 0 0 0] 0.25",
    "vaxis": "[0 -1 0 0] 0.25",
    "rotation": "0",
    "lightmapscale": "16",
    "smoothing_groups": "0",
}

class SourceObjectType(Enum):
    CLASS = auto()
    PROPERTY = auto()

class SourceFile:
    def __init__(self, inpath : pathlib.Path):
        self.infile : io.TextIOBase = inpath.open('r')
        self.curline : list[str] = []

    def __del__(self):
        self.infile.close()

    @staticmethod
    def splitline(line : str):
        # like normal str.split() but keeps quoted strings together
        line = line.strip()

        parts = []
        pos = 0
        quoted : bool = False
        if line[0] == '\"':
            quoted = True
        
        while pos < len(line):
            if quoted:
                try:
                    qindex = line[pos+1:].index('\"')
                except ValueError:
                    parts.append(line[pos:])
                    return parts

                parts.append(line[pos:pos+qindex+2])
                pos += qindex + 2
                quoted = False
            else:
                try:
                    qindex = line[pos:].index('\"')
                except ValueError:
                    parts.extend(line[pos:].split())
                    return parts

                parts.extend(line[pos:pos+qindex].split())
                pos += qindex
                quoted = True

        if len(parts) == 0:
            return [line]
        
        return parts

    def try_refill(self):
        while len(self.curline) == 0:
            line = self.infile.readline()
            if len(line) == 0:
               raise EOFError
            self.curline = SourceFile.splitline(line)

    def split_from_line(self, start : str) -> Optional[str]:
        try:
            self.try_refill()
        except EOFError:
            return None
        nextsym : str = self.curline[0]
        if nextsym.startswith(start):
            self.curline[0] = self.curline[0].removeprefix(start)
            if len(self.curline[0]) == 0:
                self.curline.pop(0)
            return start

        try:
            lbindex = nextsym.index(start)
            # return the rest of the string to the start
            if lbindex < len(nextsym) - 1:
                self.curline[0] = nextsym[lbindex+1:]
            nextsym = nextsym[:lbindex]
        except ValueError:
            return None

        return nextsym

    def get_next(self) -> Optional[str]:
        nextsym = self.split_from_line('{')
        if nextsym is None:
            nextsym = self.split_from_line('}')
        if nextsym is None:
            try:
                self.try_refill()
            except EOFError:
                return None
            nextsym = self.curline.pop(0)

        return nextsym

    def get_next_object(self) -> Optional[tuple[SourceObjectType, Optional[str], Optional[str]]]:
        nextsym = self.get_next()
        if nextsym is None:
            return None
        if nextsym[0] == '\"':
            if len(nextsym) < 2 or nextsym[-1] != '\"':
                raise ValueError("Malformed property name")
            propval = self.get_next()
            if propval is None or propval[0] != '\"' or propval[-1] != '\"':
                raise ValueError("Malformed property value")
            return SourceObjectType.PROPERTY, nextsym[1:-1], propval[1:-1]
        elif nextsym == '}':
            return SourceObjectType.CLASS, None, None
        else:
            brace = self.get_next()
            if brace != '{':
                raise ValueError("Class name with no class.")
            return SourceObjectType.CLASS, nextsym, None

    def __iter__(self):
        return self

    def __next__(self):
        next_object = self.get_next_object()
        if next_object is None:
            raise StopIteration
        return next_object

    def load(self) -> dict[str, str | list]:
        # use key/value tuple pairs because classes may appear multiple times
        # and they don't generally provide a name
        ret : dict[str, str | list] = {}
        stack : list[dict] = [ret]

        for objtype, ret1, ret2 in self:
            if objtype == SourceObjectType.PROPERTY:
                stack[-1][ret1] = ret2
            else: # class
                if ret1 is not None:
                    newclass : dict[str, str | list] = {}
                    if ret1 not in stack[-1]:
                        stack[-1][ret1] = []
                    stack[-1][ret1].append(newclass)
                    stack.append(newclass)
                else:
                    stack = stack[:-1]
        
        return ret

    @staticmethod
    def get_value(data : dict[str, str | list],
                  key : str):
        for item in data:
            if item[0] == key:
                return item[1]
        
        raise KeyError(f"Key not found \"{key}\"")

    @staticmethod
    def dumpclass(data : dict[str, str | list],
                  level : int = 0):
        pad = ''.rjust(level, '\t')
        ret = ""

        for item in data.keys():
            if isinstance(data[item], str):
                ret += f"{pad}\"{item}\" \"{data[item]}\"\n"
            else:
                for item2 in data[item]:
                    ret += f"{pad}{item}\n"
                    ret += pad
                    ret += '{\n'
                    ret += SourceFile.dumpclass(item2, level + 1)
                    ret += pad
                    ret += '}\n'

        return ret

    @staticmethod
    def dump(data : dict[str, str | list]) -> str:
        return SourceFile.dumpclass(data)

Point2 = namedtuple('Point2', ['x', 'y'])
Point3 = namedtuple('Point3', ['x', 'y', 'z'])
UVPoint = namedtuple('UVPoint', ['u_x', 'u_y', 'u_z', 'u_translate', 'u_scale',
                                 'v_x', 'v_y', 'v_z', 'v_translate', 'v_scale'])

def translate(point : Point3,
              pos : Point3) -> Point3:
    return Point3(point.x + pos.x, point.y + pos.y, point.z + pos.z)

def rotate(point : Point3,
            angles : Point3) -> Point3:
    #  1  0          0
    #  0  cos(a_x)  -sin(a_x)
    #  0  sin(a_x)   cos(a_x)

    #  cos(a_y)  0  sin(a_y)
    #  0         1  0
    # -sin(a_y)  0  cos(a_y)

    #  cos(a_y)              0          sin(a_y)
    #  (sin(a_x))(sin(a_y))  cos(a_x)  -(sin(a_x))(cos(a_y))
    # -(cos(a_x))(sin(a_y))  sin(a_x)   (cos(a_x))(cos(a_y))

    #  cos(a_z)  -sin(a_z)  0
    #  sin(a_z)   cos(a_z)  0
    #  0          0         1

    #  (cos(a_y))(cos(a_z))                                 -(cos(a_y))(sin(a_z))                                  sin(a_y)
    #  (sin(a_x))(sin(a_y))(cos(a_z))+(cos(a_x))(sin(a_z))  -(sin(a_x))(sin(a_y))(sin(a_z))+(cos(a_x))(cos(a_z))  -(sin(a_x))(cos(a_y))
    # -(cos(a_x))(sin(a_y))(cos(a_z))+(sin(a_x))(sin(a_z))   (cos(a_x))(sin(a_y))(sin(a_z))+(sin(a_x))(cos(a_z))   (cos(a_x))(cos(a_y))
    # TODO this is broken
    return Point3( (point.x * cos(angles.x) * cos(angles.z))
                  +(point.y * sin(angles.x) * sin(angles.y) * sin(angles.z)) + (point.y * cos(angles.x) * sin(angles.z))
                  -(point.z * cos(angles.x) * sin(angles.y) * cos(angles.z)) + (point.z * sin(angles.x) * sin(angles.z)),
                  -(point.x * cos(angles.y) * sin(angles.z)) \
                  -(point.y * sin(angles.x) * sin(angles.y) * sin(angles.z)) + (point.y * cos(angles.x) * cos(angles.z))
                  -(point.z * cos(angles.x) * sin(angles.y) * sin(angles.z)) + (point.z * sin(angles.x) * cos(angles.z)),
                   (point.x * sin(angles.y))
                  -(point.y * sin(angles.x) * cos(angles.y))
                  +(point.z * cos(angles.x) * cos(angles.y)))

def gen_polygon(sides : int, 
                radius : float) -> list[Point2]:
    point_distance : float = hypot(tan(tau / sides / 2.0), 1.0) * radius
    points : list[Point2] = []
    for i in range(sides):
        x : float = sin((float(i) - 0.5) / float(sides) * tau)
        y : float = cos((float(i) - 0.5) / float(sides) * tau)
        points.append(Point2(x * point_distance, y * point_distance))

    return points

class Shape:
    points : list[Point2]
    uvs : list[UVPoint]
    materials : list[str]
    thickness : float
    top_angle : float
    bottom_angle : float
    children : list["Shape"]

    TOP_INDEX = 0
    BOTTOM_INDEX = 1
    SIDE_INDEX = 2

    def __init__(self, points : list[Point2],
                       thickness : float,
                       pos : Point3 = Point3(0.0, 0.0, 0.0),
                       angle : Point3 = Point3(0.0, 0.0, 0.0),
                       uvs : Optional[list[UVPoint]] = None,
                       materials : Optional[list[str]] = None,
                       top_angle : float = 0.0,
                       bottom_angle : float = 0.0):
        self.points = points
        self.thickness = thickness
        self.pos = pos
        self.angle = angle
        # TODO top/bottom angle UVs
        if uvs is None:
            uvs = [UVPoint(1.0, 0.0, 0.0, 0.0, 1.0,
                           0.0, 1.0, 0.0, 0.0, 1.0),
                   UVPoint(1.0, 0.0, 0.0, 0.0, 1.0,
                           0.0, 1.0, 0.0, 0.0, 1.0)]
            for i in range(len(points)):
                p1 : Point2 = points[(i+1)%len(points)]
                p2 : Point2 = points[i]
                xdiff : float = p2.x - p1.x
                ydiff : float = p2.y - p1.y
                maxdiff : float = max(abs(xdiff), abs(ydiff))
                uvs.append(UVPoint(xdiff / maxdiff, ydiff / maxdiff, 0.0, 0.0, 1.0,
                                   0.0, 0.0, 1.0, 0.0, 1.0))
        self.uvs = uvs
        if materials is None:
            materials = list(itertools.repeat(DEFAULT_MATERIAL, len(points) + 2))
        self.materials = materials
        self.children = []

    def add_child(self, child : "Shape"):
        self.children.append(child)

    def set_one_material(self, idx : int, material : str):
        self.materials[idx] = material

    def set_all_materials(self, material : str):
        self.materials = list(itertools.repeat(material, len(self.points) + 2))

    def set_top_material(self, material : str):
        self.materials[Shape.TOP_INDEX] = material

    def set_bottom_material(self, material : str):
        self.materials[Shape.BOTTOM_INDEX] = material

    def set_side_material(self, idx : int, material : str):
        self.materials[idx - Shape.SIDE_INDEX] = material

    def set_all_side_materials(self, material : str):
        self.materials[2:] = list(itertools.repeat(material, len(self.points)))

    @staticmethod
    def make_sideclass(side_id : int,
                       p1 : Point3,
                       p2 : Point3,
                       p3 : Point3,
                       uv : UVPoint,
                       material : str) -> dict[str, str | list]:
            sideclass : dict[str, str | list] = copy.copy(DEFAULT_SIDE)
            sideclass['id'] = str(side_id)
            sideclass['plane'] = f"({p1.x:.3f} {p1.y:.3f} {p1.z:.3f}) " \
                                 f"({p2.x:.3f} {p2.y:.3f} {p2.z:.3f}) " \
                                 f"({p3.x:.3f} {p3.y:.3f} {p3.z:.3f})"
            sideclass['material'] = material
            sideclass['uaxis'] = f"[{uv.u_x:.3f} {uv.u_y:.3f} {uv.u_z:.3f} {uv.u_translate:.3f}] {uv.u_scale:.3f}"
            sideclass['vaxis'] = f"[{uv.v_x:.3f} {uv.v_y:.3f} {uv.v_z:.3f} {uv.v_translate:.3f}] {uv.v_scale:.3f}"
            return sideclass

    def to_dict(self, ids : list[int]) -> list[dict[str, str | list]]:
        # TODO wedges
        # TODO split concave shapes
        shapeclasses : list[dict[str, str | list]] = []
        shapeclass : dict[str, str | list] = {}
        shapeclass['id'] = str(ids[0])
        ids[0] += 1
        sides : list[dict] = []
        shapeclass['side'] = sides
        # TODO select sequential points which don't all share a point on an axis
        p1 : Point3 = translate(rotate(Point3(self.points[0].x, self.points[0].y, self.thickness / 2.0), self.angle), self.pos)
        p2 : Point3 = translate(rotate(Point3(self.points[1].x, self.points[1].y, self.thickness / 2.0), self.angle), self.pos)
        p3 : Point3 = translate(rotate(Point3(self.points[2].x, self.points[2].y, self.thickness / 2.0), self.angle), self.pos)
        sides.append(Shape.make_sideclass(ids[1],
                                          p1, p2, p3,
                                          self.uvs[Shape.TOP_INDEX],
                                          self.materials[Shape.TOP_INDEX]))
        ids[1] += 1
        p1 = translate(rotate(Point3(self.points[2].x, self.points[2].y, self.thickness / -2.0), self.angle), self.pos)
        p2 = translate(rotate(Point3(self.points[1].x, self.points[1].y, self.thickness / -2.0), self.angle), self.pos)
        p3 = translate(rotate(Point3(self.points[0].x, self.points[0].y, self.thickness / -2.0), self.angle), self.pos)
        sides.append(Shape.make_sideclass(ids[1],
                                          p1, p2, p3,
                                          self.uvs[Shape.BOTTOM_INDEX],
                                          self.materials[Shape.BOTTOM_INDEX]))
        ids[1] += 1
        for i in range(len(self.points)):
            i2 : int = (i+1)%len(self.points)
            p1 = translate(rotate(Point3(self.points[i2].x, self.points[i2].y, self.thickness / 2.0), self.angle), self.pos)
            p2 = translate(rotate(Point3(self.points[i].x, self.points[i].y, self.thickness / 2.0), self.angle), self.pos)
            p3 = translate(rotate(Point3(self.points[i].x, self.points[i].y, self.thickness / -2.0), self.angle), self.pos)
            sides.append(Shape.make_sideclass(ids[1],
                                              p1, p2, p3,
                                              self.uvs[Shape.SIDE_INDEX + i],
                                              self.materials[Shape.SIDE_INDEX + i]))
            ids[1] += 1
        shapeclasses.append(shapeclass)
        # TODO figure out passing on parent transforms relative to center or face to children
        for child in self.children:
            shapeclasses.extend(child.to_dict(ids))
        return shapeclasses

class VMF:
    def __init__(self) -> None:
        self.shapes : list[Shape] = []

    def add_shape(self, shape : Shape):
        self.shapes.append(shape)

    def generate(self) -> str:
        # world is class ID 1
        ids = [2, 1]
        root : dict[str, str | list] = {}
        root['versioninfo'] = [copy.copy(DEFAULT_VERSIONINFO)]
        root['world'] = [copy.copy(DEFAULT_WORLD)]
        solids = []
        root['world'][0]['solid'] = solids
        for shape in self.shapes:
            solids.extend(shape.to_dict(ids))
        return SourceFile.dump(root)

def main(args : list[str]):
    #d = SourceFile(pathlib.Path(args[0])).load()
    v = VMF()

    materials : list[str] = list(itertools.repeat("brick/brickwall026f", 10))
    materials[0] = "concrete/concretefloor033a"
    materials[1] = "concrete/concretefloor033a"
    shape : Shape = Shape(gen_polygon(8, 1024.0),
                          16.0,
                          materials=materials)
    shape.add_child(Shape(gen_polygon(8, 1024.0),
                          16.0,
                          pos=Point3(0.0, 0.0, 256.0),
                          materials=materials))
    materials = list(itertools.repeat("brick/brickwall026f", 6))
    shape.add_child(Shape(gen_polygon(4, 256.0),
                          16.0,
                          pos=Point3(724.0775, 724.0775, 128.0),
                          materials=materials))
    v.add_shape(shape)
    print(v.generate())

    return

if __name__ == '__main__':
    main(sys.argv[1:])