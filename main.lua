
require "src.globals"
require "src.spriteref"

local worldfactory = require "src.world"

function love.load()
    love.graphics.setDefaultFilter("nearest", "nearest")
    
	SPRITEREF:load_images_from_disk()
    
    world = worldfactory.new_world()
    
    player = worldfactory.new_player_a(world)
    player.body:setX(32)
    player.body:setY(20)
    
    local block_layout = {
        {0, 7, 2, 2},
        {1, 9, 1, 1},
        {1, 10, 1, 1},
        {1, 11, 5, 2},
        {9, 8, 1, 1},
        {10, 8, 1, 1}
    }
    
    blocks = {}
    
    for i, b_layout in ipairs(block_layout) do 
        local block = worldfactory.new_block(world, b_layout[3], b_layout[4])
        block.body:setX(GLOBALS.cell_size * b_layout[1] + block.w / 2)
        block.body:setY(GLOBALS.cell_size * b_layout[2] + block.h / 2)
        table.insert(blocks, block)
    end
end

player_pos_2 = {x = GLOBALS.cell_size * 9.5, y = GLOBALS.cell_size * 7}

function love.draw()
    local str = "Fun Game! " .. tostring(GLOBALS.tick_count) .. " " .. tostring(GLOBALS.render_tick_count)
    love.graphics.print(str, 200, 100)
    
    local player_sprite_2 = SPRITEREF.animate(SPRITEREF.player_b_idles, 20)
    love.graphics.draw(SPRITEREF.img_atlas, player_sprite_2, player_pos_2.x + GLOBALS.cell_size, player_pos_2.y, 0, -3, 3)

    if player:get_current_sprite() then
        love.graphics.draw(
            SPRITEREF.img_atlas, 
            player:get_current_sprite(), 
            player.body:getX() - player.w / 2, 
            player.body:getY() - player.h / 2, 0, GLOBALS.cell_size / 16, GLOBALS.cell_size / 16)
    end

    for i, block in ipairs(blocks) do
        if block:get_current_sprite() then
            love.graphics.draw(
                SPRITEREF.img_atlas, 
                block:get_current_sprite(), 
                block.body:getX() - block.w / 2, 
                block.body:getY() - block.h / 2, 0, GLOBALS.cell_size / 16, GLOBALS.cell_size / 16)
        end
    end
    
end

function love.update(dt)
    local full_update = GLOBALS:update(dt)
    
    if love.keyboard.isDown("right") or love.keyboard.isDown("d") then
        player.body:applyForce(400, 0)
    elseif love.keyboard.isDown("left") or love.keyboard.isDown("a") then
        player.body:applyForce(-400, 0)
    end
    
    if love.keyboard.isDown("up") or love.keyboard.isDown("w") then
        player.body:applyForce(0, -1000)
    end

    
    if full_update then
        world:update(1 / GLOBALS.tick_fps)
    end
end
