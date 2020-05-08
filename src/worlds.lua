
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
    o = o or {gravity = 9.81 * GLOBALS.cell_size}
    setmetatable(o, self)
    self.__index = self
    
    o.box2d_world = love.physics.newWorld(0, o.gravity, true)
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

function world.WorldState:draw_physics (camera)
    for _, body in pairs(self.box2d_world:getBodies()) do
        for _, fixture in pairs(body:getFixtures()) do
            love.graphics.reset()
            
            local fixture_data = fixture:getUserData()
            if fixture_data then
                if fixture_data[world.USERDATA_SENSOR_ID] then
                    love.graphics.setColor(1, 0.5, 0.5)
                elseif fixture_data[world.USERDATA_ENTITY_TYPE] == world.USERDATA_ENTITY_BLOCK then
                    love.graphics.setColor(0.5, 0.25, 1)
                elseif fixture_data[world.USERDATA_ENTITY_TYPE] == world.USERDATA_ENTITY_PLAYER then
                    love.graphics.setColor(0.5, 1, 0.5)
                end
            end
            
            local shape = fixture:getShape()
     
            if shape:typeOf("CircleShape") then
                local cx, cy = body:getWorldPoints(shape:getPoint())
                love.graphics.circle("fill", cx,  cy, shape:getRadius())
            elseif shape:typeOf("PolygonShape") then
                love.graphics.polygon("fill", body:getWorldPoints(shape:getPoints()))
            else
                love.graphics.line(body:getWorldPoints(shape:getPoints()))
            end
            
            local bx, by = body:getWorldPoints(0, 0)
            love.graphics.setColor(0, 0, 0)
            love.graphics.circle("fill", bx, by, 2)
        end
    end
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

function world.Entity:get_world (w)
    return self.world
end

function world.Entity:get_sprite ()
    return nil
end

function world.Entity:update ()
    
end

function world.Entity:draw (camera)
    
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
    local res = world.PlayerEntity:new()
    res:set_body(love.physics.newBody(self.box2d_world, x + w / 2, y + h / 2, "dynamic"))
    
    res.body:setFixedRotation(true)
    res.shape = love.physics.newRectangleShape(w, h)
    res.fixture = love.physics.newFixture(res.body, res.shape, 2)
    local main_body_user_data = {}
    main_body_user_data[world.USERDATA_ENTITY_TYPE] = world.USERDATA_ENTITY_PLAYER
    res.fixture:setUserData(main_body_user_data)

    -- building the "can I jump" detector
    res.foot_sensor_shape = love.physics.newRectangleShape(0, h / 2, w - 2, 2)
    res.foot_sensor_fixture = love.physics.newFixture(res.body, res.foot_sensor_shape)
    res.foot_sensor_fixture:setSensor(true)
    res.foot_sensor_id = "sensor_id_" .. tostring(res:get_id()) .. "foot"
    
    local foot_user_data = {}
    foot_user_data[world.USERDATA_SENSOR_ID] = res.foot_sensor_id
    res.foot_sensor_fixture:setUserData(foot_user_data)
    
    -- build left/right sensors
    res.left_sensor_shape = love.physics.newRectangleShape(-w / 2, 0, 2, 0.8 * h)
    res.left_sensor_fixture = love.physics.newFixture(res.body, res.left_sensor_shape)
    res.left_sensor_fixture:setSensor(true)
    res.left_sensor_id = "sensor_id_" .. tostring(res:get_id()) .. "left"
    
    local left_user_data = {}
    left_user_data[world.USERDATA_SENSOR_ID] = res.left_sensor_id
    res.left_sensor_fixture:setUserData(left_user_data)
    
    res.right_sensor_shape = love.physics.newRectangleShape(w / 2, 0, 2, 0.8 * h)
    res.right_sensor_fixture = love.physics.newFixture(res.body, res.right_sensor_shape)
    res.right_sensor_fixture:setSensor(true)
    res.right_sensor_id = "sensor_id_" .. tostring(res:get_id()) .. "right"
    
    local right_user_data = {}
    right_user_data[world.USERDATA_SENSOR_ID] = res.right_sensor_id
    res.right_sensor_fixture:setUserData(right_user_data)
    
    res.sensor_states = {}  -- sensor_id -> collision_count
    
    res.jump_cooldown = 0
    res.jump_max_cooldown = 20
    res.facing_right = true
    res.crouching = false
    
    res.max_x_vel = 4
    res.min_x_vel = 1
    res.x_accel = 0.25
    
    res:set_world(self)
    self:add_entity(res)
    
    return res
end

function world.PlayerEntity:get_sprite ()
    if self:is_airborne() then
        if self:is_left_walled() or self:is_right_walled() then
            return SPRITEREF.animate(SPRITEREF.player_a_wallslides, 20)
        else
            return SPRITEREF.animate(SPRITEREF.player_a_airbornes, 20)
        end
    elseif self:is_crouching() then
        return SPRITEREF.animate(SPRITEREF.player_a_crouching, 20)
    else
        return SPRITEREF.animate(SPRITEREF.player_a_idles, 20)
    end
end

function world.PlayerEntity:is_airborne ()
    return self:get_world():get_sensor_val(self.foot_sensor_id) == 0
end

function world.PlayerEntity:is_left_walled ()
    return self:get_world():get_sensor_val(self.left_sensor_id) > 0
end

function world.PlayerEntity:is_right_walled ()
    return self:get_world():get_sensor_val(self.right_sensor_id) > 0
end

function world.PlayerEntity:is_crouching ()
    return self.crouching and not self:is_airborne()
end

function world.PlayerEntity:can_jump ()
    return not self:is_airborne() and self.jump_cooldown <= 0
end

function world.PlayerEntity:do_jump ()
    self.jump_cooldown = self.jump_max_cooldown
end

function world.PlayerEntity:update ()
    local go_left = love.keyboard.isDown("left") or love.keyboard.isDown("a")
    local go_right = love.keyboard.isDown("right") or love.keyboard.isDown("d")
    local dx = 0
    if go_left then dx = dx - 1 end
    if go_right then dx = dx + 1 end
    
    if self:is_airborne() then
        self.body:applyForce(dx * 300, 0)
    else
        self.body:applyForce(dx * 700, 0)
    end
        
    if love.keyboard.isDown("up") or love.keyboard.isDown("w") then
        if self:can_jump() then
            self.body:applyLinearImpulse(0, -400)
        end
    end
    
    self.crouching = love.keyboard.isDown("s") or love.keyboard.isDown("down")
    
    local x_vel, _ = self.body:getLinearVelocity()
    if x_vel < -0.15 then
        self.facing_right = false
    elseif x_vel > 0.15 then
        self.facing_right = true
    end
end

function world.PlayerEntity:draw (camera)
    local sprite = self:get_sprite()
    
    local center_x = self.body:getX() - camera.x_offset
    local bottom_y = self.body:getY() + self.h / 2 - camera.y_offset
    local xflip = self.facing_right and 1 or -1
    
    if sprite then
        local _, _, spr_w, spr_h = sprite:getViewport()
        love.graphics.draw(
            SPRITEREF.img_atlas, 
            sprite, 
            center_x - xflip * spr_w / 2 * camera.zoom, 
            bottom_y - spr_h * camera.zoom, 0, xflip * camera.zoom, camera.zoom)
    end
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