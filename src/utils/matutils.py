import numpy
import math

import src.utils.util as util


def translation_matrix(xyz_trans, mat=None):
    res = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
    for i in range(0, len(xyz_trans)):
        res.itemset((i, 3), float(xyz_trans[i]))
    return res


def scale_matrix(xyz_scale, mat=None):
    res = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
    for i in range(0, len(xyz_scale)):
        res.itemset((i, i), float(xyz_scale[i]))
    return res


def xrot_matrix(xrot):
    Rx = numpy.identity(4, dtype=numpy.float32)
    Rx.itemset((1, 1), math.cos(xrot))
    Rx.itemset((2, 1), -math.sin(xrot))
    Rx.itemset((1, 2), math.sin(xrot))
    Rx.itemset((2, 2), math.cos(xrot))
    return Rx


def yrot_matrix(yrot):
    Ry = numpy.identity(4, dtype=numpy.float32)
    Ry.itemset((0, 0), math.cos(yrot))
    Ry.itemset((2, 0), math.sin(yrot))
    Ry.itemset((0, 2), -math.sin(yrot))
    Ry.itemset((2, 2), math.cos(yrot))
    return Ry


def zrot_matrix(zrot):
    Rz = numpy.identity(4, dtype=numpy.float32)
    Rz.itemset((0, 0), math.cos(zrot))
    Rz.itemset((1, 0), -math.sin(zrot))
    Rz.itemset((0, 1), math.sin(zrot))
    Rz.itemset((1, 1), math.cos(zrot))
    return Rz


def rotation_matrix(xyz_rot, mat=None):
    res = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
    Rx = xrot_matrix(xyz_rot[0] if len(xyz_rot) >= 1 else 0)
    Ry = yrot_matrix(xyz_rot[1] if len(xyz_rot) >= 2 else 0)
    Rz = zrot_matrix(xyz_rot[2] if len(xyz_rot) >= 3 else 0)
    Rxyz = Rx.dot(Ry).dot(Rz)
    for i in range(0, 9):
        ij = (i % 3, i // 3)
        res.itemset(ij, Rxyz[ij[0]][ij[1]])
    return res


def ortho_matrix(left, right, bottom, top, near_val, far_val):
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 0), float(2 / (right - left)))
    res.itemset((1, 1), float(2 / (top - bottom)))
    res.itemset((2, 2), float(-2 / (far_val - near_val)))

    t_x = -(right + left) / (right - left)
    t_y = -(top + bottom) / (top - bottom)
    t_z = -(far_val + near_val) / (far_val - near_val)
    res.itemset((0, 3), float(t_x))
    res.itemset((1, 3), float(t_y))
    res.itemset((2, 3), float(t_z))

    return res


# yoinked from OpenGL's gluPerspective
def perspective_matrix(fovy, aspect, z_near, z_far):
    f = 1 / math.tan(fovy / 2)
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 0), f / aspect)
    res.itemset((1, 1), f)
    res.itemset((2, 2), (z_far + z_near) / (z_near - z_far))
    res.itemset((3, 2), (2 * z_far * z_near) / (z_near - z_far))
    res.itemset((2, 3), -1)
    res.itemset((3, 3), 0)
    return res


# yoinked from gluLookAt
def get_matrix_looking_at(eye_xyz, target_xyz, up_vec):
    F = (
        target_xyz[0] - eye_xyz[0],
        target_xyz[1] - eye_xyz[1],
        target_xyz[2] - eye_xyz[2]
    )
    f = util.set_length(F, 1)
    up_norm = util.set_length(up_vec, 1)
    s = util.cross_prod(f, up_norm)
    u = util.cross_prod(s, f)
    res = numpy.array([[s[0], s[1], s[2], 0],
                       [u[0], u[1], u[2], 0],
                       [-f[0], -f[1], -f[2], 0],
                       [0, 0, 0, 1]])
    return res

