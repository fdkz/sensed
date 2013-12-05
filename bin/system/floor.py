from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

import vector
import vbo

class Floor:
    def __init__(self, num_tiles=100, tile_size=1.):
        """Build a grid of lines on the x/z plane. While drawing, also render a filled quad under the lines.
        Midpoint will be on the zero-coordinate."""
        self.num_tiles = num_tiles
        self.tile_size = tile_size
        self.grid_color = (0.7, 0.7, 0.7, 1.0)
        self.fill_color = (0.6, 0.6, 0.6, 0.6)

        #self._floor_vertex_list = pyglet.graphics.vertex_list((ntiles+1) * 4, ('v3f/static', v))
        self._floor_vertex_list = self._build_grid_vbo(num_tiles, tile_size)

    def _build_grid_vbo(self, num_tiles, tile_size):
        w2 = num_tiles * tile_size / 2.
        v = []; ts = tile_size
        for i in range(num_tiles + 1):
            v.extend([i*ts-w2,0.,w2,  i*ts-w2,0.,-w2,  -w2,0.,i*ts-w2,  w2,0.,i*ts-w2])
        return vbo.VBO(v)

    def render(self):
        glLineWidth(1.)

        glColor4f(*self.grid_color)

        self._floor_vertex_list.draw(GL_LINES)
        #self._floor_vertex_list.draw(GL_TRIANGLES)

        if 1:
            w2 = self.num_tiles * self.tile_size / 2.
            glBegin(GL_QUADS)
            glColor4f(*self.fill_color)
            glVertex3f(-w2, 0.,  w2)
            glVertex3f( w2, 0.,  w2)
            glVertex3f( w2, 0., -w2)
            glVertex3f(-w2, 0., -w2)
            glEnd()

    def intersection(self, start, direction):
        """ return: 3d-intersection-coordinate, None if no intersection found """

        if start[1] <= 0. and direction[1] <= 0. or start[1] >= 0. and direction[1] >= 0.:
            return None
        else:
            x = -direction[0] * start[1] / direction[1] + start[0]
            y = 0.
            z = -direction[2] * start[1] / direction[1] + start[2]
            return vector.Vector((x, y, z))
