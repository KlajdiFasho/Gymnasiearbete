import displayio
import terminalio
import time
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from Handlers.gamestate import BaseState, STATE_GAME_OVER, STATE_MENU, STATE_PAUSE

# --- PHYSICS CONSTANTS ---
GRAVITY = 600.0
WALK_ACCEL = 300.0
MAX_SPEED = 80.0
SLIDE_SPEED = 240.0
SLIDE_FRICTION = 250.0
MAX_FALL_SPEED = 300.0
FRICTION = 600.0
JUMP_FORCE = -260.0
JUMP_CUT = 0.5
TILE_SIZE = 16

# --- ENEMY CONSTANTS ---
ENEMY_SPEED = 25.0
ENEMY_JUMP_FORCE = -220.0
ENEMY_VISION = 150.0

# --- LEVEL DATA (Visual Editor) ---
LEVEL_MAP = [
    "###############################################################################",
    "#                                                                             #",
    "#                                                                              ",
    "#                                                                              ",
    "#                                                                             #",
    "#                                                                            ##",
    "#                     #                                                      S#",
    "#                 ##                                                        ###",
    "#           ###SSS                             E       S                S     #",
    "#          #   ###                         ###### S  #####              ##    #",
    "#                        E                ##    ####     ##                   #",
    "#      ##               ####            ###                ###              ###",
    "#    #####        ####           SS           S      E S     ##     SS        #",
    "########################   ####################################################",
    "###############################################################################",
]

