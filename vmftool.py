#!/usr/bin/env python3

import io
import pathlib
from typing import Optional, Union, Any
from enum import Enum, auto
from dataclasses import dataclass
from collections import namedtuple
from collections.abc import Callable
import pprint
import copy
import itertools
from math import pi, tau, sin, cos, tan, hypot, atan2
from abc import ABC, abstractmethod

F_PRECISION : int = 3
DEFAULT_MATERIAL = "BLACK_OUTLINE"

DEFAULT_VERSIONINFO : dict[str, str | list] = {
	"editorversion": "400",
	"editorbuild": "8870",
	"mapversion": "0",
	"formatversion": "100"
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

    def __str__(self) -> str:
        return f"{self.x:.{F_PRECISION}f} {self.y:.{F_PRECISION}f}"

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

    def __str__(self) -> str:
        return f"{self.x:.{F_PRECISION}f} {self.y:.{F_PRECISION}f} {self.z:.{F_PRECISION}f}"

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

@dataclass
class UVPoint():
    u : Point3
    u_translate : float
    u_scale : float
    v : Point3
    v_translate : float
    v_scale : float

    def u_str(self) -> str:
        return f"[{self.u} {self.u_translate:.{F_PRECISION}f}] {self.u_scale:.{F_PRECISION}f}"

    def v_str(self) -> str:
        return f"[{self.v} {self.v_translate:.{F_PRECISION}f}] {self.v_scale:.{F_PRECISION}f}"

    def rotate(self,
               angle : Point3) -> "UVPoint":
        return UVPoint(self.u.rotate(angle), self.u_translate, self.u_scale,
                       self.v.rotate(angle), self.v_translate, self.v_scale)

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

class Shape(ABC):
    pos : Point3
    angle : Point3
    child_shapes : list["ChildShape"]
    child_entities : list["ChildEntity"]

    @abstractmethod
    def __init__(self, pos : Point3 = Point3(0.0, 0.0, 0.0),
                       angle : Point3 = Point3(0.0, 0.0, 0.0)):
        self.pos = pos
        self.angle = angle
        self.child_shapes = []
        self.child_entities = []

    @abstractmethod
    def make_own_dict(self, ids : IDs,
                            pos : Point3,
                            angle : Point3) -> dict[str, str | list]:
        pass

    @abstractmethod
    def get_child_offset(self, relative : int) -> tuple[Point3, Point3]:
        pass

    @staticmethod
    def make_sideclass(side_id : int,
                       p1 : Point3,
                       p2 : Point3,
                       p3 : Point3,
                       uv : UVPoint,
                       material : str) -> dict[str, str | list]:
        sideclass : dict[str, str | list] = copy.copy(DEFAULT_SIDE)
        sideclass['id'] = str(side_id)
        sideclass['plane'] = f"({p1}) ({p2}) ({p3})"
        sideclass['material'] = material
        sideclass['uaxis'] = uv.u_str()
        sideclass['vaxis'] = uv.v_str()
        return sideclass

    def add_child_shape(self, shape : "Shape", relative : int):
        self.child_shapes.append(ChildShape(relative, shape))

    def add_child_entity(self, entity : "Entity", relative : int):
        self.child_entities.append(ChildEntity(relative, entity))

    def child_entity_dicts(self, ids : IDs,
                                 last_pos : Point3,
                                 last_angle : Point3) -> list[dict[str, str | list]]:
        return [child_entity.entity.make_own_dict(ids, last_pos + self.pos, last_angle + self.angle) for child_entity in self.child_entities]

    def to_dict(self, ids : IDs) -> tuple[list[dict[str, str | list]],
                                          list[dict[str, str | list]]]:
        shapeclasses : list[dict[str, str | list]] = []
        entityclasses : list[dict[str, str | list]] = []
        shapeclasses.append(self.make_own_dict(ids,
                                               Point3(0.0, 0.0, 0.0),
                                               Point3(0.0, 0.0, 0.0)))
        entityclasses.extend(self.child_entity_dicts(ids,
                                                     Point3(0.0, 0.0, 0.0),
                                                     Point3(0.0, 0.0, 0.0)))

        stack : list["ChildStackFrame"] = [ChildStackFrame(self,
                                                           0,
                                                           Point3(0.0, 0.0, 0.0),
                                                           Point3(0.0, 0.0, 0.0))]

        cur_frame : "ChildStackFrame" = stack[-1]
        parent : Shape = cur_frame.child
        last_pos : Point3 = Point3(0.0, 0.0, 0.0)
        last_angle : Point3 = Point3(0.0, 0.0, 0.0)

        process : bool = True
        while process:
            # get the current shape to process
            child : ChildShape = cur_frame.child.child_shapes[cur_frame.index]
            cur : Shape = child.shape

            next_pos, next_angle = parent.get_child_offset(child.relative)
            shapeclasses.append(cur.make_own_dict(ids, last_pos + next_pos, last_angle + next_angle))
            entityclasses.extend(cur.child_entity_dicts(ids, last_pos + next_pos, last_angle + next_angle))

            if len(cur.child_shapes) > 0:
                # if the shape has any child shapes, add it to the stack to start processing through them
                stack.append(ChildStackFrame(cur, 0, last_pos, last_angle))
                cur_frame = stack[-1]

                # update current status variables
                last_pos += next_pos
                last_angle += next_angle
            else:
                cur_frame.index += 1
                while cur_frame.index == len(cur_frame.child.child_shapes):
                    # if there are no more, go back up the stack
                    del stack[-1]
                    # if there's no more stack, there's nothing left to do
                    if len(stack) == 0:
                        process = False
                        break

                    cur_frame = stack[-1]
                    # advance to the next entry
                    cur_frame.index += 1

                    # update current status variables
                    last_pos = cur_frame.pos
                    last_angle = cur_frame.angle

        return shapeclasses, entityclasses

class PolygonShape(Shape):
    points : list[Point2]
    uvs : list[UVPoint]
    materials : list[str]
    thickness : float
    top_slope : float
    bottom_slope : float

    SHAPE = -1
    TOP = 0
    BOTTOM = 1
    SIDE = 2

    def __init__(self, points : list[Point2],
                       thickness : float,
                       pos : Point3 = Point3(0.0, 0.0, 0.0),
                       angle : Point3 = Point3(0.0, 0.0, 0.0),
                       uvs : Optional[list[UVPoint]] = None,
                       materials : Union[Optional[list[str]], str] = None,
                       top_slope : float = 0.0,
                       bottom_slope : float = 0.0):
        super().__init__(pos, angle)
        # points is assumed to be clockwise and convex
        self.points = points
        self.thickness = thickness
        # TODO top/bottom angle UVs
        if uvs is None:
            uvs = [UVPoint(Point3(1.0, 0.0, 0.0), 0.0, 1.0,
                           Point3(0.0, 1.0, 0.0), 0.0, 1.0),
                   UVPoint(Point3(1.0, 0.0, 0.0), 0.0, 1.0,
                           Point3(0.0, 1.0, 0.0), 0.0, 1.0)]
            for i in range(len(points)):
                p1 : Point2 = points[(i+1)%len(points)]
                p2 : Point2 = points[i]
                xdiff : float = p2.x - p1.x
                ydiff : float = p2.y - p1.y
                maxdiff : float = max(abs(xdiff), abs(ydiff))
                uvs.append(UVPoint(Point3(xdiff / maxdiff, ydiff / maxdiff, 0.0), 0.0, 1.0,
                                   Point3(0.0, 0.0, 1.0), 0.0, 1.0))
        self.uvs = uvs
        if not isinstance(materials, list):
            if materials is None:
                materials = list(itertools.repeat(DEFAULT_MATERIAL, len(points) + 2))
            else:
                materials = list(itertools.repeat(materials, len(points) + 2))
        self.materials = materials
        self.top_slope = top_slope
        self.bottom_slope = bottom_slope

    def set_one_material(self, idx : int, material : str):
        self.materials[idx] = material

    def set_all_materials(self, material : str):
        self.materials = list(itertools.repeat(material, len(self.points) + 2))

    def set_top_material(self, material : str):
        self.materials[PolygonShape.TOP] = material

    def set_bottom_material(self, material : str):
        self.materials[PolygonShape.BOTTOM] = material

    def set_side_material(self, idx : int, material : str):
        self.materials[idx - PolygonShape.SIDE] = material

    def set_all_side_materials(self, material : str):
        self.materials[2:] = list(itertools.repeat(material, len(self.points)))

    def get_child_offset(self, relative : int) -> tuple[Point3, Point3]:
        y_origin : float = self.points[0].y

        if relative < 0: # shape origin
            # just add the angle and position of this shape's origin
            return self.pos, self.angle
        elif relative == PolygonShape.TOP:
            # find the top angle with slope as well as the offset from the origin with slope, rotated by this shape's angle
            return Point3(0.0, 0.0, (self.thickness / 2.0) + (self.top_slope * -y_origin)).rotate(self.angle) + self.pos, \
                   Point3(self.angle.x + atan2(self.top_slope, 1.0), self.angle.y, self.angle.z)
        elif relative == PolygonShape.BOTTOM:
            # TODO probably wrong
            # mostly the same as above
            # rotate everything upside down
            return Point3(0.0, 0.0, (self.thickness / -2.0) + (self.top_slope * -y_origin)).rotate(self.angle) + self.pos, \
                   Point3(self.angle.x - atan2(self.bottom_slope, 1.0), self.angle.y, self.angle.z)
        # side
        sp1 : Point2 = self.points[relative - PolygonShape.SIDE]
        sp2 : Point2 = self.points[(relative - PolygonShape.SIDE + 1)%len(self.points)]
        sp1_ry : float = sp1.y - y_origin
        sp2_ry : float = sp2.y - y_origin
        z_offset : float = ((sp1_ry * self.top_slope) + 
                            (sp1_ry * self.bottom_slope) +
                            (sp2_ry * self.top_slope) +
                            (sp2_ry * self.bottom_slope)) / 4.0
        side_angle : float = atan2(sp2.x - sp1.x, sp2.y - sp1.y)
        # rotate everything to be flat with the side
        return Point3((sp1.x + sp2.x) / 2.0, (sp1.y + sp2.y) / 2.0, z_offset).rotate(self.angle) + self.pos, \
               Point3(self.angle.x + side_angle, self.angle.y + (pi / 2.0), self.angle.z + (pi / 2.0))

    def make_own_dict(self, ids : IDs,
                            last_pos : Point3,
                            last_angle : Point3) -> dict[str, str | list]:
        pos : Point3 = last_pos + self.pos
        angle : Point3 = last_angle + self.angle

        shapeclass : dict[str, str | list] = {}
        shapeclass['id'] = str(ids.get_and_inc_class_id())
        sides : list[dict] = []
        shapeclass['side'] = sides

        y_origin : float = self.points[0].y
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
                                          self.uvs[PolygonShape.TOP].rotate(angle),
                                          self.materials[PolygonShape.TOP]))
        p1 = Point3(self.points[2].x,
                    self.points[2].y,
                    (self.thickness / -2.0) + ((self.points[2].y - y_origin) * self.bottom_slope)).rotate(angle) + pos
        p2 = Point3(self.points[1].x,
                    self.points[1].y,
                    (self.thickness / -2.0) + ((self.points[1].y - y_origin) * self.bottom_slope)).rotate(angle) + pos
        p3 = Point3(self.points[0].x, self.points[0].y, self.thickness / -2.0).rotate(angle) + pos
        sides.append(Shape.make_sideclass(ids.get_and_inc_side_id(),
                                          p1, p2, p3,
                                          self.uvs[PolygonShape.BOTTOM].rotate(angle),
                                          self.materials[PolygonShape.BOTTOM]))
        for i in range(len(self.points)):
            i2 : int = (i+1)%len(self.points)
            p1 = Point3(self.points[i2].x, self.points[i2].y, self.thickness / 2.0).rotate(angle) + pos
            p2 = Point3(self.points[i].x, self.points[i].y, self.thickness / 2.0).rotate(angle) + pos
            p3 = Point3(self.points[i].x, self.points[i].y, self.thickness / -2.0).rotate(angle) + pos
            sides.append(Shape.make_sideclass(ids.get_and_inc_side_id(),
                                              p1, p2, p3,
                                              self.uvs[PolygonShape.SIDE + i].rotate(angle),
                                              self.materials[PolygonShape.SIDE + i]))
        return shapeclass

