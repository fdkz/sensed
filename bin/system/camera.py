# update: 2012.07.15

import math

from pyglet.gl import *

import coordinate_system
import vector

class Camera:
    """
    camera = Camera()
    camera.mode = Camera.ORTHOGONAL
    camera.set_window_size(800, 600)

    camera.set_opengl_projection()
    .. draw 3d stuff ..

    camera.set_opengl_pixel_projection()
    sx, sy, sz = camera.screenspace(vector)
    .. draw text/icons at pixel (sx, sy) with depth sz ..

    -----------------------

    forward-z should be positive, unlike in opengl.. methods like
    screenspace, window_ray.. may not work otherwise. don't know.
    """
    ORTHOGONAL  = 1 # screen center is (0, 0)
    PERSPECTIVE = 2
    PIXEL       = 3 # top-left is (0, 0). (top-left tip of the top-left pixel)

    def __init__(self, pixel_aspect_w_h=1.):
        self.mode = self.PIXEL
        self.pixel_aspect_w_h = pixel_aspect_w_h

        self.USE_FRUSTUM = 0
        # read-only from here

        self.fovx      = 0.
        self.fovy      = 0.
        self.tanfovx_2 = 0.
        self.tanfovy_2 = 0.
        self.orthox    = 5000. # window width in opengl units
        self.orthoy    = 5000.
        self.set_fovx(40.)
        #self.set_fovx(80.)
        self.set_fovy(80.)

        self.z_near = 50.
        self.z_far  = 500. * 1000.

        # experimental. projection screen offset, represented as x/z.
        # if equal to self._tanfovx_2 * 2, extends the screen seamlessly to the right.
        # works only if self.mode == self.PERSPECTIVE
        # TODO: add to self.screenspace(..)
        self.screen_tanxofs = 0.
        self.screen_tanyofs = 0.

    def set_fovx(self, fovx):
        self.fovx = float(fovx)
        self.tanfovx_2 = math.tan(math.radians(self.fovx / 2.))

    def set_fovy(self, fovy):
        self.fovy = fovy
        self.tanfovy_2 = math.tan(math.radians(self.fovy / 2.))

    def update_fovx(self, w_h):
        """
        keep fovy and orthoy as they are and recalculate fovx and orthox
        according to window size and pixel aspect ratio.

        w_h - window width divided by window height (in pixels)
        """
        physical_window_w_h = w_h * self.pixel_aspect_w_h

        self.tanfovx_2 = self.tanfovy_2 * physical_window_w_h
        self.fovx      = math.degrees(2. * math.atan(self.tanfovx_2))
        self.orthox    = self.orthoy * physical_window_w_h

    def update_fovy(self, w_h):
        physical_window_w_h = w_h * self.pixel_aspect_w_h

        self.tanfovy_2 = self.tanfovx_2 / physical_window_w_h
        self.fovy      = math.degrees(2. * math.atan(self.tanfovy_2))
        self.orthoy    = self.orthox / physical_window_w_h

    def set_orthox(self, orthox):
        self.orthox = float(orthox)

    def set_orthoy(self, orthoy):
        self.orthoy = float(orthoy)

    def set_opengl_projection(self, projection_mode, w_pixels, h_pixels, z_near=50., z_far=500*1000.):
        """
        projection_mode - self.ORTHOGONAL, self.PIXEL, self.PERSPECTIVE
        """
        self.z_near = z_near
        self.z_far  = z_far

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        if projection_mode == self.ORTHOGONAL:
            glOrtho(-self.orthox / 2., self.orthox / 2., \
                    -self.orthoy / 2., self.orthoy / 2., z_near, z_far)
        elif projection_mode == self.PIXEL:
            glOrtho(0., w_pixels, h_pixels, 0., z_near, z_far)
        elif projection_mode == self.PERSPECTIVE:
            left   = self.z_near * (self.screen_tanxofs - self.tanfovx_2)
            right  = self.z_near * (self.screen_tanxofs + self.tanfovx_2)
            bottom = self.z_near * (self.screen_tanyofs - self.tanfovy_2)
            top    = self.z_near * (self.screen_tanyofs + self.tanfovy_2)
            glFrustum(left, right, bottom, top, self.z_near, self.z_far)

            # these three are equivalent
            #glFrustum(-self.z_near * self.tanfovx_2, self.z_near * self.tanfovx_2,
            #          -self.z_near * self.tanfovy_2, self.z_near * self.tanfovy_2,
            #          self.z_near, self.z_far)
            #gluPerspective(self.fovy, self.tanfovx_2 / self.tanfovy_2, self.z_near, self.z_far)
            #gluPerspective(self.fovy, w_pixels / h_pixels * self.pixel_aspect_w_h, z_near, z_far)

    def screenspace(self, projection_mode, vect, w_pixels, h_pixels):
        """
        return values for current projection mode..

        project vect (has to be already in camera-space) to screen-space
        return: (0, 0, z) in pixels. up-left of the given window

        the returned z: vect.z if the camera is in orthogonal projection
        mode. if in perspective mode, return modified vect.z that generates
        the same z-buffer values in pixel-projection that vect.z would
        generate in perspective projection mode.

        (glOrtho & glFrustum (gluPerspective) use z-buffer differently)

        beware that vect.z has to be positive ( vect[2] > 0 )
        """
        if projection_mode == self.ORTHOGONAL:
            return  w_pixels / self.orthox * vect[0] + w_pixels / 2., \
                   -h_pixels / self.orthoy * vect[1] + h_pixels / 2., vect[2]
        elif projection_mode == self.PERSPECTIVE:
            sx =  vect[0] * (w_pixels / 2.) / vect[2] / self.tanfovx_2 + w_pixels / 2.
            sy = -vect[1] * (h_pixels / 2.) / vect[2] / self.tanfovy_2 * self.pixel_aspect_w_h + h_pixels / 2.
            sz = self.z_far + self.z_near - self.z_far * self.z_near / vect[2]
            return sx, sy, sz

    def window_ray(self, projection_mode, w_pixels, h_pixels, x, y):
        """
        return a ray that goes through the given pixel-coordinate,
        in camera-space. NOT normalized.

        return: start, direction (vectors. world-space coordinates)
                ("start" is necessary in case of orthogonal projection)
        """
        if projection_mode == self.ORTHOGONAL:
            # TODO: untested
            xx = self.orthox * (float(x) / w_pixels - .5)
            yy = self.orthoy * (float(y) / h_pixels - .5)
            zz = 1.
            return vector.Vector((xx, -yy, 0.)), vector.Vector((0., 0., zz))
        elif projection_mode == self.PERSPECTIVE:
            #  TODO: aspect ratio.. or already in tanfov*?
            xx = x - w_pixels / 2.
            yy = (y - h_pixels / 2.) * w_pixels / h_pixels * self.tanfovy_2 / self.tanfovx_2
            zz = w_pixels / 2. / self.tanfovx_2
            return vector.Vector(), vector.Vector((xx, -yy, zz))
        return None, None