class Level:
    def __init__(self):
        self.width = len(LEVEL_MAP[0])
        self.height = len(LEVEL_MAP)
        self.pixel_width = self.width * TILE_SIZE

        self.palette = displayio.Palette(2)
        self.palette[0] = 0x6B8CFF
        self.palette[1] = 0x00AA00

        # single tile bitmap (two frames stacked vertically as before)
        self.bitmap = displayio.Bitmap(TILE_SIZE, TILE_SIZE * 2, 2)
        for y in range(TILE_SIZE, TILE_SIZE * 2):
            for x in range(TILE_SIZE):
                self.bitmap[x, y] = 1

        # TileGrid that maps to the entire level (same approach you had).
        self.tilegrid = displayio.TileGrid(
            self.bitmap,
            pixel_shader=self.palette,
            width=self.width,
            height=self.height,
            tile_width=TILE_SIZE,
            tile_height=TILE_SIZE,
        )

        self.enemy_spawns = []
        self.spike_spawns = []

        for y in range(self.height):
            row_string = LEVEL_MAP[y]
            for x in range(self.width):
                char = row_string[x]
                if char == "#":
                    self.tilegrid[x, y] = 1
                elif char == "E":
                    self.tilegrid[x, y] = 0
                    self.enemy_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                elif char == "S":
                    self.tilegrid[x, y] = 0
                    self.spike_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                else:
                    self.tilegrid[x, y] = 0

    def is_solid(self, x, y):
        tx = int(x // TILE_SIZE)
        ty = int(y // TILE_SIZE)
        if tx < 0 or tx >= self.width:
            return True
        if ty < 0:
            return False
        if ty >= self.height:
            return True
        return LEVEL_MAP[ty][tx] == "#"

class Spike:
    def __init__(self, x, y, bitmap, palette):
        self.x = x
        self.y = y
        self.hitbox_x = x + 3
        self.hitbox_y = y + 6
        self.hitbox_w = 10
        self.hitbox_h = 10
        self.sprite = displayio.TileGrid(bitmap, pixel_shader=palette, x=int(x - 8), y=int(y - 9))
        # cache integer position so we don't write the same position repeatedly
        self._prev_x = int(self.sprite.x)
        self._prev_y = int(self.sprite.y)

class Enemy:
    def __init__(self, x, y):
        self.width = 16
        self.height = 16
        self.start_x = x
        self.start_y = y
        self.x = float(x)
        self.y = float(y)
        self.vx = -30.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self.bitmap = displayio.Bitmap(16, 16, 1)
        self.palette = displayio.Palette(1)
        self.palette[0] = 0x880000
        self.sprite = displayio.TileGrid(self.bitmap, pixel_shader=self.palette, x=int(x), y=int(y))
        # prev integer positions to avoid redundant writes
        self._prev_sprite_x = int(self.sprite.x)
        self._prev_sprite_y = int(self.sprite.y)

    def reset(self):
        self.x = float(self.start_x)
        self.y = float(self.start_y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True
        self.sprite.hidden = False
        # only set sprite pos if different
        sx = int(self.x)
        sy = int(self.y)
        if self._prev_sprite_x != sx:
            self.sprite.x = sx
            self._prev_sprite_x = sx
        if self._prev_sprite_y != sy:
            self.sprite.y = sy
            self._prev_sprite_y = sy

    def update(self, dt, level, player):
        if not self.alive:
            return
        dist_to_player = player.x - self.x

        if abs(dist_to_player) < ENEMY_VISION:
            target_vel = ENEMY_SPEED if dist_to_player > 0 else -ENEMY_SPEED
            if self.vx < target_vel:
                self.vx += WALK_ACCEL * dt
            elif self.vx > target_vel:
                self.vx -= WALK_ACCEL * dt
        else:
            if self.vx > 0:
                self.vx = max(0, self.vx - FRICTION * dt)
            elif self.vx < 0:
                self.vx = min(0, self.vx + FRICTION * dt)

        if self.on_ground:
            look_dir = 1 if self.vx > 0 else -1
            check_x = self.x + (self.width if look_dir == 1 else 0) + (look_dir * 10)
            wall_blocked = level.is_solid(check_x, self.y + 8)
            gap_ahead = not level.is_solid(check_x, self.y + self.height + 2)
            if wall_blocked or gap_ahead:
                if abs(self.vx) > 10:
                    self.vy = ENEMY_JUMP_FORCE
                    self.on_ground = False

        self.vy += GRAVITY * dt
        self.x += self.vx * dt

        if self.vx > 0:
            if level.is_solid(self.x + self.width, self.y) or level.is_solid(self.x + self.width, self.y + self.height - 1):
                self.x = (int((self.x + self.width) // TILE_SIZE) * TILE_SIZE) - self.width - 0.01
                self.vx = 0
        elif self.vx < 0:
            if level.is_solid(self.x, self.y) or level.is_solid(self.x, self.y + self.height - 1):
                self.x = (int(self.x // TILE_SIZE) + 1) * TILE_SIZE + 0.01
                self.vx = 0

        self.y += self.vy * dt
        self.on_ground = False

        if self.vy > 0:
            if level.is_solid(self.x + 2, self.y + self.height) or level.is_solid(self.x + self.width - 2, self.y + self.height):
                self.y = (int((self.y + self.height) // TILE_SIZE) * TILE_SIZE) - self.height
                self.vy = 0
                self.on_ground = True
        elif self.vy < 0:
            if level.is_solid(self.x + 2, self.y) or level.is_solid(self.x + self.width - 2, self.y):
                self.y = (int(self.y // TILE_SIZE) + 1) * TILE_SIZE
                self.vy = 0

        if self.y > 300:
            self.alive = False
            self.sprite.hidden = True

        # only update sprite.x/y if the integer position changed
        sx = int(self.x)
        sy = int(self.y)
        if self._prev_sprite_x != sx:
            self.sprite.x = sx
            self._prev_sprite_x = sx
        if self._prev_sprite_y != sy:
            self.sprite.y = sy
            self._prev_sprite_y = sy

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
        self.is_sliding = False
        self.slide_cooldown = 0.0
        self.is_dead = False

        self.group = displayio.Group()
        self.sprites = {}
        self.sprite_offset_x = -10
        self.sprite_offset_y = -9 # Visual feet at 25px fix

        # cached prev values to avoid redundant writes
        self._prev_group_x = None
        self._prev_group_y = None
        self._prev_frame_index = None
        self._prev_flip_x = None

        def load_sprite(name, filename, tile_w=32, tile_h=32, frame_count=None):
            try:
                bmp = displayio.OnDiskBitmap(f"/sprites/{filename}")
                pal = bmp.pixel_shader
                if isinstance(pal, displayio.ColorConverter):
                    pal.make_transparent(0xFF00FF)
                else:
                    pal.make_transparent(0)
                    for i in range(len(pal)):
                        if pal[i] == 0xFF00FF:
                            pal.make_transparent(i)

                grid = displayio.TileGrid(bmp, pixel_shader=pal, tile_width=tile_w, tile_height=tile_h)
                grid.hidden = True
                self.group.append(grid)

                cols = bmp.width // tile_w
                rows = bmp.height // tile_h
                total_frames = cols * rows
                if frame_count is not None:
                    total_frames = frame_count

                self.sprites[name] = {"grid": grid, "frames": total_frames}

            except Exception as e:
                print(f"Failed to load {filename}: {e}")
                fallback = displayio.Bitmap(16, 16, 1)
                pal = displayio.Palette(1)
                pal[0] = 0xFF0000
                grid = displayio.TileGrid(fallback, pixel_shader=pal)
                grid.hidden = True
                self.group.append(grid)
                self.sprites[name] = {"grid": grid, "frames": 1}

        load_sprite("run", "run.bmp", 32, 32)
        load_sprite("jump", "jump.bmp", 32, 32, frame_count=3)
        load_sprite("slide", "slide.bmp", 32, 32, frame_count=3)
        load_sprite("death", "death.bmp", 32, 32)

        self.current_anim = "run"
        self.anim_timer = 0.0
        self.frame_index = 0
        self.set_animation("run")

    def set_animation(self, name):
        if self.current_anim == name:
            return
        if self.current_anim in self.sprites:
            self.sprites[self.current_anim]["grid"].hidden = True
        self.current_anim = name
        if name in self.sprites:
            self.sprites[name]["grid"].hidden = False
            self.frame_index = 0
            # reset cached values so the first frame forces an update
            self._prev_frame_index = None
            self._prev_flip_x = None

    def die(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.vx = 0
        self.vy = 0
        self.set_animation("death")
        self.frame_index = 0
        self.anim_timer = 0

    def reset_state(self, start_x, start_y):
        self.x = float(start_x)
        self.y = float(start_y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing_right = True
        self.is_sliding = False
        self.slide_cooldown = 0.0
        self.is_dead = False
        self.set_animation("run")
        self.frame_index = 0

    def update(self, handler, dt, level):

        if self.is_dead:
            self.set_animation("death")
            anim_data = self.sprites["death"]
            self.anim_timer += dt
            if self.anim_timer > 0.2:
                if self.frame_index < anim_data["frames"] - 1:
                    self.frame_index += 1
                self.anim_timer = 0

            active_grid = anim_data["grid"]
            gx = int(self.x + self.sprite_offset_x)
            gy = int(self.y + self.sprite_offset_y)
            # only change group position if different
            if self._prev_group_x != gx:
                self.group.x = gx
                self._prev_group_x = gx
            if self._prev_group_y != gy:
                self.group.y = gy
                self._prev_group_y = gy
            if self._prev_frame_index != self.frame_index:
                active_grid[0] = self.frame_index
                self._prev_frame_index = self.frame_index
            return

        ax, ay = handler.get_axis()
        if self.slide_cooldown > 0:
            self.slide_cooldown -= dt

        if handler.was_just_pressed("Y") and self.on_ground and not self.is_sliding and self.slide_cooldown <= 0:
            self.is_sliding = True
            self.slide_cooldown = 2.0
            direction = 1 if self.facing_right else -1
            self.vx = direction * SLIDE_SPEED
            self.frame_index = 0

        if self.is_sliding:
            if self.vx > 0:
                self.vx -= SLIDE_FRICTION * dt
                if self.vx < 0:
                    self.vx = 0
            elif self.vx < 0:
                self.vx += SLIDE_FRICTION * dt
                if self.vx > 0:
                    self.vx = 0
            if abs(self.vx) < 5 or not self.on_ground:
                self.is_sliding = False
        else:
            if abs(ax) > 0.1:
                self.vx += ax * WALK_ACCEL * dt
                self.facing_right = (ax > 0)
            else:
                if self.vx > 0:
                    self.vx = max(0, self.vx - FRICTION * dt)
                elif self.vx < 0:
                    self.vx = min(0, self.vx + FRICTION * dt)
            self.vx = max(min(self.vx, MAX_SPEED), -MAX_SPEED)

        dx = self.vx * dt
        if dx > 14:
            dx = 14
        elif dx < -14:
            dx = -14
        self.x += dx

        if self.vx > 0:
            if level.is_solid(self.x + self.width, self.y) or level.is_solid(self.x + self.width, self.y + self.height - 0.1):
                self.x = (int((self.x + self.width) // TILE_SIZE) * TILE_SIZE) - self.width - 0.01
                self.vx = 0
                self.is_sliding = False
        elif self.vx < 0:
            if level.is_solid(self.x, self.y) or level.is_solid(self.x, self.y + self.height - 0.1):
                self.x = (int(self.x // TILE_SIZE) + 1) * TILE_SIZE + 0.01
                self.vx = 0
                self.is_sliding = False

        if handler.was_just_pressed("A") and self.on_ground and not self.is_sliding:
            self.vy = JUMP_FORCE
            self.on_ground = False
        if handler.was_just_released("A") and self.vy < 0:
            self.vy *= JUMP_CUT

        self.vy += GRAVITY * dt
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        dy = self.vy * dt
        if dy > 14:
            dy = 14
        elif dy < -14:
            dy = -14
        self.y += dy

        self.on_ground = False
        if self.vy > 0:
            if level.is_solid(self.x + 2, self.y + self.height) or level.is_solid(self.x + self.width - 2, self.y + self.height):
                self.y = (int((self.y + self.height) // TILE_SIZE) * TILE_SIZE) - self.height
                self.vy = 0
                self.on_ground = True
        elif self.vy < 0:
            if level.is_solid(self.x + 2, self.y) or level.is_solid(self.x + self.width - 2, self.y):
                self.y = (int(self.y // TILE_SIZE) + 1) * TILE_SIZE
                self.vy = 0

        if self.y > 300 and not self.is_dead:
            self.die()

        new_anim = "run"
        if self.is_sliding:
            new_anim = "slide"
        elif not self.on_ground:
            new_anim = "jump"
        elif abs(self.vx) > 10:
            new_anim = "run"
        else:
            new_anim = "run"

        self.set_animation(new_anim)
        anim_data = self.sprites[self.current_anim]

        # Animation frame logic unchanged, but we only write to display when something changed.
        if self.current_anim == "run":
            if abs(self.vx) > 10:
                self.anim_timer += dt
                if self.anim_timer > 0.1:
                    self.frame_index = (self.frame_index + 1) % anim_data["frames"]
                    self.anim_timer = 0
            else:
                self.frame_index = 0
        elif self.current_anim == "jump":
            self.anim_timer += dt
            if self.anim_timer > 0.15:
                next_frame = self.frame_index + 1
                if next_frame < anim_data["frames"]:
                    self.frame_index = next_frame
                else:
                    self.frame_index = anim_data["frames"] - 1
                self.anim_timer = 0
        elif self.current_anim == "slide":
            self.anim_timer += dt
            if self.anim_timer > 0.08:
                next_frame = self.frame_index + 1
                if next_frame < anim_data["frames"]:
                    self.frame_index = next_frame
                else:
                    self.frame_index = anim_data["frames"] - 1
                self.anim_timer = 0

        active_grid = anim_data["grid"]
        gx = int(self.x + self.sprite_offset_x)
        gy = int(self.y + self.sprite_offset_y)
        # write group position only if it changed
        if self._prev_group_x != gx:
            self.group.x = gx
            self._prev_group_x = gx
        if self._prev_group_y != gy:
            self.group.y = gy
            self._prev_group_y = gy

        # flip_x only if changed
        flip_val = not self.facing_right
        if self._prev_flip_x != flip_val:
            active_grid.flip_x = flip_val
            self._prev_flip_x = flip_val

        # frame index only if changed
        if self._prev_frame_index != self.frame_index:
            active_grid[0] = self.frame_index
            self._prev_frame_index = self.frame_index

class PlatformerGame(BaseState):
    def __init__(self, manager):
        super().__init__(manager)

        self.bg = Rect(0, 0, 340, 260, fill=0x6B8CFF)
        self.root_group.append(self.bg)

        self.world = displayio.Group()
        self.root_group.append(self.world)

        self.level = Level()
        self.world.append(self.level.tilegrid)

        # --- LOAD SPIKE ASSET ---
        try:
            self.spike_bmp = displayio.OnDiskBitmap("/sprites/spike.bmp")
            self.spike_pal = self.spike_bmp.pixel_shader
            if isinstance(self.spike_pal, displayio.ColorConverter):
                self.spike_pal.make_transparent(0xFF00FF)
            else:
                self.spike_pal.make_transparent(0)
                for i in range(len(self.spike_pal)):
                    if self.spike_pal[i] == 0xFF00FF:
                        self.spike_pal.make_transparent(i)
        except:
            print("Err: spike.bmp missing")
            self.spike_bmp = displayio.Bitmap(32, 32, 1)
            self.spike_pal = displayio.Palette(1)
            self.spike_pal[0] = 0x555555

        # --- SPAWN SPIKES ---
        self.spikes = []
        for pos in self.level.spike_spawns:
            self.spikes.append(Spike(pos[0], pos[1], self.spike_bmp, self.spike_pal))

        for s in self.spikes:
            self.world.append(s.sprite)

        # --- ENEMIES ---
        self.enemies = []
        for pos in self.level.enemy_spawns:
            self.enemies.append(Enemy(pos[0], pos[1]))

        for e in self.enemies:
            self.world.append(e.sprite)

        self.player = Player(50, 50)
        self.world.append(self.player.group)

        self.hud = label.Label(self.manager.font_game, text="MARIO DEMO", x=10, y=10, color=0xFFFFFF, background_color=0x000000)
        self.root_group.append(self.hud)

        self.camera_x = 0
        # store previous world.x to avoid redundant display writes
        self._prev_world_x = None

        self.hud_timer = 0

        self.game_state = "PLAYING"
        self.death_timer = 0.0

        # Death Overlay
        self.overlay_group = displayio.Group()
        self.overlay_group.hidden = True

        dither_bmp = displayio.Bitmap(320, 240, 2)
        dither_pal = displayio.Palette(2)
        dither_pal[0] = 0x000000
        dither_pal.make_transparent(0)
        dither_pal[1] = 0x000000

        for y in range(0, 240, 2):
            for x in range(0, 320, 2):
                dither_bmp[x, y] = 1
                if x+1 < 320 and y+1 < 240:
                    dither_bmp[x+1, y+1] = 1

        self.overlay_bg = displayio.TileGrid(dither_bmp, pixel_shader=dither_pal)
        self.overlay_group.append(self.overlay_bg)

        self.overlay_text = label.Label(self.manager.font_ui, text="YOU DIED", scale=3, x=90, y=100, color=0xFF0000)
        self.overlay_sub = label.Label(self.manager.font_ui, text="Press A to Save", scale=2, x=70, y=150, color=0xFFFFFF)

        self.overlay_group.append(self.overlay_text)
        self.overlay_group.append(self.overlay_sub)

        self.root_group.append(self.overlay_group)

    def reset(self):
        self.player.reset_state(50, 50)
        self.camera_x = 0
        # only write when different
        desired_world_x = 0
        if self._prev_world_x != desired_world_x:
            self.world.x = desired_world_x
            self._prev_world_x = desired_world_x

        for e in self.enemies:
            e.reset()

        self.game_state = "PLAYING"
        self.overlay_group.hidden = True
        self.manager.log("Platformer: Reset")

    def enter(self):
        self.manager.log("Platformer: Resume")

    def update(self, handler, dt):
        if self.game_state == "PLAYING":
            self.player.update(handler, dt, self.level)

            if self.player.is_dead:
                self.game_state = "DYING"
                self.death_timer = 2.0
                return

            px, py = self.player.x, self.player.y
            pw, ph = self.player.width, self.player.height

            # Spikes
            for spike in self.spikes:
                if (px < spike.hitbox_x + spike.hitbox_w and
                    px + pw > spike.hitbox_x and
                    py < spike.hitbox_y + spike.hitbox_h and
                    py + ph > spike.hitbox_y):

                    self.player.die()
                    self.game_state = "DYING"
                    self.death_timer = 2.0
                    self.manager.log("Spiked!")
                    break

            if not self.player.is_dead:
                for enemy in self.enemies:
                    enemy.update(dt, self.level, self.player)

                    if enemy.alive:
                        ex, ey = enemy.x, enemy.y
                        ew, eh = enemy.width, enemy.height

                        if (px < ex + ew and px + pw > ex and py < ey + eh and py + ph > ey):
                            if self.player.is_sliding:
                                enemy.alive = False
                                enemy.sprite.hidden = True
                                self.manager.log("Enemy Defeated (Slide)")
                            elif self.player.vy > 0 and (py + ph) < (ey + eh/2):
                                enemy.alive = False
                                enemy.sprite.hidden = True
                                self.player.vy = -150
                                self.manager.log("Enemy Defeated (Stomp)")
                            else:
                                self.player.die()
                                self.game_state = "DYING"
                                self.death_timer = 2.0
                                self.manager.log("Player Killed")
                                break

            CAMERA_LEFT = 100
            CAMERA_RIGHT = 220
            screen_pos_x = self.player.x - self.camera_x
            if screen_pos_x > CAMERA_RIGHT:
                self.camera_x += (screen_pos_x - CAMERA_RIGHT)
            elif screen_pos_x < CAMERA_LEFT:
                self.camera_x += (screen_pos_x - CAMERA_LEFT)
            max_scroll = self.level.pixel_width - 320
            if self.camera_x < 0:
                self.camera_x = 0
            if self.camera_x > max_scroll:
                self.camera_x = max_scroll

            # Only update world.x if integer value changed (avoid forcing recompose every frame)
            new_world_x = -int(self.camera_x)
            if self._prev_world_x != new_world_x:
                self.world.x = new_world_x
                self._prev_world_x = new_world_x

            if handler.was_just_pressed("SEL"):
                self.manager.change_state(STATE_PAUSE)

            if self.player.y > 300:
                self.player.die()
                self.game_state = "DYING"
                self.death_timer = 2.0

            self.hud_timer += dt
            if self.hud_timer > 0.5:
                # update only when changed (optional)
                new_text = f"P: {int(self.player.x)}"
                if self.hud.text != new_text:
                    self.hud.text = new_text
                self.hud_timer = 0

        elif self.game_state == "DYING":
            self.player.update(handler, dt, self.level)
            self.death_timer -= dt
            if self.death_timer <= 0:
                # Trigger Save Prompt
                self.manager.trigger_save_prompt("Mario", int(self.player.x), "Distance")
