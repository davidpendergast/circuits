
local world = {}  -- the namespace

world.USERDATA_SENSOR_ID = "sensor_id"
world.USERDATA_ENTITY_TYPE = "entity_type"

world.USERDATA_ENTITY_BLOCK = "block"
world.USERDATA_ENTITY_PLAYER = "player"

world.WorldState = {        -- the prototype
    all_entities = {},      -- ent_id -> Entity
    box2d_world = nil,      -- the physics simulation
    sensor_states = {}      -- sensor_id -> number of active collisions
}  

function world.WorldState:new (o)
    o = o or {}
    setmetatable(o, self)
    self.__index = self
    
    o.box2d_world = love.physics.newWorld(0, 9.81 * GLOBALS.cell_size, true)
    o.box2d_world:setCallbacks(
        o:_make_callback3(o._begin_contact),
        o:_make_callback3(o._end_contact),
        o:_make_callback3(o._pre_solve),
        o:_make_callback5(o._post_solve)
    )
    
    return o
end

function world.WorldState:_make_callback3 (func)
    local function res (arg1, arg2, arg3)
        func(self, arg1, arg2, arg3)
    end
    return res
end

function world.WorldState:_make_callback5 (func)
    local function res (arg1, arg2, arg3, arg4, arg5)
        func(self, arg1, arg2, arg3, arg4, arg5)
    end
    return res
end

function world.WorldState:_begin_contact (fix1, fix2, contact)
    self:_handle_potential_sensor_contact(fix1, fix2, true)
    self:_handle_potential_sensor_contact(fix2, fix1, true)
end

function world.WorldState:_handle_potential_sensor_contact(sensor, block, began)
    local sensor_user_data = sensor:getUserData()
    if not sensor_user_data or not sensor_user_data[world.USERDATA_SENSOR_ID] then
        return
    end
    local sensor_id = sensor_user_data[world.USERDATA_SENSOR_ID]
    print("saw sensor collision: ", sensor_id)
    
    local block_user_data = block:getUserData()
    if not block_user_data or block_user_data[world.USERDATA_ENTITY_TYPE] ~= world.USERDATA_ENTITY_BLOCK then
        return
    end
    
    self.sensor_states[sensor_id] = self:get_sensor_val(sensor_id) + (began and 1 or -1)
    print("set ", sensor_id, " to: ", self.sensor_states[sensor_id])
end

function world.WorldState:_end_contact (fix1, fix2, contact)
    self:_handle_potential_sensor_contact(fix1, fix2, false)
    self:_handle_potential_sensor_contact(fix2, fix1, false)
end

function world.WorldState:_pre_solve (fix1, fix2, contact)
    
end

function world.WorldState:_post_solve (fix1, fix2, contact, normal, tangent)
    
end

function world.WorldState:add_entity (ent)
    self.all_entities[ent:get_id()] = ent
end

function world.WorldState:destroy_entity(ent)
    if ent then
        ent:destroy()
        self.all_entities[ent:get_id()] = nil
    end
end

function world.WorldState:update(dt)
    for _, v in ipairs(self.all_entities) do
        v:update()
    end
    if self.box2d_world then
        self.box2d_world:update(dt)
    end
end

function world.WorldState:get_sensor_val (sensor_id)
    if self.sensor_states[sensor_id] then
        return self.sensor_states[sensor_id]
    else
        return 0
    end
end

world.Entity = {
    w = 0,
    h = 0,
    id = 0,
    world = nil,
    body = nil,  -- box2d body
}

function world.Entity:get_id ()
    return self.id
end

function world.Entity:get_body ()
    return self.body
end

function world.Entity:set_body (body)
    self.body = body
end

function world.Entity:set_world (w)
    self.world = w
end

function world.Entity:set_size (w, h)
    self.w = w
    self.h = h
end

function world.Entity:get_size ()
    return self.w, self.h
end

function world.Entity:get_world (w)
    return self.world
end

function world.Entity:get_sprite ()
    return nil
end

function world.Entity:get_rect ()
    local w, h = self:get_size()
    return {0, 0, w, h}  -- TODO
end

function world.Entity:update ()
    
end

_ENT_ID_COUNT = 0

function world.next_ent_id ()
    _ENT_ID_COUNT = _ENT_ID_COUNT + 1
    return _ENT_ID_COUNT - 1
end

function world.Entity:new (o)
    o = o or {}
    setmetatable(o, self)
    self.__index = self
    o.id = world.next_ent_id()
    return o
end

world.PlayerEntity = world.Entity:new()

function world.PlayerEntity:new (o)
    o = o or {}
    setmetatable(o, self)
    self.__index = self
    return o
end

function world.WorldState:create_player (x, y, w, h)
    -- factory method for player entities
    local res = world.PlayerEntity:new()
    res:set_size(w, h)
    res:set_body(love.physics.newBody(self.box2d_world, x - w / 2, y - h / 2, "dynamic"))
    
    res.body:setFixedRotation(true)
    res.shape = love.physics.newRectangleShape(w, h)
    res.fixture = love.physics.newFixture(res.body, res.shape, 1)
    
    -- building the "can I jump" detector
    res.foot_sensor_shape = love.physics.newRectangleShape(0, h-1, w, 2)
    res.foot_sensor_fixture = love.physics.newFixture(res.body, res.foot_sensor_shape)
    res.foot_sensor_fixture:setSensor(true)
    res.foot_sensor_id = "sensor_id_" .. tostring(res:get_id()) .. "foot"
    
    local foot_user_data = {}
    foot_user_data[world.USERDATA_SENSOR_ID] = res.foot_sensor_id
    res.foot_sensor_fixture:setUserData(foot_user_data)
    
    res.sensor_states = {}  -- sensor_id -> collision_count
    
    res:set_world(self)
    self:add_entity(res)
    
    return res
end

function world.PlayerEntity:get_sprite ()
    return SPRITEREF.animate(SPRITEREF.player_a_idles, 20)
end
    
world.BlockEntity = world.Entity:new ({grid_w=0, grid_h=0, rand_seed=0})

function world.BlockEntity:new (o)
    o = o or {}
    setmetatable(o, self)
    self.__index = self
    return o
end
    
function world.WorldState:create_block (grid_x, grid_y, grid_w, grid_h)
    -- factory method for block entities
    local res = world.BlockEntity:new()
    
    local x = grid_x * GLOBALS.cell_size
    local y = grid_y * GLOBALS.cell_size
    local w = grid_w * GLOBALS.cell_size
    local h = grid_h * GLOBALS.cell_size
    
    res:set_size(w, h)
    res:set_body(love.physics.newBody(self.box2d_world, x + w / 2, y + h / 2))
    
    res.body:setFixedRotation(true)
    
    res.shape = love.physics.newRectangleShape(w, h)
    res.fixture = love.physics.newFixture(res.body, res.shape, 1)
    
    local block_user_data = {}
    block_user_data[world.USERDATA_ENTITY_TYPE] = world.USERDATA_ENTITY_BLOCK
    
    res.fixture:setUserData(block_user_data)
    
    res.grid_w = grid_w
    res.grid_h = grid_h
    res.rand_seed = math.floor(love.math.random() * 999)
    
    res:set_world(self)
    self:add_entity(res)
    return res
end

function world.BlockEntity:get_sprite()
    return SPRITEREF.get_block_sprite(self.grid_w, self.grid_h, self.rand_seed)
end


return world