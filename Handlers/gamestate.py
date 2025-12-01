import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

# --- CONSTANTS ---
STATE_MENU = "MENU"
STATE_PLATFORMER = "PLATFORMER"
STATE_GAME_OVER = "GAME_OVER"
STATE_SETTINGS = "SETTINGS"
STATE_CONSOLE = "CONSOLE"

# -----------------------------------------------------------
# BASE STATE
# -----------------------------------------------------------
class BaseState:
    def __init__(self, manager):
        self.manager = manager
        self.root_group = displayio.Group()

    def enter(self):
        pass

    def exit(self):
        pass

    def update(self, handler, dt):
        pass

    def get_group(self):
        return self.root_group

# -----------------------------------------------------------
# STATE 1: MAIN MENU
# -----------------------------------------------------------
class MenuState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x000044)
        self.title = label.Label(terminalio.FONT, text="MAIN MENU", scale=3, x=60, y=60, color=0xFFFFFF)
        self.instr = label.Label(terminalio.FONT, text="Press A to Start\nPress SEL for Settings", scale=2, x=40, y=140, color=0xAAAAAA)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.instr)

    def update(self, handler, dt):
        if handler.was_just_pressed("A"):
            self.manager.change_state(STATE_PLATFORMER)
        elif handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_SETTINGS)

# -----------------------------------------------------------
# STATE 2: GAME PLATFORMER
# -----------------------------------------------------------
class PlatformerState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x000000)
        self.player = Rect(150, 110, 20, 20, fill=0x00FF00)
        self.hud = label.Label(terminalio.FONT, text="PLAYING... (Press B to die.)", x=10, y=10, color=0xFFFFFF)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.player)
        self.root_group.append(self.hud)
        
        self.px = 150.0
        self.py = 110.0
        self.speed = 100.0

    def enter(self):
        self.px, self.py = 150.0, 110.0
        self.manager.log("Game Started")

    def update(self, handler, dt):
        ax, ay = handler.get_axis()
        self.px += ax * self.speed * dt
        self.py += ay * (-self.speed) * dt

        if self.px > 320: self.px = 0
        if self.px < 0: self.px = 320
        if self.py > 240: self.py = 0
        if self.py < 0: self.py = 240

        self.player.x = int(self.px)
        self.player.y = int(self.py)

        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_GAME_OVER)
        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_MENU)

# -----------------------------------------------------------
# STATE 3: GAME OVER
# -----------------------------------------------------------
class GameOverState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x440000)
        self.msg = label.Label(terminalio.FONT, text="GAME OVER", scale=3, x=60, y=100, color=0xFF0000)
        self.sub = label.Label(terminalio.FONT, text="Press A to Restart", scale=2, x=50, y=150, color=0xFFFFFF)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.msg)
        self.root_group.append(self.sub)

    def enter(self):
        self.manager.log("Player Died")

    def update(self, handler, dt):
        if handler.was_just_pressed("A"):
            self.manager.change_state(STATE_MENU)

# -----------------------------------------------------------
# STATE 4: SETTINGS
# -----------------------------------------------------------
class SettingsState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x444444)
        
        self.text = label.Label(terminalio.FONT, text="SETTINGS\n\nSensitivity: ...", scale=2, x=20, y=40, color=0xFFFFFF)
        self.help = label.Label(terminalio.FONT, text="Press X to Toggle Sense", x=20,y=130, color=0xDDDDDD)
        
        self.console_hint = label.Label(terminalio.FONT, text="Press SEL for Console", x=20, y=180, color=0x00FF00)
        self.back_hint = label.Label(terminalio.FONT, text="Press B to Back (Menu)", x=20, y=210, color=0xCCCCCC)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.text)
        self.root_group.append(self.help)
        self.root_group.append(self.console_hint)
        self.root_group.append(self.back_hint)

    def update_label(self, sensitivity):
        if sensitivity > 1.5:
            self.text.text = "SETTINGS\n\nSensitivity: HIGH"
        else:
            self.text.text = "SETTINGS\n\nSensitivity: NORMAL"

    def update(self, handler, dt):
        self.update_label(handler.sensitivity)

        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_MENU)
        
        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_CONSOLE)
        
        if handler.was_just_pressed("X"):
            handler.sensitivity = 2.0 if handler.sensitivity == 1.5 else 1.5
            self.manager.log(f"Sense set to: {handler.sensitivity}")

