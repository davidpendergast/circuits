
require "src.globals"
require "src.spriteref"

function love.load()
    love.graphics.setDefaultFilter("nearest", "nearest")
    
	SPRITEREF:load_images_from_disk()
end

player_pos = {x = 32, y = 128}

function love.draw()
    local str = "Fun Game! " .. tostring(GLOBALS.tick_count) .. " " .. tostring(GLOBALS.render_tick_count)
    love.graphics.print(str, 200, 100)
    
    local player_sprite = SPRITEREF.player_a_idles[1 + (math.floor(GLOBALS.tick_count / 20) % #SPRITEREF.player_a_idles)]
    love.graphics.draw(SPRITEREF.img_atlas, player_sprite, player_pos.x, player_pos.y, 0, 4, 4)
end

function love.update(dt)
    GLOBALS:update(dt)
end
