
GLOBALS = {}

GLOBALS.time_accum = 0
GLOBALS.render_tick_count = 0

GLOBALS.tick_fps = 30
GLOBALS.tick_count = 0

function GLOBALS.update(self, dt)
    self.time_accum = self.time_accum + dt
    if self.time_accum >= 1 / self.tick_fps then
        self.tick_count = self.tick_count + 1
        self.time_accum = self.time_accum - 1 / self.tick_fps
    end 
    self.render_tick_count = self.render_tick_count + 1
end

