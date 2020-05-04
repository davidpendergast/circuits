
SPRITEREF = {}

SPRITEREF.img_atlas = nil

function SPRITEREF.load_images_from_disk(self)
    -- TODO OS-safe paths
    self.img_atlas = love.graphics.newImage("assets/circuits.png") 
    
    local offs = {x = 0, y = 0}
    local img = self.img_atlas
    
    local function make_quad(x, y, w, h) 
        return love.graphics.newQuad(x + offs.x, y + offs.y, w, h, img:getDimensions()) 
    end
    
    local function make_quads(x, y, w, h, n)
        local res = {}
        for i=1,n do
           table.insert(res, make_quad(x + (i - 1) * w, y, w, h))
        end
        return res
    end
    
    self.player_a_idles = make_quads(0, 0, 16, 32, 2)
    self.player_b_idles = make_quads(0, 48, 16, 16, 2)
    self.player_c_idles = make_quads(0, 64, 32, 32, 2)
    self.player_d_idles = make_quads(0, 96, 16, 32, 2)
    self.player_d_flying = make_quads(32, 96, 16, 32, 6)
    
    self.blocks_1x1 = make_quads(0, 208, 16, 16, 2)
    self.blocks_2x2 = make_quads(0, 224, 32, 32, 1)
    self.blocks_5x2 = make_quads(0, 288, 5*16, 32, 1)
end

function SPRITEREF.animate(frames, frame_time)
   return frames[1 + (math.floor(GLOBALS.tick_count / frame_time) % #frames)]
end

function SPRITEREF.get_block_sprite(w, h, seed)
    local sprites = nil
    if w == 1 and h == 1 then
        sprites = SPRITEREF.blocks_1x1
    elseif w == 2 and h == 2 then
        sprites = SPRITEREF.blocks_2x2
    elseif w == 5 and h == 2 then
        sprites = SPRITEREF.blocks_5x2
    end
    
    if sprites and #sprites > 0 then
        return sprites[1 + (seed % #sprites)]
    else
        return nil
    end
end