import numpy


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


