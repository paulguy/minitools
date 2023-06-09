#!/usr/bin/env python

import struct

rxcoords = (
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0
)

rycoords = (
    0.0, -0.001, 0.001, 0.006,
    0.0, 0.0, -0.001, 0.0,
    0.0, 0.0, 0.002, 0.0,
    0.0, -0.001, -0.001, 0.0
)

gxcoords = (
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0
)

gycoords = (
    0.003, 0.003, 0.005, 0.001,
    0.0, 0.002, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, -0.003, -0.003, 0.0
)

bxcoords = (
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0
)

bycoords = (
    -0.004, 0.0, 0.0, 0.0,
    0.0, -0.001, 0.0, 0.0,
    0.0, 0.001, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.002
)

print("""//!TEXTURE XCOORDS
//!SIZE 4 4
//!FORMAT rgb16f
//!FILTER LINEAR""")
for r, g, b in zip(rxcoords, gxcoords, bxcoords):
    print(memoryview(struct.pack('fff', 1.0-r, 1.0-g, 1.0-b)).hex(), end='')
print()
print()
print("""//!TEXTURE YCOORDS
//!SIZE 4 4
//!FORMAT rgb16f
//!FILTER LINEAR""")
for r, g, b in zip(rycoords, gycoords, bycoords):
    print(memoryview(struct.pack('fff', 1.0-r, 1.0-g, 1.0-b)).hex(), end='')
print()
print()
print("""//!HOOK OUTPUT
//!BIND HOOKED
//!BIND XCOORDS
//!BIND YCOORDS
//!COMPONENTS 3
//!DESC Convergence Adjust

#define COORDS_WIDTH (4.0)
#define COORDS_HEIGHT (4.0)

const vec2 COORDS_size = vec2(COORDS_WIDTH, COORDS_HEIGHT);
const vec2 border = 1.0 / COORDS_size / 2.0;
const vec2 area = 1.0 - (border * 2.0);

vec4 hook() {
    vec2 pos = HOOKED_pos * area + border;
    vec3 xoffset = texture(XCOORDS, pos).rgb - 1.0;
    vec3 yoffset = texture(YCOORDS, pos).rgb - 1.0;
    vec2 roffset = vec2(xoffset.r, yoffset.r);
    vec2 goffset = vec2(xoffset.g, yoffset.g);
    vec2 boffset = vec2(xoffset.b, yoffset.b);

    //return vec4(roffset.x + 1.0 / 2.0,
    //            goffset.x + 1.0 / 2.0,
    //            boffset.x + 1.0 / 2.0,
    //            1.0);
    return vec4(HOOKED_tex(HOOKED_pos + roffset).r,
                HOOKED_tex(HOOKED_pos + goffset).g,
                HOOKED_tex(HOOKED_pos + boffset).b,
                1.0);
}""")
print()