# -----------------------------------------------------------
# STATE 5: CONSOLE (Updated with Scrolling)
# -----------------------------------------------------------
class ConsoleState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x111111) 
        self.title = label.Label(terminalio.FONT, text="SYSTEM LOGS", scale=2, x=10, y=10, color=0x00FF00)
        
        # Displays the actual log lines
        self.logs_label = label.Label(terminalio.FONT, text="", x=10, y=40, color=0x00FF00, line_spacing=1.2)
        
        self.back = label.Label(terminalio.FONT, text="[B] Back | [JOY] Scroll", x=10, y=220, color=0xFFFFFF)

        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.logs_label)
        self.root_group.append(self.back)
        
        # Scrolling State
        self.max_lines_visible = 12
        self.top_line_index = 0
        self.scroll_cooldown = 0.0

    def enter(self):
        # Auto-scroll to the bottom (show newest)
        total_logs = len(self.manager.logs)
        # Calculate the index so the last line is at the bottom
        self.top_line_index = max(0, total_logs - self.max_lines_visible)
        self.update_view()

    def update_view(self):
        # Slice the logs based on current scroll position
        start = self.top_line_index
        end = start + self.max_lines_visible
        visible_logs = self.manager.logs[start:end]
        
        self.logs_label.text = "\n".join(visible_logs)
        
        # Update title with position indicator
        total = len(self.manager.logs)
        current = min(end, total)
        self.title.text = f"LOGS ({current}/{total})"

    def update(self, handler, dt):
        # 1. Back Navigation
        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_SETTINGS)

        # 2. Scrolling Logic
        # We use a cooldown so it doesn't scroll 60 lines per second
        self.scroll_cooldown -= dt
        
        if self.scroll_cooldown <= 0:
            dirs = handler.get_direction()
            
            did_scroll = False
            
            # Scroll UP (Backward in history)
            if dirs['UP']:
                if self.top_line_index > 0:
                    self.top_line_index -= 1
                    did_scroll = True
            
            # Scroll DOWN (Forward in history)
            elif dirs['DOWN']:
                total_logs = len(self.manager.logs)
                max_start = max(0, total_logs - self.max_lines_visible)
                if self.top_line_index < max_start:
                    self.top_line_index += 1
                    did_scroll = True
            
            if did_scroll:
                self.update_view()
                self.scroll_cooldown = 0.1 # 100ms delay between scrolls

# -----------------------------------------------------------
# STATE MANAGER
# -----------------------------------------------------------
class GameStateManager:
    def __init__(self, main_display_group):
        self.main_group = main_display_group
        self.states = {}
        self.current_state_obj = None
        
        # Increased log capacity for scrolling demo
        self.logs = ["System Boot...", "Manager Init..."]

        self.states[STATE_MENU] = MenuState(self)
        self.states[STATE_PLATFORMER] = PlatformerState(self)
        self.states[STATE_GAME_OVER] = GameOverState(self)
        self.states[STATE_SETTINGS] = SettingsState(self)
        self.states[STATE_CONSOLE] = ConsoleState(self)

    def log(self, message):
        """Adds a message to the internal log list"""
        self.logs.append(f"> {message}")
        # Keep list size reasonable (max 50 lines now)
        if len(self.logs) > 50:
            self.logs.pop(0)
        print(f"LOG: {message}")

    def change_state(self, state_id):
        if state_id not in self.states: return

        if self.current_state_obj:
            self.current_state_obj.exit()

        self.current_state_obj = self.states[state_id]
        self.current_state_obj.enter()

        self.log(f"State -> {state_id}")

        while len(self.main_group) > 0:
            self.main_group.pop()
        self.main_group.append(self.current_state_obj.get_group())

    def update(self, handler, dt):
        if self.current_state_obj:
            self.current_state_obj.update(handler, dt)
