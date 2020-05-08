
require "src.globals"
require "src.spriteref"

io.stdout:setvbuf("no")     -- makes the console output display immediately
show_anim_preview = false   -- debug thing to help draw animations
show_physics = true

local worlds = require "src.worlds"

function love.load()
    love.graphics.setDefaultFilter("nearest", "nearest")
    love.physics.setMeter(GLOBALS.cell_size) --the height of a meter our world
    
	SPRITEREF:load_images_from_disk()
    
    world = worlds.WorldState:new{gravity=15 * GLOBALS.cell_size}
    
    player = world:create_player(32, 20, GLOBALS.cell_size * 0.5, GLOBALS.cell_size * 1.75)
    blocks = {}
    
    local block_layout = {
        {0, 7, 2, 2},
        {1, 9, 1, 1},
        {1, 10, 1, 1},
        {6, 4, 1, 1},
        {7, 4, 1, 1},
        {1, 11, 5, 2},
        {9, 8, 1, 1},
        {10, 8, 1, 1}
    }

    for i, b_layout in ipairs(block_layout) do 
        local block = world:create_block(b_layout[1], b_layout[2], b_layout[3], b_layout[4])
        table.insert(blocks, block)
    end
end

player_pos_2 = {x = GLOBALS.cell_size * 9.5, y = GLOBALS.cell_size * 7.5}
anim_preview = {x = GLOBALS.cell_size * 5, y = GLOBALS.cell_size * 4, scale=4, speed=20}
camera = {x_offset=0, y_offset=0, zoom=GLOBALS.cell_size / 16}

function love.draw ()
    if show_physics then
        world:draw_physics(camera)
    else
        love.graphics.reset()
        
        local str = "Fun Game! " .. tostring(GLOBALS.tick_count) .. " " .. tostring(GLOBALS.render_tick_count)
        love.graphics.print(str, 200, 100)
        
        local player_sprite_2 = SPRITEREF.animate(SPRITEREF.player_b_idles, 20)
        love.graphics.draw(SPRITEREF.img_atlas, 
            player_sprite_2, 
            player_pos_2.x + GLOBALS.cell_size, 
            player_pos_2.y, 0, -2, 2)

        if show_anim_preview and anim_preview then
            local anim_preview_sprite = SPRITEREF.animate(SPRITEREF.anim_preview, anim_preview.speed)
            love.graphics.draw(SPRITEREF.img_atlas, anim_preview_sprite, anim_preview.x, anim_preview.y, 0, 
                anim_preview.scale, anim_preview.scale)
        end

        player:draw(camera)

        for _, block in ipairs(blocks) do
            if block:get_sprite() then
                love.graphics.draw(
                    SPRITEREF.img_atlas, 
                    block:get_sprite(), 
                    block.body:getX() - block.w / 2, 
                    block.body:getY() - block.h / 2, 0, GLOBALS.cell_size / 16, GLOBALS.cell_size / 16)
            end
        end
    end
end

function love.update(dt)
    local full_update = GLOBALS:update(dt)
    
    if show_anim_preview and anim_preview and (GLOBALS.tick_count % 60) == 0 then
        print("reloading sprites...")
        if not pcall(SPRITEREF.load_images_from_disk, SPRITEREF) then
            print("FAILED!")
        end
    end
    
    if love.keyboard.isDown("f5") then
        show_physics = not show_physics 
    end
    
    if full_update then
        player:update()
    end

    if full_update then
        world:update(1 / GLOBALS.tick_fps)
    end
end