@dataclass
class EntityOption:
    to_dict : Callable[[Any], str]
    default : Any

@dataclass
class EntityDef:
    name : str
    options : dict[str, EntityOption]

ENTITIES : dict[str, EntityDef] = {
    "info_player_start": EntityDef("info_player_start", {
        "angles": EntityOption(lambda a: str(a),
                               Point3(0.0, 0.0, 0.0))
    })
}

class Entity:
    entitydef : EntityDef
    origin : Point3
    options : Optional[dict[str, Any]]
    solid : list[Shape]

    def __init__(self, name : str,
                       origin : Point3,
                       options : Optional[dict[str, Any]] = None):
        self.entitydef = ENTITIES[name]
        if options is not None:
            for option in options.keys():
                if not isinstance(options[option], type(self.entitydef.options[option].default)):
                    raise TypeError(f"Option type is '{type(options[option])}' but should be '{type(self.entitydef.options[option].default)}'.")
            self.options = copy.copy(options)
        else:
            self.options = None
        self.origin = origin
        self.solid = []

    def add_shape(self, shape : Shape):
        self.solid.append(shape)

    def make_own_dict(self, ids : IDs,
                            last_pos : Point3 = Point3(0.0, 0.0, 0.0),
                            last_angle : Point3 = Point3(0.0, 0.0, 0.0)) -> dict[str, str | list]:
        pos : Point3 = last_pos + self.origin
        ret : dict[str, str | list] = {"id": str(ids.get_and_inc_class_id()),
                                       "classname": self.entitydef.name,
                                       "origin": str(pos)}
        if self.options is not None:
            for option in self.entitydef.options.keys():
                if option in self.options:
                    ret[option] = self.entitydef.options[option].to_dict(self.options[option])
                else:
                    ret[option] = self.entitydef.options[option].to_dict(self.entitydef.options[option].default)
        if len(self.solid) > 0:
            solids_class : list[dict[str, str | list]] = []
            ret['solid'] = solids_class
            for solid in self.solid:
                # this ends up being recursive, but for the moment, brush entities with children is unsupported.
                solids, _ = solid.to_dict(ids)
                solids_class.extend(solids)
        return ret

@dataclass
class Child:
    relative : int

@dataclass
class ChildShape(Child):
    shape : Shape

@dataclass
class ChildEntity(Child):
    entity : Entity

@dataclass
class ChildStackFrame:
    child : Union[Shape, Entity]
    index : int
    pos : Point3
    angle : Point3

class VMF:
    shapes : list[Shape]
    entities : list[Entity]
    prefab : bool

    def __init__(self, prefab : bool = False) -> None:
        self.shapes = []
        self.entities = []
        self.prefab = prefab

    def add_shape(self, shape : Shape):
        self.shapes.append(shape)

    def add_entity(self, entity : Entity):
        self.entities.append(entity)

    def generate(self) -> str:
        ids : IDs = IDs()
        root : dict[str, str | list] = {}
        root['versioninfo'] = [copy.copy(DEFAULT_VERSIONINFO)]
        root['versioninfo'][0]['prefab'] = '1' if self.prefab else '0'
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