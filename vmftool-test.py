#!/usr/bin/env python3

import sys
from typing import Optional, Union
from math import hypot
import itertools
from vmftool import *

DEFAULT_WALL_THICKNESS : float = 16.0

def make_room(sides : int,
              radius : float,
              height : float,
              wall_materials : Union[list[str], str],
              floor_material : str,
              ceiling_material : str,
              wall_thickness : float = DEFAULT_WALL_THICKNESS,
              make_wall : Optional[list[bool]] = None) -> Shape:
    half_thickness : float = wall_thickness / 2.0
    polygon : list[Point2] = gen_polygon(sides, radius + half_thickness)
    shape : Shape = Shape(polygon,
                          wall_thickness,
                          pos=Point3(0.0, 0.0, 0.0 - half_thickness),
                          materials=floor_material)
    # add the whole wall thickness to compensate for the half thickness subtracted from the floor
    shape.add_child_shape(Shape(polygon,
                                wall_thickness,
                                pos=Point3(0.0, 0.0, height + wall_thickness),
                                materials=ceiling_material),
                          Shape.SHAPE)
    side_length : float = hypot(polygon[1].x - polygon[0].x, polygon[1].y - polygon[0].y)
    wall : list[Point2] = [Point2(-side_length / 2.0 - half_thickness, height + wall_thickness),
                           Point2(side_length / 2.0 + half_thickness, height + wall_thickness),
                           Point2(side_length / 2.0 + half_thickness, 0.0),
                           Point2(-side_length / 2.0 - half_thickness, 0.0)]
    for i in range(len(polygon)):
        if make_wall is None or make_wall[i] is False:
            continue
        i2 : int = (i+1)%len(polygon)
        shape.add_child_shape(Shape(wall,
                                    wall_thickness,
                                    pos=Point3(0.0, 0.0, 0.0),
                                    materials=wall_materials),
                              Shape.SIDE + i)
    return shape

def main(args : list[str]):
    v : VMF = VMF()

    shape = make_room(8, 256.0, 128.0,
                      "brick/brickwall026f",
                      "concrete/concretefloor033a",
                      "concrete/concretefloor033a",
                      make_wall=[False, True, True, True, True, True, True, True])
    shape.add_child_entity(Entity("info_player_start",
                                  Point3(0.0, 0.0, 10.0),
                                  {'angles': Point3(0.0, 0.0, 0.0)}),
                           Shape.TOP)
    v.add_shape(shape)
    print(v.generate())

if __name__ == '__main__':
    main(sys.argv[1:])