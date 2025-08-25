#!/usr/bin/env python3

import io
import sys
import pathlib
from typing import Optional, Union
from enum import Enum, auto
from dataclasses import dataclass
from collections import namedtuple
import pprint
import copy
import itertools
from math import pi, tau, sin, cos, tan, hypot, atan2

F_PRECISION : int = 3
DEFAULT_MATERIAL = "BLACK_OUTLINE"

DEFAULT_VERSIONINFO : dict[str, str | list] = {
	"editorversion": "400",
	"editorbuild": "8870",
	"mapversion": "0",
	"formatversion": "100",
	"prefab": "0"
}

DEFAULT_WORLD : dict[str, str | list] = {
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

@dataclass
class Point2:
    x : float
    y : float

    def __add__(self, other : "Point2"):
        return Point2(self.x + other.x, self.y + other.y)

    def rotate2(self,
                angle : float) -> "Point2":
        return Point2((self.x * cos(angle)) - (self.y * sin(angle)),
                      (self.x * sin(angle)) + (self.y * cos(angle)))

@dataclass
class Point3:
    x : float
    y : float
    z : float

    def __add__(self, other : "Point3"):
        return Point3(self.x + other.x, self.y + other.y, self.z + other.z)

    def rotate(self,
               angle : "Point3") -> "Point3":
        if angle.x == 0.0 and angle.y == 0.0 and angle.z == 0.0:
            return self
        #  1  0          0
        #  0  cos(a_x)  -sin(a_x)
        #  0  sin(a_x)   cos(a_x)

        #  cos(a_y)  0  sin(a_y)
        #  0         1  0
        # -sin(a_y)  0  cos(a_y)

        #  cos(a_z)  -sin(a_z)  0
        #  sin(a_z)   cos(a_z)  0
        #  0          0         1
        point = Point3((self.x *  cos(angle.z)) + (self.y *  sin(angle.z)),
                       (self.x * -sin(angle.z)) + (self.y *  cos(angle.z)),
                        self.z)
        point = Point3((point.x *  cos(angle.y)) + (point.z * -sin(angle.y)),
                        point.y,
                       (point.x *  sin(angle.y)) + (point.z *  cos(angle.y)))
#        return  Point3( self.x,
#                       (self.y *  cos(angle.x)) + (self.z *  sin(angle.x)),
#                       (self.y * -sin(angle.x)) + (self.z *  cos(angle.x)))
        # calculate X rotation using Z matrix like some expect?  seems to make sense i guess.
        point = Point3((point.x *  cos(angle.x)) + (point.y *  sin(angle.x)),
                       (point.x * -sin(angle.x)) + (point.y *  cos(angle.x)),
                        point.z)
        return point

UVPoint = namedtuple('UVPoint', ('u_x', 'u_y', 'u_z', 'u_translate', 'u_scale',
                                 'v_x', 'v_y', 'v_z', 'v_translate', 'v_scale'))
class IDs:
    class_id : int
    side_id : int

    def __init__(self):
        self.class_id = 1
        self.side_id = 1

    def get_and_inc_class_id(self):
        class_id = self.class_id
        self.class_id += 1
        return class_id

    def get_and_inc_side_id(self):
        class_id = self.class_id
        self.class_id += 1
        return class_id

def gen_polygon(sides : int, 
                radius : float) -> list[Point2]:
    point_distance : float = hypot(tan(tau / sides / 2.0), 1.0) * radius
    points : list[Point2] = []
    for i in range(sides):
        # make a clockwise polygon starting at minimum Y and going along the X axis
        # so when sloped, the slope goes in some predictable way maybe
        x : float = -sin((float(i) - 0.5) / float(sides) * tau)
        y : float = -cos((float(i) - 0.5) / float(sides) * tau)
        points.append(Point2(x * point_distance, y * point_distance))

    return points

class Entity:
    origin : Point3

    def __init__(self, origin : Point3):
        self.origin = origin

    def make_own_dict(self, ids : IDs,
                            last_pos : Point3 = Point3(0.0, 0.0, 0.0),
                            last_angle : Point3 = Point3(0.0, 0.0, 0.0)) -> dict[str, str | list]:
        pos : Point3 = last_pos + self.origin
        return {"id": str(ids.get_and_inc_class_id()),
                "origin": f"{pos.x:.{F_PRECISION}f} {pos.y:.{F_PRECISION}f} {pos.z:.{F_PRECISION}f}"}

class Player(Entity):
    CLASSNAME : str = "info_player_start"
    angles : Point3

    def __init__(self, origin : Point3, angles : Point3):
        super().__init__(angles)
        self.angles = angles

    def make_own_dict(self, ids : IDs,
                            last_pos : Point3 = Point3(0.0, 0.0, 0.0),
                            last_angle : Point3 = Point3(0.0, 0.0, 0.0)) -> dict[str, str | list]:
        angle : Point3 = last_angle + self.angles
        entityclass : dict[str, str | list] = super().make_own_dict(ids, last_pos, last_angle)
        entityclass['classname'] = self.CLASSNAME
        entityclass['angles'] = f"{angle.x:.{F_PRECISION}f}, {angle.y:.{F_PRECISION}f}, {angle.z:.{F_PRECISION}f}"
        return entityclass

@dataclass
class Child:
    child : Union[Entity, "Shape"]
    relative : int

@dataclass
class ShapeStackFrame:
    shape : "Shape"
    index : int
    pos : Point3
    angle : Point3

class Shape:
    points : list[Point2]
    uvs : list[UVPoint]
    materials : list[str]
    thickness : float
    top_slope : float
    bottom_slope : float
    child_shapes : list[Child]
    child_entities : list[Child]

    SHAPE = -1
    TOP = 0
    BOTTOM = 1
    SIDE = 2

    def __init__(self, points : list[Point2],
                       thickness : float,
                       pos : Point3 = Point3(0.0, 0.0, 0.0),
                       angle : Point3 = Point3(0.0, 0.0, 0.0),
                       uvs : Optional[list[UVPoint]] = None,
                       materials : Optional[list[str]] = None,
                       top_slope : float = 0.0,
                       bottom_slope : float = 0.0):
        # points is assumed to be clockwise and convex
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
        self.top_slope = top_slope
        self.bottom_slope = bottom_slope
        self.child_shapes = []
        self.child_entities = []

    def add_child_shape(self, child : "Shape", relative : int):
        self.child_shapes.append(Child(child, relative))

    def add_child_entity(self, child : Entity, relative : int):
        self.child_entities.append(Child(child, relative))

    def set_one_material(self, idx : int, material : str):
        self.materials[idx] = material

    def set_all_materials(self, material : str):
        self.materials = list(itertools.repeat(material, len(self.points) + 2))

    def set_top_material(self, material : str):
        self.materials[Shape.TOP] = material

    def set_bottom_material(self, material : str):
        self.materials[Shape.BOTTOM] = material

    def set_side_material(self, idx : int, material : str):
        self.materials[idx - Shape.SIDE] = material

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
            sideclass['plane'] = f"({p1.x:.{F_PRECISION}f} {p1.y:.{F_PRECISION}f} {p1.z:.{F_PRECISION}f}) " \
                                 f"({p2.x:.{F_PRECISION}f} {p2.y:.{F_PRECISION}f} {p2.z:.{F_PRECISION}f}) " \
                                 f"({p3.x:.{F_PRECISION}f} {p3.y:.{F_PRECISION}f} {p3.z:.{F_PRECISION}f})"
            sideclass['material'] = material
            sideclass['uaxis'] = f"[{uv.u_x:.{F_PRECISION}f} {uv.u_y:.{F_PRECISION}f} {uv.u_z:.{F_PRECISION}f} {uv.u_translate:.{F_PRECISION}f}] {uv.u_scale:.{F_PRECISION}f}"
            sideclass['vaxis'] = f"[{uv.v_x:.{F_PRECISION}f} {uv.v_y:.{F_PRECISION}f} {uv.v_z:.{F_PRECISION}f} {uv.v_translate:.{F_PRECISION}f}] {uv.v_scale:.{F_PRECISION}f}"
            return sideclass

    def make_own_dict(self, ids : IDs,
                            pos : Point3,
                            angle : Point3) -> dict[str, str | list]:
        y_origin : float = self.points[0].y
        shapeclass : dict[str, str | list] = {}
        shapeclass['id'] = str(ids.get_and_inc_class_id())
        sides : list[dict] = []
        shapeclass['side'] = sides
        # TODO select sequential points which don't all share a point on an axis
        p1 : Point3 = Point3(self.points[0].x, self.points[0].y, self.thickness / 2.0).rotate(angle) + pos
        p2 : Point3 = Point3(self.points[1].x,
                             self.points[1].y,
                             (self.thickness / 2.0) + ((self.points[1].y - y_origin) * self.top_slope)).rotate(angle) + pos
        p3 : Point3 = Point3(self.points[2].x,
                             self.points[2].y,
                             (self.thickness / 2.0) + ((self.points[2].y - y_origin) * self.top_slope)).rotate(angle) + pos
        sides.append(Shape.make_sideclass(ids.get_and_inc_side_id(),
                                          p1, p2, p3,
                                          self.uvs[Shape.TOP],
                                          self.materials[Shape.TOP]))
        p1 = Point3(self.points[2].x,
                    self.points[2].y,
                    (self.thickness / -2.0) + ((self.points[2].y - y_origin) * self.bottom_slope)).rotate(angle) + pos
        p2 = Point3(self.points[1].x,
                    self.points[1].y,
                    (self.thickness / -2.0) + ((self.points[1].y - y_origin) * self.bottom_slope)).rotate(angle) + pos
        p3 = Point3(self.points[0].x, self.points[0].y, self.thickness / -2.0).rotate(angle) + pos
        sides.append(Shape.make_sideclass(ids.get_and_inc_side_id(),
                                          p1, p2, p3,
                                          self.uvs[Shape.BOTTOM],
                                          self.materials[Shape.BOTTOM]))
        for i in range(len(self.points)):
            i2 : int = (i+1)%len(self.points)
            p1 = Point3(self.points[i2].x, self.points[i2].y, self.thickness / 2.0).rotate(angle) + pos
            p2 = Point3(self.points[i].x, self.points[i].y, self.thickness / 2.0).rotate(angle) + pos
            p3 = Point3(self.points[i].x, self.points[i].y, self.thickness / -2.0).rotate(angle) + pos
            sides.append(Shape.make_sideclass(ids.get_and_inc_side_id(),
                                              p1, p2, p3,
                                              self.uvs[Shape.SIDE + i],
                                              self.materials[Shape.SIDE + i]))
        return shapeclass

    def child_entity_dicts(self, ids : IDs,
                                 last_pos : Point3,
                                 last_angle : Point3,
                                 y_origin : float) -> list[dict[str, str | list]]:
        entityclasses : list[dict[str, str | list]] = []

        for child_entity in self.child_entities:
            child : Entity = child_entity.child
            if child_entity.relative < 0: # shape origin
                entityclasses.append(child_entity.child.make_own_dict(ids, last_pos + self.pos, last_angle + self.angle))
            elif child_entity.relative == Shape.TOP:
                next_pos = Point3(0.0, 0.0, (self.thickness / 2.0) + (self.top_slope * -y_origin)).rotate(self.angle) + self.pos
                next_angle = Point3(self.angle.x + atan2(self.top_slope, 1.0), self.angle.y, self.angle.z)
                entityclasses.append(child_entity.child.make_own_dict(ids,
                                                                    last_pos + next_pos,
                                                                    last_angle + next_angle))
            elif child_entity.relative == Shape.BOTTOM:
                next_pos = Point3(0.0, 0.0, (self.thickness / -2.0) + (self.top_slope * -y_origin)).rotate(self.angle) + self.pos
                next_angle = Point3(self.angle.x - atan2(self.bottom_slope, 1.0), self.angle.y, self.angle.z)
                entityclasses.append(child_entity.child.make_own_dict(ids,
                                                                    last_pos + next_pos,
                                                                    last_angle + next_angle))
            else: # side
                sp1 = self.points[child_entity.relative - self.SIDE]
                sp2 = self.points[(child_entity.relative - self.SIDE + 1)%len(self.points)]
                sp1_ry = sp1.y - y_origin
                sp2_ry = sp2.y - y_origin
                z_offset = ((sp1_ry * self.top_slope) + 
                            (sp1_ry * self.bottom_slope) +
                            (sp2_ry * self.top_slope) +
                            (sp2_ry * self.bottom_slope)) / 4.0
                next_pos = Point3((sp1.x + sp2.x) / 2.0, (sp1.y + sp2.y) / 2.0, z_offset).rotate(self.angle) + self.pos
                side_angle = atan2(sp2.x - sp1.x, sp2.y - sp1.y)
                next_angle = Point3(self.angle.x + side_angle, self.angle.y + (pi / 2.0), self.angle.z + (pi / 2.0))
                entityclasses.append(child_entity.child.make_own_dict(ids,
                                                                    last_pos + next_pos,
                                                                    last_angle + next_angle))

        return entityclasses

    def to_dict(self, ids : IDs) -> tuple[list[dict[str, str | list]],
                                          list[dict[str, str | list]]]:
        shapeclasses : list[dict[str, str | list]] = []
        entityclasses : list[dict[str, str | list]] = []
        shapeclasses.append(self.make_own_dict(ids, self.pos, self.angle))
        entityclasses.extend(self.child_entity_dicts(ids,
                                                     Point3(0.0, 0.0, 0.0),
                                                     Point3(0.0, 0.0, 0.0),
                                                     self.points[0].y))

        stack : list[ShapeStackFrame] = [ShapeStackFrame(self,
                                                         0,
                                                         Point3(0.0, 0.0, 0.0),
                                                         Point3(0.0, 0.0, 0.0))]

        cur_frame : ShapeStackFrame = stack[-1]
        parent : Shape = cur_frame.shape
        last_pos : Point3 = parent.pos
        last_angle : Point3 = parent.angle
        y_origin : float = parent.points[0].y

        process : bool = True
        while process:
            # get the current shape to process
            child : Child = cur_frame.shape.child_shapes[cur_frame.index]
            cur : Shape = child.child
            pos : Point3 = cur.pos
            angle : Point3 = cur.angle

            if child.relative < 0: # shape origin
                # just add the angle and position of this shape's origin
                shapeclasses.append(cur.make_own_dict(ids, last_pos + pos, last_angle + angle))
            elif child.relative == Shape.TOP:
                # find the top angle with slope as well as the offset from the origin with slope, rotated by this shape's angle
                next_pos : Point3 = Point3(0.0, 0.0, (cur.thickness / 2.0) + (cur.top_slope * -y_origin)).rotate(angle) + pos
                next_angle : Point3 = Point3(angle.x + atan2(cur.top_slope, 1.0), angle.y, angle.z)
                shapeclasses.append(cur.make_own_dict(ids,
                                                      last_pos + next_pos,
                                                      last_angle + next_angle))
            elif child.relative == Shape.BOTTOM:
                # TODO probably wrong
                # mostly the same as above
                next_pos = Point3(0.0, 0.0, (cur.thickness / -2.0) + (cur.top_slope * -y_origin)).rotate(angle) + pos
                # rotate everything upside down
                next_angle = Point3(angle.x - atan2(cur.bottom_slope, 1.0), angle.y, angle.z)
                shapeclasses.append(cur.make_own_dict(ids,
                                                      last_pos + next_pos,
                                                      last_angle + next_angle))
            else: # side
                sp1 : Point2 = parent.points[child.relative - Shape.SIDE]
                sp2 : Point2 = parent.points[(child.relative - Shape.SIDE + 1)%len(parent.points)]
                sp1_ry : float = sp1.y - y_origin
                sp2_ry : float = sp2.y - y_origin
                z_offset : float = ((sp1_ry * parent.top_slope) + 
                                    (sp1_ry * parent.bottom_slope) +
                                    (sp2_ry * parent.top_slope) +
                                    (sp2_ry * parent.bottom_slope)) / 4.0
                next_pos = Point3((sp1.x + sp2.x) / 2.0, (sp1.y + sp2.y) / 2.0, z_offset).rotate(angle) + pos
                # rotate everything to be flat with the side
                side_angle : float = atan2(sp2.x - sp1.x, sp2.y - sp1.y)
                next_angle = Point3(angle.x + side_angle, angle.y + (pi / 2.0), angle.z + (pi / 2.0))
                shapeclasses.append(cur.make_own_dict(ids,
                                                      last_pos + next_pos,
                                                      last_angle + next_angle))

            if len(cur.child_shapes) > 0:
                # if the shape has any child shapes, add it to the stack to start processing through them
                stack.append(ShapeStackFrame(cur, 0, last_pos, last_angle))
                cur_frame = stack[-1]
                # update current status variables
                parent = cur_frame.shape
                last_pos += cur.pos
                last_angle += cur.angle
                y_origin = parent.points[0].y

                entityclasses.extend(parent.child_entity_dicts(ids, last_pos, last_angle, y_origin))
            else:
                cur_frame.index += 1
                while cur_frame.index == len(cur_frame.shape.child_shapes):
                    # if there are no more, go back up the stack
                    del stack[-1]
                    # if there's no more stack, there's nothing left to do
                    if len(stack) == 0:
                        process = False
                        break

                    cur_frame = stack[-1]
                    # update current status variables
                    parent = cur_frame.shape
                    last_pos = cur_frame.pos
                    last_angle = cur_frame.angle
                    y_origin = parent.points[0].y

                    # advance to the next entry
                    cur_frame.index += 1

        return shapeclasses, entityclasses

class VMF:
    shapes : list[Shape]
    entities : list[Entity]

    def __init__(self) -> None:
        self.shapes = []
        self.entities = []

    def add_shape(self, shape : Shape):
        self.shapes.append(shape)

    def add_entity(self, entity : Entity):
        self.entities.append(entity)

    def generate(self) -> str:
        ids : IDs = IDs()
        root : dict[str, str | list] = {}
        root['versioninfo'] = [copy.copy(DEFAULT_VERSIONINFO)]
        root['world'] = [copy.copy(DEFAULT_WORLD)]
        root['world'][0]['id'] = str(ids.get_and_inc_class_id())
        solids_class : list[dict[str, str | list]] = []
        root['world'][0]['solid'] = solids_class
        entities_class : list[dict[str, str | list]] = []
        root['entity'] = entities_class
        for shape in self.shapes:
            shapes, entities = shape.to_dict(ids)
            solids_class.extend(shapes)
            entities_class.extend(entities)
        for entity in self.entities:
            # entities have no children, nor generate shapes
            entities_class.append(entity.make_own_dict(ids))
        return SourceFile.dump(root)

def main(args : list[str]):
    #d = SourceFile(pathlib.Path(args[0])).load()
    v = VMF()

    materials : list[str] = list(itertools.repeat("brick/brickwall026f", 10))
    materials[0] = "concrete/concretefloor033a"
    materials[1] = "concrete/concretefloor033a"
    polygon : list[Point2] = gen_polygon(8, 1024.0)
    shape : Shape = Shape(polygon,
                          16.0,
                          pos=Point3(0.0, 0.0, 50.0),
                          materials=materials,
                          top_slope=0.02,
                          bottom_slope=0.01)
    shape.add_child_entity(Player(Point3(0.0, 0.0, 10.0),
                                  Point3(0.0, 0.0, 0.0)),
                           Shape.TOP)
    shape.add_child_shape(Shape(polygon,
                                16.0,
                                pos=Point3(0.0, 0.0, 256.0),
                                materials=materials),
                          Shape.SHAPE)
    wallmaterials : list[str] = list(itertools.repeat("brick/brickwall026f", 6))
    side_length : float = hypot(polygon[1].x - polygon[0].x, polygon[1].y - polygon[0].y)
    wall : list[Point2] = [Point2(-side_length / 2.0 - 1.0, 128.0),
                           Point2(side_length / 2.0 + 1.0, 128.0),
                           Point2(side_length / 2.0 + 1.0, -128.0),
                           Point2(-side_length / 2.0 - 1.0, -128.0)]
    for i in range(len(polygon)):
        i2 : int = (i+1)%len(polygon)
        wallshape = Shape(wall,
                          16.0,
                          pos=Point3(0.0, 0.0, 128.0),
                          materials=wallmaterials)
        shape.add_child_shape(wallshape, Shape.SIDE + i)
    v.add_shape(shape)
    print(v.generate())

    return

if __name__ == '__main__':
    main(sys.argv[1:])