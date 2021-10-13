
_ALL_PARTICLE_TYPES = []


class ParticleType:

    def __init__(self, ident):
        self._id = ident
        _ALL_PARTICLE_TYPES.append(self)

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        return isinstance(other, ParticleType) and other._id == self._id


class ParticleTypes:
    CROSS_TINY = ParticleType("CROSS_TINY")
    CROSS_SMALL = ParticleType("CROSS_SMALL")
    BUBBLES_SMALL = ParticleType("BUBBLES_SMALL")
    BUBBLES_MEDIUM = ParticleType("BUBBLES_MEDIUM")
    BUBBLES_LARGE = ParticleType("BUBBLES_LARGE")

