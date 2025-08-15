#!/usr/bin/env python3

import io
import sys
import pathlib
from typing import Optional
from enum import Enum, auto
from dataclasses import dataclass
import pprint
import copy
import itertools
import math

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

class Side:
    plane : tuple[tuple[float, float, float],
                  tuple[float, float, float],
                  tuple[float, float, float]]
    material : str = DEFAULT_MATERIAL
    uv : tuple[tuple[float, float, float, float, float],
               tuple[float, float, float, float, float]]

    def __init__(self, plane, material = DEFAULT_MATERIAL, uv = None):
        self.plane = plane
        self.material = material
        self.uv = uv

class VMF:
    def __init__(self) -> None:
        self.brushes : list[list[Side]] = []

    def add_brush(self, sides : list[Side]):
        self.brushes.append(copy.copy(sides))

    def add_polygon(self, pos : tuple[float, float],
                          angle : tuple[float, float, float],
                          sides : int,
                          radius : float,
                          thickness : float,
                          materials : list[str],
                          side_proportions : Optional[list[float]] = None,
                          point_proportions : Optional[list[float]] = None):
        if side_proportions is None:
            side_proportions = list(itertools.repeat(1.0, sides))
        if point_proportions is None:
            point_proportions = list(itertools.repeat(1.0, sides))
        for item in side_proportions:
            if item > 1.0:
                raise ValueError("side proportions must be 0.0 to 1.0")
        max_proportion : float = sum(side_proportions)
        proportion : float = side_proportions[0] / 2.0
        side_points : list[tuple[float, float]] = []
        for side in side_proportions:
            point_distance : float = math.hypot(side, 1.0) * radius
            x : float = math.sin(proportion / max_proportion * math.tau) * point_distance
            y : float = math.cos(proportion / max_proportion * math.tau) * point_distance
            side_points.append((x, y))
            proportion += side
        brush_sides : list[Side] = []
        top_z : float = thickness / 2.0
        bottom_z : float = -thickness / 2.0
        # top
        plane = ((side_points[0][0], side_points[0][1], top_z),
                 (side_points[1][0], side_points[1][1], top_z),
                 (side_points[2][0], side_points[2][1], top_z))
        brush_sides.append(Side(plane, material=materials[0], uv=((1.0, 0.0, 0.0, 0.0, 1.0),
                                                                  (0.0, 1.0, 0.0, 0.0, 1.0))))
        # bottom
        plane = ((side_points[2][0], side_points[2][1], bottom_z),
                 (side_points[1][0], side_points[1][1], bottom_z),
                 (side_points[0][0], side_points[0][1], bottom_z))
        brush_sides.append(Side(plane, material=materials[1], uv=((1.0, 0.0, 0.0, 0.0, 1.0),
                                                                  (0.0, 1.0, 0.0, 0.0, 1.0))))
        # sides
        for i in range(len(side_points) - 1):
            plane = ((side_points[i+1][0], side_points[i+1][1], top_z),
                     (side_points[i][0], side_points[i][1], top_z),
                     (side_points[i][0], side_points[i][1], bottom_z))
            xdiff : float = plane[1][0] - plane[0][0]
            ydiff : float = plane[1][1] - plane[0][1]
            maxdiff : float = max(abs(xdiff), abs(ydiff))
            brush_sides.append(Side(plane, material=materials[i+2], uv=((xdiff / maxdiff, ydiff / maxdiff, 0.0, 0.0, 1.0),
                                                                        (0.0, 0.0, 1.0, 0.0, 1.0))))
        # last side
        plane = ((side_points[0][0], side_points[0][1], top_z),
                 (side_points[-1][0], side_points[-1][1], top_z),
                 (side_points[-1][0], side_points[-1][1], bottom_z))
        xdiff = plane[1][0] - plane[0][0]
        ydiff = plane[1][1] - plane[0][1]
        maxdiff = max(abs(xdiff), abs(ydiff))
        brush_sides.append(Side(plane, material=materials[-1], uv=((xdiff / maxdiff, ydiff / maxdiff, 0.0, 0.0, 1.0),
                                                                    (0.0, 0.0, 1.0, 0.0, 1.0))))
        self.add_brush(brush_sides)

    def generate(self) -> str:
        class_id = 2
        side_id = 1
        root : dict[str, str | list] = {}
        root['versioninfo'] = [copy.copy(DEFAULT_VERSIONINFO)]
        root['world'] = [copy.copy(DEFAULT_WORLD)]
        solids = []
        root['world'][0]['solid'] = solids
        for brush in self.brushes:
            brushclass : dict[str, str | list] = {}
            brushclass['id'] = str(class_id)
            class_id += 1
            sides : list[dict] = []
            brushclass['side'] = sides
            solids.append(brushclass)
            for side in brush:
                sideclass : dict[str, str | list] = copy.copy(DEFAULT_SIDE)
                sideclass['id'] = str(side_id)
                side_id += 1
                plane = side.plane
                sideclass['plane'] = f"({plane[0][0]:.3f} {plane[0][1]:.3f} {plane[0][2]:.3f}) " \
                                     f"({plane[1][0]:.3f} {plane[1][1]:.3f} {plane[1][2]:.3f}) " \
                                     f"({plane[2][0]:.3f} {plane[2][1]:.3f} {plane[2][2]:.3f})"
                sideclass['material'] = side.material
                uv = side.uv
                sideclass['uaxis'] = f"[{uv[0][0]:.3f} {uv[0][1]:.3f} {uv[0][2]:.3f} {uv[0][3]:.3f}] {uv[0][4]:.3f}"
                sideclass['vaxis'] = f"[{uv[1][0]:.3f} {uv[1][1]:.3f} {uv[1][2]:.3f} {uv[1][3]:.3f}] {uv[1][4]:.3f}"
                sides.append(sideclass)
        return SourceFile.dump(root)

