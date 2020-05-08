
GLOBALS = {}

GLOBALS.time_accum = 0
GLOBALS.render_tick_count = 0

GLOBALS.tick_fps = 30
GLOBALS.tick_count = 0

GLOBALS.cell_size = 48 -- in pixels

function GLOBALS.update(self, dt)
    self.time_accum = self.time_accum + dt  -- TODO fix potential death spiral
    local do_logic_update = false
    if self.time_accum >= 1 / self.tick_fps then
        self.tick_count = self.tick_count + 1
        self.time_accum = self.time_accum - 1 / self.tick_fps
        do_logic_update = true
    end 
    self.render_tick_count = self.render_tick_count + 1
    return do_logic_update
end

