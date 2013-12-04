"""
3d vector class

some sites i used for reference and ideas:

http://www.python.org/doc/2.2.3/ref/numeric-types.html
http://ccl.osc.edu/cca/software/SOURCES/PYTHON/HINSEN/Vector.shtml
"""

#import timeit
import math


# def set(self, v):
# def reset(self):
# def new(self):
# def len(self):
# def len2(self):
# def normal(self):
# def normalize(self):
# def rotate(self, normal, angle):
# def angle(self, vector):
# def cross(self, other):
# def dot(self, other):
# def reflection(self, plane_normal):
# def dist(self, other):
# def dist2(self, other):


class Vector:
    """
    3d vector class.

    only the methods normalize() &amp; rotate() modify the current vector.
    v.normalize() :: is faster than :: v = v.normal()

    ----

    operators are three times slower than non-returning, direct-modifying class
    methods.

    for example:

    def add2(self, other):
        s, o = self.data, other.data
        s[0] += o[0]
        s[1] += o[1]
        s[2] += o[2]

    -1- takes 10.4 seconds for 100 000 calls (duron 800MHz)
    v += v2 + v2 + v2 + v2  # 10.4

    -2- takes 3.3 seconds for 100 000 calls
    v.add2(v2)
    v.add2(v2)
    v.add2(v2)
    v.add2(v2)
    """

    def __init__(self, (x, y, z) = (0., 0., 0.)):
        self.data = [float(x), float(y), float(z)]

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        s = self.data
        return 'Vector((%s,%s,%s))' % (`s[0]`, `s[1]`, `s[2]`)

    def set(self, v):
        """use v1.set(v2) instead of v1 = v2.
        python is only copying references. look for copy module."""
        self.data[0] = v[0] ; self.data[1] = v[1] ; self.data[2] = v[2]

    def reset(self):
        self.data[0] = 0. ; self.data[1] = 0. ; self.data[2] = 0.

    def new(self):
        """return a copy of current vector. alternatively, you could use:
        import copy
        v2 = copy.deepcopy(v)
        """
        return Vector( (self.data[0], self.data[1], self.data[2]) )


    # no need for __radd__, __rsub__. can't think of any possible situation


    def __add__(self, other):
        s, o = self.data, other.data
        return Vector( (s[0] + o[0], s[1] + o[1], s[2] + o[2]) )

    def __sub__(self, other):
        s, o = self.data, other.data
        return Vector( (s[0] - o[0], s[1] - o[1], s[2] - o[2]) )

    def __neg__(self):
        s = self.data
        return Vector( (-s[0], -s[1], -s[2]) )

    def __mul__(self, n):
        s = self.data
        return Vector( (s[0] * n, s[1] * n, s[2] * n) )

    def __rmul__(self, n):
        s = self.data
        return Vector( (s[0] * n, s[1] * n, s[2] * n) )

    def __div__(self, n):
        s = self.data
        return Vector( (s[0] / n, s[1] / n, s[2] / n) )

    def __eq__(self, other):
        return self.data == other.data

    def __ne__(self, other):
        return self.data != other.data

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, v):
        self.data[i] = float(v)


    def add(self, other):
        if isinstance(other, Vector):
            s, o = self.data, other.data
            s[0] += o[0]
            s[1] += o[1]
            s[2] += o[2]
        else:
            s = self.data
            s[0] += other[0]
            s[1] += other[1]
            s[2] += other[2]

    def len(self):
        s = self.data
        return math.sqrt(s[0] * s[0] + s[1] * s[1] + s[2] * s[2])

    def len2(self):
        s = self.data
        return s[0] * s[0] + s[1] * s[1] + s[2] * s[2]

    def normal(self):
        """return a normalized vector"""
        l = self.len()
        if l == 0.:
            return Vector((1., 0., 0.))
            #raise ZeroDivisionError, "can't normalize a zero-length vector"
        s = self.data
        return Vector( (s[0] / l, s[1] / l, s[2] / l) )

    def normalize(self):
        """normalize current vector. no return"""
        l = self.len()
        if l == 0:
            raise ZeroDivisionError, "can't normalize a zero-length vector"
        s = self.data
        s[0] /= l; s[1] /= l; s[2] /= l

    def rotate(self, normal, angle):
        """rotate angle degrees around normal.
        normal - has to be a unit vector?"""
        c = math.cos( math.radians(-angle) )
        s = math.sin( math.radians(-angle) )

        #assert(rNormal.IsUnitLength());

        # A - normal
        # V - vector or point that's being rotated

        # this is THE equation
        # c * V + (1 - c) * (A dot V) * A + s * (A cross V);

        # uncomment the next line &amp; comment every following. BUT! the next line
        # is 4.5 times slower than all the following lines together.
        #self.data = c * self + (1 - c) * normal.dot(self) * normal + s * normal.cross(self)

        dot  = self.dot(normal)
        vect = self.cross(normal)

        o = self.data; n = normal.data; v = vect.data
        o[0] = c * o[0] + (1.0 - c) * dot * n[0] + s * v[0]
        o[1] = c * o[1] + (1.0 - c) * dot * n[1] + s * v[1]
        o[2] = c * o[2] + (1.0 - c) * dot * n[2] + s * v[2]


    def angle(self, vector):
        """
        return the angle between two vectors. degrees.
        both vectors HAVE to be unit-length.. maybe.
        """
        return math.degrees( math.acos(self.dot(vector) / (self.len() * vector.len())) )

    def cross(self, other):
        """
        right-handed cross-product in a left-handed space
        x - right, y - up, z - forward
        """

        s, o = self.data, other.data
        return Vector((s[2] * o[1] - s[1] * o[2], \
                       s[0] * o[2] - s[2] * o[0], \
                       s[1] * o[0] - s[0] * o[1]))

    #def cross(self, other):
    #    s, o = self.data, other.data
    #    return Vector((s[1] * o[2] - s[2] * o[1], \
    #                   s[2] * o[0] - s[0] * o[2], \
    #                   s[0] * o[1] - s[1] * o[0]))

    def dot(self, other):
        """dot product. project 'other' vector onto 'self'.
        or alternatively: world space -&gt; object space"""
        s, o = self.data, other.data
        return s[0] * o[0] + s[1] * o[1] + s[2] * o[2]

    def reflection(self, plane_normal):
        """return the reflected vector
        plane_normal - has to be a unit vector?"""
        return (self - plane_normal * 2.0 * self.dot(plane_normal)) * self.len()

        #assert(rPlaneNormal.IsUnitLength()); // DEBUG
        #return (*this - rPlaneNormal * 2.0f * (DotProd(rPlaneNormal))) * Length();

    def dist(self, other):
        s, o = self.data, other.data
        x, y, z = o[0] - s[0], o[1] - s[1], o[2] - s[2]
        return math.sqrt(x*x + y*y + z*z)


    def dist2(self, other):
        s, o = self.data, other.data
        x, y, z = o[0] - s[0], o[1] - s[1], o[2] - s[2]
        return x*x + y*y + z*z
