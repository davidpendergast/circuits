
local mod = {}

function mod.new_world()
    love.physics.setMeter(GLOBALS.cell_size) --the height of a meter our worlds
    return love.physics.newWorld(0, 9.81 * GLOBALS.cell_size, true)
end

function mod.new_entity(world, x, y, w, h, body_type)
    local res = {}
    res.body = love.physics.newBody(world, x - w / 2, y - h / 2, body_type)
    res.shape = love.physics.newRectangleShape(w, h)
    res.body:setFixedRotation(true)
    res.w = w
    res.h = h
    
    function res.get_current_sprite(self)
        return nil
    end
    return res
end

function mod.new_player_a(world)
    local res = mod.new_entity(world, 0, 0, GLOBALS.cell_size, GLOBALS.cell_size * 2, "dynamic")
    res.fixture = love.physics.newFixture(res.body, res.shape, 1)
    
    function res.get_current_sprite(self)
        return SPRITEREF.animate(SPRITEREF.player_a_idles, 20)
    end
    return res
end

function mod.new_block(world, w, h)
    local res = mod.new_entity(world, 0, 0, w * GLOBALS.cell_size, h * GLOBALS.cell_size)
    res.fixture = love.physics.newFixture(res.body, res.shape)
    
    res.block_w = w
    res.block_h = h
    res.rand_seed = math.floor(love.math.random() * 999)
    
    function res.get_current_sprite(self)
        return SPRITEREF.get_block_sprite(self.block_w, self.block_h, self.rand_seed)
    end
        
    return res
end

return mod