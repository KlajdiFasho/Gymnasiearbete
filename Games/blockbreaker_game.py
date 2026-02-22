import displayio
import terminalio
import math
import time
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from Handlers.gamestate import BaseState, STATE_MENU, STATE_PAUSE

# --- CONSTANTS ---
SCREEN_W = 320
SCREEN_H = 240
PADDLE_W = 48;
PADDLE_H = 8;
PADDLE_Y = 220;
PADDLE_SPEED = 260.0;
PADDLE_COLOR = 0x00FFFF
BALL_SIZE = 6;
BALL_SPEED_BASE = 140.0;
BALL_SPEED_MAX = 240.0
BRICK_W = 32; BRICK_H = 12; GRID_COLS = 10; GRID_ROWS = 10
LEVELS = [
    [[0]*10,[0]*10,[1]*10,[2]*10,[3]*10,[0]*10],
    [[7,0,0,0,0,0,0,0,0,7],[7,1,1,1,0,0,1,1,1,7],[7,2,2,2,0,0,2,2,2,7],[7,3,3,3,0,0,3,3,3,7],[7,4,4,4,0,0,4,4,4,7],[7,5,5,5,0,0,5,5,5,7]],
    [[7]*10,[7,6,6,6,6,6,6,6,6,7],[7,0,0,0,0,0,0,0,0,7],[7,0,4,4,4,4,4,4,0,7],[7,0,4,4,4,4,4,4,0,7],[7,0,0,0,0,0,0,0,0,7],[7,7,0,0,0,0,0,0,7,7]],
    [[1,0,1,0,1,1,0,1,0,1],[0,2,0,2,7,7,2,0,2,0],[3,0,3,0,7,7,0,3,0,3],[0,4,0,4,0,0,4,0,4,0],[5,0,5,0,7,7,0,5,0,5],[0,6,0,6,7,7,6,0,6,0],[7,7,0,0,0,0,0,0,7,7]]
]

