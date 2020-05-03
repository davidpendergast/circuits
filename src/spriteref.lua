
SPRITEREF = {}

SPRITEREF.img_atlas = nil

function SPRITEREF.load_images_from_disk(self)
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
    
    print("player_a_idles[1] = ", tostring(self.player_a_idles[1]))
end