def main(args : list[str]):
    #d = SourceFile(pathlib.Path(args[0])).load()
    v = VMF()

    materials : list[str] = list(itertools.repeat("brick/brickwall026f", 10))
    materials[0] = "concrete/concretefloor033a"
    materials[1] = "concrete/concretefloor033a"
    v.add_polygon((0.0, 0.0),
                  (0.0, 0.0, 0.0),
                  8,
                  64.0,
                  128.0,
                  materials=materials)
    print(v.generate())

    return
 
    v.add_brush([Side(((-64.0, 128.0, 64.0), (64.0, 128.0, 64.0), (64.0, 0.0, 64.0)),
                      material="concrete/concretefloor033a",
                      uv=((1.0, 0.0, 0.0, 0.0, 0.25),
                          (0.0, -1.0, 0.0, 0.0, 0.25))),
                 Side(((-64.0, 0.0, 0.0), (64.0, 0.0, 0.0), (64.0, 128.0, 0.0)),
                      material="concrete/concretefloor033a",
                      uv=((1.0, 0.0, 0.0, 0.0, 0.25),
                          (0.0, -1.0, 0.0, 0.0, 0.25))),
                 Side(((-64.0, 128.0, 64.0), (-64.0, 0.0, 64.0), (-64.0, 0.0, 0.0)),
                      material="concrete/concretefloor033a",
                      uv=((0.0, 1.0, 0.0, 0.0, 0.25),
                          (0.0, 0.0, -1.0, 0.0, 0.25))),
                 Side(((64.0, 128.0, 0.0), (64.0, 0.0, 0.0), (64.0, 0.0, 64.0)),
                      material="concrete/concretefloor033a",
                      uv=((0.0, 1.0, 0.0, 0.0, 0.25),
                          (0.0, 0.0, -1.0, 0.0, 0.25))),
                 Side(((64.0, 128.0, 64.0), (-64.0, 128.0, 64.0), (-64.0, 128.0, 0.0)),
                      material="concrete/concretefloor033a",
                      uv=((1.0, 0.0, 0.0, 0.0, 0.25),
                          (0.0, 0.0, -1.0, 0.0, 0.25))),
                 Side(((64.0, 0.0, 0.0), (-64.0, 0.0, 0.0), (-64.0, 0.0, 64.0)),
                      material="concrete/concretefloor033a",
                      uv=((1.0, 0.0, 0.0, 0.0, 0.25),
                          (0.0, 0.0, -1.0, 0.0, 0.25)))])

    #print(v.generate())

if __name__ == '__main__':
    main(sys.argv[1:])