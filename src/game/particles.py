
import src.utils.util as util
import src.game.entities as entities


class ParticleTeleportEffect(entities.Entity):

    def __init__(self, start_sprite, end_sprite, time):
        entities.Entity.__init__(self,
                                 self.start_sprite.x(),
                                 self.end_sprite.y(),
                                 w=start_sprite.width(),
                                 h=start_sprite.height())
        self.start_sprite = start_sprite
        self.end_sprite = end_sprite
        self.total_time = time

        self.t = 0

    def update_start_sprite(self, start_sprite):
        self.start_sprite = start_sprite

    def update_end_sprite(self, end_sprite):
        self.end_sprite = end_sprite

    def get_prog(self):
        return util.bound(self.t / self.total_time, 0, 1)

    def update(self):
        self.t += 1

        if self.t > self.total_time:
            self.get_world().remove_entity(self)

    def all_sprites(self):
        # TODO
        yield self.start_sprite
        yield self.end_sprite