class BrickGrid:
    def __init__(self):
        self.active_bricks = 0
        self.palette = displayio.Palette(8)
        self.palette[0] = 0x000000
        self.palette[1] = 0xFF0000
        self.palette[2] = 0xFF7F00
        self.palette[3] = 0xFFFF00
        self.palette[4] = 0x00FF00
        self.palette[5] = 0x0000FF
        self.palette[6] = 0xFF00FF
        self.palette[7] = 0x555555
        self.palette.make_transparent(0)
        self.sheet = displayio.Bitmap(BRICK_W, BRICK_H * 8, 8)
        for i in range(8):
            for y in range(BRICK_H):
                for x in range(BRICK_W):
                    self.sheet[x, y + (i * BRICK_H)] = i
        self.grid = displayio.TileGrid(self.sheet, pixel_shader=self.palette, width=GRID_COLS, height=GRID_ROWS, tile_width=BRICK_W, tile_height=BRICK_H)
    def load_level(self, level_idx):
        for i in range(GRID_COLS * GRID_ROWS): self.grid[i % GRID_COLS, i // GRID_COLS] = 0
        data = LEVELS[level_idx % len(LEVELS)]
        self.active_bricks = 0
        for r, row in enumerate(data):
            for c, color_idx in enumerate(row):
                if color_idx > 0:
                    self.grid[c, r] = color_idx
                    if color_idx < 7: self.active_bricks += 1
    def check_collision(self, ball_rect):
        col1 = int(ball_rect.x // BRICK_W); col2 = int((ball_rect.x + ball_rect.width) // BRICK_W)
        row1 = int(ball_rect.y // BRICK_H); row2 = int((ball_rect.y + ball_rect.height) // BRICK_H)
        score = 0
        for c in range(col1, col2 + 1):
            for r in range(row1, row2 + 1):
                if 0 <= c < GRID_COLS and 0 <= r < GRID_ROWS:
                    tile = self.grid[c, r]
                    if tile > 0:
                        if tile < 7: self.grid[c, r] = 0; self.active_bricks -= 1; score += tile * 10
                        return True, score
        return False, 0

class Paddle:
    def __init__(self):
        self.width = PADDLE_W; self.height = PADDLE_H
        self.x = (SCREEN_W - PADDLE_W) // 2; self.y = PADDLE_Y
        self.rect = Rect(int(self.x), int(self.y), self.width, self.height, fill=PADDLE_COLOR)
    def update(self, handler, dt):
        ax, _ = handler.get_axis()
        if abs(ax) > 0.1: self.x += ax * PADDLE_SPEED * dt
        if self.x < 0: self.x = 0
        if self.x > SCREEN_W - self.width: self.x = SCREEN_W - self.width
        self.rect.x = int(self.x)

class Ball:
    def __init__(self):
        self.size = BALL_SIZE; self.x = 0.0; self.y = 0.0; self.vx = 0.0; self.vy = 0.0; self.active = False
        self.rect = Rect(0, 0, self.size, self.size, fill=0xFFFFFF)
    def reset(self, paddle):
        self.active = False
        self.x = paddle.x + (paddle.width // 2) - (self.size // 2)
        self.y = paddle.y - self.size - 2
        self.vx = 0; self.vy = 0; self.update_rect()
    def launch(self):
        self.active = True; self.vx = 0.0; self.vy = -BALL_SPEED_BASE
    def update(self, dt, paddle, brick_grid):
        if not self.active:
            self.x = paddle.x + (paddle.width // 2) - (self.size // 2)
            self.y = paddle.y - self.size - 2
            self.update_rect(); return "NONE", 0
        total_score = 0
        move_x = self.vx * dt; move_y = self.vy * dt
        distance = math.sqrt(move_x**2 + move_y**2)
        MAX_STEP = 2.0; steps = int(math.ceil(distance / MAX_STEP))
        if steps == 0: steps = 1
        step_x = move_x / steps; step_y = move_y / steps
        status = "NONE"
        for _ in range(steps):
            prev_x = self.x; self.x += step_x; self.update_rect()
            if self.x <= 0: self.x = 0; self.vx = abs(self.vx)
            elif self.x >= SCREEN_W - self.size: self.x = SCREEN_W - self.size; self.vx = -abs(self.vx)
            hit, score = brick_grid.check_collision(self.rect)
            if hit: self.vx *= -1; self.x = prev_x; self.update_rect(); total_score += score
            prev_y = self.y; self.y += step_y; self.update_rect()
            if self.y <= 0: self.y = 0; self.vy = abs(self.vy)
            hit, score = brick_grid.check_collision(self.rect)
            if hit: self.vy *= -1; self.y = prev_y; self.update_rect(); total_score += score
            if (self.vy > 0 and self.y + self.size >= paddle.y and self.y < paddle.y + paddle.height and self.x + self.size >= paddle.x and self.x < paddle.x + paddle.width):
                self.vy = -abs(self.vy); self.y = paddle.y - self.size - 0.1
                center_ball = self.x + self.size/2; center_paddle = paddle.x + paddle.width/2
                offset = (center_ball - center_paddle) / (paddle.width/2)
                self.vx += offset * 100
                if abs(self.vy) < BALL_SPEED_MAX: self.vy *= 1.05
            if self.y > SCREEN_H: status = "LOST"; break
        self.update_rect(); return status, total_score
    def update_rect(self): self.rect.x = int(self.x); self.rect.y = int(self.y)

class BlockBreakerGame(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 340, 260, fill=0x000022)
        self.root_group.append(self.bg)
        self.brick_grid = BrickGrid()
        self.root_group.append(self.brick_grid.grid)
        self.paddle = Paddle()
        self.root_group.append(self.paddle.rect)
        self.ball = Ball()
        self.root_group.append(self.ball.rect)
        self.score_label = label.Label(self.manager.font_ui, text="SCORE: 0", x=5, y=230, color=0xFFFFFF)
        self.lives_label = label.Label(self.manager.font_ui, text="LIVES: 3", x=240, y=230, color=0xFFFFFF)
        self.msg_label = label.Label(self.manager.font_ui, text="READY?", scale=2, x=110, y=140, color=0x00FFFF)
        self.root_group.append(self.score_label); self.root_group.append(self.lives_label); self.root_group.append(self.msg_label)
        self.level_idx = 0; self.score = 0; self.lives = 3; self.state = "START"

    def reset(self):
        self.score = 0; self.lives = 3; self.level_idx = 0
        self.lives_label.text = "LIVES: 3"; self.score_label.text = "SCORE: 0"
        self.load_level(0); self.manager.log("BlockBreaker: Reset")

    def load_level(self, idx):
        self.brick_grid.load_level(idx)
        self.paddle.x = (SCREEN_W - PADDLE_W)//2; self.ball.reset(self.paddle)
        self.msg_label.text = f"LEVEL {idx+1}"; self.msg_label.hidden = False
        self.state = "START"
        self.lives = 3; self.lives_label.text = "LIVES: 3"

    def update(self, handler, dt):
        if self.state == "START":
            self.paddle.update(handler, dt)
            self.ball.update(dt, self.paddle, self.brick_grid)
            if handler.was_just_pressed("A"): self.ball.launch(); self.msg_label.hidden = True; self.state = "PLAY"
        elif self.state == "PLAY":
            self.paddle.update(handler, dt)
            status, points = self.ball.update(dt, self.paddle, self.brick_grid)
            if points > 0:
                self.score += points; self.score_label.text = f"SCORE: {self.score}"
                if self.brick_grid.active_bricks == 0:
                    self.state = "LEVEL_DONE"; self.msg_label.text = "CLEARED!"; self.msg_label.hidden = False; self.ball.active = False
            if status == "LOST":
                self.lives -= 1; self.lives_label.text = f"LIVES: {self.lives}"
                self.manager.log(f"Ball Lost. Lives: {self.lives}")
                if self.lives <= 0:
                    self.state = "GAME_OVER"
                    # Trigger Save Prompt immediately on Game Over
                    self.manager.trigger_save_prompt("Block Breaker", self.score, "Points")
                else:
                    self.state = "START"; self.ball.reset(self.paddle); self.msg_label.text = "READY?"; self.msg_label.hidden = False
        elif self.state == "LEVEL_DONE":
            if handler.was_just_pressed("A"):
                self.level_idx += 1
                if self.level_idx >= len(LEVELS): self.level_idx = 0
                self.load_level(self.level_idx)

        # Note: GAME_OVER state logic is largely superseded by the trigger_save_prompt,
        # but we keep this to handle returns from other states if needed.
        if handler.was_just_pressed("SEL"): self.manager.change_state(STATE_PAUSE)
        if handler.was_just_pressed("B") and self.state != "GAME_OVER": self.manager.change_state(STATE_MENU)
