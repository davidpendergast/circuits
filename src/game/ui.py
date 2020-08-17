import src.utils.util as util


_ELEMENT_UID_COUNT = 0


def _get_next_uid():
    global _ELEMENT_UID_COUNT
    _ELEMENT_UID_COUNT += 1
    return _ELEMENT_UID_COUNT - 1


class UiElement:

    def __init__(self):
        self.uid = _get_next_uid()
        self._parent = None
        self._children = []

        self._rel_xy = (0, 0)  # position relative to parent

    def update(self):
        raise NotImplementedError()

    def all_sprites(self):
        raise NotImplementedError()

    def get_size(self):
        raise NotImplementedError()

    def all_sprites_from_self_and_kids(self):
        for c in self._children:
            for spr in c.all_sprites_from_self_and_kids():
                yield spr
        for spr in self.all_sprites():
            yield spr

    def update_self_and_kids(self):
        self.update()
        for c in self._children:
            c.update()

    def get_rect(self, absolute=False):
        xy = self.get_xy(absolute=absolute)
        size = self.get_size()
        return (xy[0], xy[1], size[0], size[1])

    def get_xy(self, absolute=False):
        if absolute and self._parent is not None:
            return util.add(self._parent.get_xy(absolute=True), self._rel_xy)
        else:
            return self._rel_xy

    def set_xy(self, rel_xy):
        self._rel_xy = rel_xy

    def add_child(self, element):
        element.set_parent(self)

    def add_children(self, elements):
        for e in elements:
            e.set_parent(self)

    def remove_child(self, element):
        if element in self._children:
            element.set_parent(None)
        else:
            print("WARN: tried to remove non-child: child={}".format(element))

    def remove_children(self, elements):
        for e in elements:
            self.remove_child(e)

    def get_parent(self):
        return self._parent

    def set_parent(self, element):
        if self._parent is not None:
            if self in self._parent._children:
                self._parent._children.remove(self)
            else:
                print("WARN: child element was disconnected from parent: child={}, parent={}".format(self, self._parent))
        self._parent = element
        if self._parent is not None:
            if self not in self._parent._children:
                self._parent._children.append(self)
            else:
                print("WARN: parent element already has reference to child?: child={}, parent={}".format(self, self._parent))

    def dfs(self, cond):
        for element in self.depth_first_traverse():
            if cond(element):
                return element
        return None

    def depth_first_traverse(self, include_self=True):
        for c in self._children:
            for element in c._children:
                yield element
        if include_self:
            yield self

    def __eq__(self, other):
        if isinstance(other, UiElement):
            return self.uid == other.uid
        else:
            return None

    def __hash__(self):
        return self.uid


class ElementGroup(UiElement):

    def __init__(self):
        UiElement.__init__(self)

    def get_size(self):
        my_xy = self.get_xy(absolute=True)
        x_size = 0
        y_size = 0
        for c in self.depth_first_traverse(include_self=False):
            c_xy = c.get_xy(absolute=True)
            c_size = c.get_size()
            x_size = max(x_size, c_xy[0] - my_xy[0] + c_size[0])
            y_size = max(y_size, c_xy[1] - my_xy[1] + c_size[1])
        return (x_size, y_size)

    def all_sprites(self):
        return []