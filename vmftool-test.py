#!/usr/bin/env python3

import sys
from typing import Optional, Union
from math import hypot
import itertools
from vmftool import VMF, Point2, Point3, Shape, gen_polygon, Player

DEFAULT_WALL_THICKNESS : float = 16.0

def make_room(sides : int,
              radius : float,
              height : float,
              wall_materials : Union[list[str], str],
              floor_material : str,
              ceiling_material : str,
              wall_thickness : float = DEFAULT_WALL_THICKNESS) -> Shape:
    half_thickness : float = wall_thickness / 2.0
    polygon : list[Point2] = gen_polygon(sides, radius + half_thickness)
    shape : Shape = Shape(polygon,
                          wall_thickness,
                          pos=Point3(0.0, 0.0, 0.0 - half_thickness),
                          materials=floor_material)
    shape.add_child_shape(Shape(polygon,
                                wall_thickness,
                                pos=Point3(0.0, 0.0, height + half_thickness),
                                materials=ceiling_material),
                          Shape.SHAPE)
    side_length : float = hypot(polygon[1].x - polygon[0].x, polygon[1].y - polygon[0].y)
    wall : list[Point2] = [Point2(-side_length / 2.0 - half_thickness, height + half_thickness),
                           Point2(side_length / 2.0 + half_thickness, height + half_thickness),
                           Point2(side_length / 2.0 + half_thickness, -half_thickness),
                           Point2(-side_length / 2.0 - half_thickness, -half_thickness)]
    for i in range(len(polygon)):
        i2 : int = (i+1)%len(polygon)
        wallshape = Shape(wall,
                          wall_thickness,
                          pos=Point3(0.0, 0.0, height),
                          materials=wall_materials)
        shape.add_child_shape(wallshape, Shape.SIDE + i)
    return shape

def main(args : list[str]):
    #d = SourceFile(pathlib.Path(args[0])).load()
    v : VMF = VMF()

    shape = make_room(8, 128.0, 32.0,
                      "brick/brickwall026f",
                      "concrete/concretefloor033a",
                      "concrete/concretefloor033a")
    shape.child_shapes[0].child.add_child_entity(Player(Point3(0.0, 0.0, 10.0),
                                                        Point3(0.0, 0.0, 0.0)),
                                                        Shape.TOP)
    v.add_shape(shape)
    print(v.generate())

if __name__ == '__main__':
    main(sys.argv[1:])