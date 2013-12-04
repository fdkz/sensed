from OpenGL import GL
from ctypes import c_float
#from ctypes import c_float, c_void_p

class VBO:
    def __init__(self, vertices):
        #pyglet.graphics.vertex_list((ntiles+1) * 4, ('v3f/static', v))

        self.num_vertices = len(vertices) / 3
        self.vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, len(vertices)*4, (c_float*len(vertices))(*vertices), GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def draw(self, elemtype):
        """ elemtype: GL_LINES, GL_TRIANGLES, .. """
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, None)
        GL.glDrawArrays(elemtype, 0, self.num_vertices)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)


# class VBOIndexed:
#     def __init__(self, indices, vertices_with_normals):
#         """ vertices_with_normals : interlaced """
#         self.num_vertices = len(vertices) / 3
#         GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
#         self.vbo = GL.glGenBuffers(1)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
#         GL.glBufferData(GL.GL_ARRAY_BUFFER, len(vertices)*4, (c_float*len(vertices))(*vertices), GL.GL_STATIC_DRAW)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

#     def draw(self, elemtype):
#         """ elemtype: GL_LINES, GL_TRIANGLES, .. """
#         stride = 3*4
#         n_offset = c_void_p(stride)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
#         GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)
#         GL.glNormalPointer(GL.GL_FLOAT, stride, n_offset)
#         GL.glDrawArrays(elemtype, 0, self.num_vertices)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

#         #glDrawElements( GL_TRIANGLES, len( self.indices ), GL_UNSIGNED_SHORT, self.indices )
