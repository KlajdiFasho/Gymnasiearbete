import displayio
import terminalio
import time
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from Handlers.gamestate import BaseState, STATE_GAME_OVER, STATE_MENU, STATE_PAUSE

# --- PHYSICS CONSTANTS ---
GRAVITY = 600.0
WALK_ACCEL = 400.0
MAX_SPEED = 120.0
MAX_FALL_SPEED = 300.0
FRICTION = 600.0
JUMP_FORCE = -250.0
JUMP_CUT = 0.5
TILE_SIZE = 16

# --- LEVEL DATA ---
LEVEL_MAP = [
    [1]*60, # Ceiling
    [1] + [0]*58 + [1],
    [1] + [0]*58 + [1],
    [1] + [0]*58 + [1],
    [1] + [0]*58 + [1],
    [1] + [0]*58 + [1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1]*60,
    [1]*60,
    [1]*60
]

class Level:
    def __init__(self):
        self.width = len(LEVEL_MAP[0])
        self.height = len(LEVEL_MAP)
        self.pixel_width = self.width * TILE_SIZE
        
        self.palette = displayio.Palette(2)
        self.palette[0] = 0x6B8CFF # Sky
        self.palette[1] = 0x00AA00 # Ground

        self.bitmap = displayio.Bitmap(TILE_SIZE, TILE_SIZE * 2, 2)
        for y in range(TILE_SIZE, TILE_SIZE * 2):
            for x in range(TILE_SIZE):
                self.bitmap[x, y] = 1
        
        self.tilegrid = displayio.TileGrid(
            self.bitmap, 
            pixel_shader=self.palette,
            width=self.width,
            height=self.height,
            tile_width=TILE_SIZE,
            tile_height=TILE_SIZE
        )
        
        for y in range(self.height):
            for x in range(self.width):
                tile_type = LEVEL_MAP[y][x]
                self.tilegrid[x, y] = tile_type
                    
    def is_solid(self, x, y):
        tx = int(x // TILE_SIZE)
        ty = int(y // TILE_SIZE)
        if tx < 0 or tx >= self.width: return True  
        if ty < 0: return False                     
        if ty >= self.height: return True           
        return LEVEL_MAP[ty][tx] == 1

class Player:
    def __init__(self, x, y):
        self.width = 12  
        self.height = 16 
        
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing_right = True
        
        # --- SPRITE MANAGEMENT ---
        self.group = displayio.Group()
        self.sprites = {} 
        
        self.sprite_offset_x = -10 
        
        # FIX: Offset for 32x32 sprite with centered 19px character
        # Visual Bottom = 32 - ((32-19)/2) = 32 - 6.5 = 25.5
        # Hitbox Bottom = 16
        # Offset = 16 - 25.5 = -9.5 (Round to -9)
        self.sprite_offset_y = -9
        
        def load_sprite(name, filename, tile_w=32, tile_h=32):
            try:
                bmp = displayio.OnDiskBitmap(f"/sprites/{filename}")
                pal = bmp.pixel_shader
                
                # TRANSPARENCY FIX:
                if isinstance(pal, displayio.ColorConverter):
                    pal.make_transparent(0xFF00FF) # Magenta
                else:
                    pal.make_transparent(0)        # Index 0
                
                grid = displayio.TileGrid(
                    bmp, 
                    pixel_shader=pal, 
                    tile_width=tile_w, 
                    tile_height=tile_h
                )
                grid.hidden = True
                
                self.group.append(grid)
                self.sprites[name] = {"grid": grid, "frames": bmp.width // tile_w}
                print(f"Loaded {filename} ({bmp.width // tile_w} frames)")
                
            except Exception as e:
                print(f"Failed to load {filename}: {e}")
                fallback = displayio.Bitmap(16, 16, 1)
                fallback_pal = displayio.Palette(1)
                fallback_pal[0] = 0xFF0000
                grid = displayio.TileGrid(fallback, pixel_shader=fallback_pal)
                grid.hidden = True
                self.group.append(grid)
                self.sprites[name] = {"grid": grid, "frames": 1}

        # Load 32x32 Sprites
        load_sprite("run", "run.bmp", 32, 32)
        load_sprite("jump", "jump.bmp", 32, 32)
        load_sprite("slide", "slide.bmp", 32, 32)
        load_sprite("death", "death.bmp", 32, 32)
        
        self.current_anim = "run" 
        self.anim_timer = 0.0
        self.frame_index = 0
        self.set_animation("run")

    def set_animation(self, name):
        if self.current_anim == name: return
        if self.current_anim in self.sprites:
            self.sprites[self.current_anim]["grid"].hidden = True
        self.current_anim = name
        if name in self.sprites:
            self.sprites[name]["grid"].hidden = False
            self.frame_index = 0

    def update(self, handler, dt, level):
        ax, ay = handler.get_axis()

        if abs(ax) > 0.1:
            self.vx += ax * WALK_ACCEL * dt
            self.facing_right = (ax > 0)
        else:
            if self.vx > 0: self.vx = max(0, self.vx - FRICTION * dt)
            elif self.vx < 0: self.vx = min(0, self.vx + FRICTION * dt)

        self.vx = max(min(self.vx, MAX_SPEED), -MAX_SPEED)

        dx = self.vx * dt
        if dx > 14: dx = 14
        elif dx < -14: dx = -14
        self.x += dx
        
        if self.vx > 0: 
            if level.is_solid(self.x + self.width, self.y) or \
               level.is_solid(self.x + self.width, self.y + self.height - 0.1):
                self.x = (int((self.x + self.width) // TILE_SIZE) * TILE_SIZE) - self.width - 0.01
                self.vx = 0
        elif self.vx < 0:
            if level.is_solid(self.x, self.y) or \
               level.is_solid(self.x, self.y + self.height - 0.1):
                self.x = (int(self.x // TILE_SIZE) + 1) * TILE_SIZE + 0.01
                self.vx = 0

        if handler.was_just_pressed("A") and self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False
        if handler.was_just_released("A") and self.vy < 0:
            self.vy *= JUMP_CUT

        self.vy += GRAVITY * dt
        if self.vy > MAX_FALL_SPEED: self.vy = MAX_FALL_SPEED

        dy = self.vy * dt
        if dy > 14: dy = 14
        elif dy < -14: dy = -14
        self.y += dy

        self.on_ground = False 
        if self.vy > 0:
            if level.is_solid(self.x + 2, self.y + self.height) or \
               level.is_solid(self.x + self.width - 2, self.y + self.height):
                self.y = (int((self.y + self.height) // TILE_SIZE) * TILE_SIZE) - self.height
                self.vy = 0
                self.on_ground = True
        elif self.vy < 0:
            if level.is_solid(self.x + 2, self.y) or \
               level.is_solid(self.x + self.width - 2, self.y):
                self.y = (int(self.y // TILE_SIZE) + 1) * TILE_SIZE
                self.vy = 0

        if self.y > 300: 
            self.x, self.y, self.vy = 50, 50, 0

        # --- ANIMATION ---
        new_anim = "run"
        if not self.on_ground:
            new_anim = "jump"
        elif abs(self.vx) > 10:
            if (self.vx > 0 and ax < -0.1) or (self.vx < 0 and ax > 0.1):
                new_anim = "slide"
            else:
                new_anim = "run"
        else:
            new_anim = "run"
            
        self.set_animation(new_anim)
        
        anim_data = self.sprites[self.current_anim]
        
        if self.current_anim == "run" and abs(self.vx) > 10:
            self.anim_timer += dt
            if self.anim_timer > 0.1: 
                self.frame_index = (self.frame_index + 1) % anim_data["frames"]
                self.anim_timer = 0
        elif self.current_anim == "run":
            self.frame_index = 0
            
        active_grid = anim_data["grid"]
        
        self.group.x = int(self.x + self.sprite_offset_x)
        self.group.y = int(self.y + self.sprite_offset_y)
        
        active_grid.flip_x = not self.facing_right
        active_grid[0] = self.frame_index

class PlatformerGame(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        
        self.bg = Rect(0, 0, 340, 260, fill=0x6B8CFF)
        self.root_group.append(self.bg)

        self.world = displayio.Group()
        self.root_group.append(self.world)

        self.level = Level()
        self.world.append(self.level.tilegrid)

        self.player = Player(50, 50)
        self.world.append(self.player.group)

        self.hud = label.Label(
            self.manager.font_game, 
            text="MARIO DEMO", 
            x=10, y=10, 
            color=0xFFFFFF,
            background_color=0x000000
        )
        self.root_group.append(self.hud)
        
        self.camera_x = 0
        self.hud_timer = 0

    def reset(self):
        self.player.x, self.player.y = 50, 50
        self.player.vx, self.player.vy = 0, 0
        self.camera_x = 0
        self.world.x = 0
        self.manager.log("Platformer: Reset")

    def enter(self):
        self.manager.log("Platformer: Resume")

    def update(self, handler, dt):
        self.player.update(handler, dt, self.level)

        # Camera
        CAMERA_LEFT = 100
        CAMERA_RIGHT = 220 
        
        screen_pos_x = self.player.x - self.camera_x
        
        if screen_pos_x > CAMERA_RIGHT:
            self.camera_x += (screen_pos_x - CAMERA_RIGHT)
        elif screen_pos_x < CAMERA_LEFT:
            self.camera_x += (screen_pos_x - CAMERA_LEFT)
            
        max_scroll = self.level.pixel_width - 320
        if self.camera_x < 0: self.camera_x = 0
        if self.camera_x > max_scroll: self.camera_x = max_scroll
        
        self.world.x = -int(self.camera_x)

        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_PAUSE)
            
        self.hud_timer += dt
        if self.hud_timer > 0.5:
            self.hud.text = f"P: {int(self.player.x)}"
            self.hud_timer = 0
