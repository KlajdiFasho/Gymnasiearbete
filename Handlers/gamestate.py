import displayio
import terminalio
import time
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

# --- CONSTANTS ---
STATE_MENU = "MENU"
STATE_PLATFORMER = "PLATFORMER"
STATE_GAME_OVER = "GAME_OVER"
STATE_SETTINGS = "SETTINGS"
STATE_PAUSE = "PAUSE"
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
        self.bg = Rect(0, 0, 320, 240, fill=0x150020)
        self.root_group.append(self.bg)
        
        self.title = label.Label(self.manager.font_ui, text="ARCADE SELECT", scale=3, x=30, y=30, color=0xFFD700)
        self.root_group.append(self.title)
        
        self.options = ["Mario Demo", "Racing (WIP)", "Space (WIP)"]
        self.selected_index = 0
        self.scroll_cooldown = 0.0
        
        self.option_labels = []
        start_y = 90
        spacing = 40
        
        for i, opt_name in enumerate(self.options):
            if "Mario" in opt_name:
                font = self.manager.font_game
                base_color = 0xFF0000 
                scale = 1 
                y_offset = 5
            else:
                font = self.manager.font_ui
                base_color = 0x8888AA 
                scale = 2
                y_offset = 0
                
            lbl = label.Label(font, text=opt_name, scale=scale, x=50, y=start_y + (i * spacing) + y_offset, color=base_color)
            self.option_labels.append(lbl)
            self.root_group.append(lbl)
            
        self.instr = label.Label(self.manager.font_ui, text="[A] START    [SEL] SETTINGS", x=40, y=220, color=0x444466)
        self.root_group.append(self.instr)

    def enter(self):
        self.update_ui()

    def update_ui(self):
        for i, lbl in enumerate(self.option_labels):
            opt_name = self.options[i]
            if i == self.selected_index:
                lbl.text = f"> {opt_name}"
                lbl.color = 0xFFFFFF 
            else:
                lbl.text = f"  {opt_name}"
                if "Mario" in opt_name:
                    lbl.color = 0xFF0000 
                else:
                    lbl.color = 0x8888AA 

    def update(self, handler, dt):
        self.scroll_cooldown -= dt
        if self.scroll_cooldown <= 0:
            dirs = handler.get_direction()
            change = 0
            if dirs['UP']: change = -1
            if dirs['DOWN']: change = 1
            if change != 0:
                self.selected_index = (self.selected_index + change) % len(self.options)
                self.update_ui()
                self.scroll_cooldown = 0.15

        if handler.was_just_pressed("A"):
            if self.selected_index == 0:
                self.manager.states[STATE_PLATFORMER].reset()
                self.manager.change_state(STATE_PLATFORMER)
            else:
                self.manager.log("Game Not Implemented")
                
        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_SETTINGS)

# -----------------------------------------------------------
# STATE 3: GAME OVER
# -----------------------------------------------------------
class GameOverState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x440000)
        self.msg = label.Label(self.manager.font_ui, text="GAME OVER", scale=3, x=60, y=100, color=0xFF0000)
        self.sub = label.Label(self.manager.font_ui, text="Press A to Restart", scale=2, x=50, y=150, color=0xFFFFFF)
        
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
        self.bg = Rect(0, 0, 320, 240, fill=0x333333)
        self.title = label.Label(self.manager.font_ui, text="GLOBAL SETTINGS", scale=2, x=15, y=20, color=0x00FFFF)
        self.info = label.Label(self.manager.font_ui, text="", scale=2, x=15, y=60, color=0xFFFFFF)
        self.help = label.Label(self.manager.font_ui, text="[SEL] Console   [X] Toggle Sense", x=15, y=180, color=0xCCCCCC)
        self.back = label.Label(self.manager.font_ui, text="[B] BACK TO MENU", x=15, y=210, color=0xFFFFFF)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.info)
        self.root_group.append(self.help)
        self.root_group.append(self.back)

    def update_label(self, sensitivity):
        mode = "HIGH" if sensitivity > 1.5 else "NORMAL"
        self.info.text = f"Sensitivity: {mode}"

    def update(self, handler, dt):
        self.update_label(handler.sensitivity)
        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_CONSOLE)
        if handler.was_just_pressed("X"):
            handler.sensitivity = 2.0 if handler.sensitivity == 1.5 else 1.5
            self.manager.log(f"Sense set to: {handler.sensitivity}")
        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_MENU)

# -----------------------------------------------------------
# STATE 6: PAUSE MENU
# -----------------------------------------------------------
class PauseState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x222222) 
        self.title = label.Label(self.manager.font_ui, text="GAME PAUSED", scale=3, x=15, y=40, color=0xFFFF00)
        self.info = label.Label(self.manager.font_ui, text="", scale=2, x=15, y=100, color=0xFFFFFF)
        self.toggle_hint = label.Label(self.manager.font_ui, text="[X] Toggle Sensitivity", x=15, y=130, color=0xAAAAAA)
        self.resume_hint = label.Label(self.manager.font_ui, text="[B] RESUME GAME", scale=1, x=15, y=180, color=0x00FF00)
        self.quit_hint = label.Label(self.manager.font_ui, text="[A] QUIT TO TITLE", scale=1, x=15, y=200, color=0xFF0000)
        
        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.info)
        self.root_group.append(self.toggle_hint)
        self.root_group.append(self.resume_hint)
        self.root_group.append(self.quit_hint)

    def update_label(self, sensitivity):
        mode = "HIGH" if sensitivity > 1.5 else "NORMAL"
        self.info.text = f"Sensitivity: {mode}"

    def update(self, handler, dt):
        self.update_label(handler.sensitivity)
        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_PLATFORMER)
        if handler.was_just_pressed("A"):
            self.manager.log("Quitting to Title...")
            self.manager.change_state(STATE_MENU)
        if handler.was_just_pressed("X"):
            handler.sensitivity = 2.0 if handler.sensitivity == 1.5 else 1.5
            self.manager.log(f"In-Game Sense: {handler.sensitivity}")

# -----------------------------------------------------------
# STATE 5: CONSOLE
# -----------------------------------------------------------
class ConsoleState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x111111) 
        self.title = label.Label(self.manager.font_ui, text="SYSTEM LOGS", scale=2, x=5, y=10, color=0x00FF00)
        self.logs_label = label.Label(self.manager.font_ui, text="", x=5, y=40, color=0x00FF00, line_spacing=1.2)
        self.back = label.Label(self.manager.font_ui, text="[B] Back | [X] Clear All | [JOY] Scroll", x=5, y=220, color=0xFFFFFF)

        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.logs_label)
        self.root_group.append(self.back)
        
        self.max_lines_visible = 19
        self.top_line_index = 0
        self.scroll_cooldown = 0.0

    def enter(self):
        total_logs = len(self.manager.logs)
        self.top_line_index = max(0, total_logs - self.max_lines_visible)
        self.update_view()

    def update_view(self):
        start = self.top_line_index
        end = start + self.max_lines_visible
        visible_entries = self.manager.logs[start:end]
        
        display_lines = []
        for entry in visible_entries:
            msg = entry['msg']
            raw_time = int(entry['time'])
            mins = raw_time // 60
            secs = raw_time % 60
            time_str = f"[{mins:02}:{secs:02}]"
            
            max_msg_len = 40
            if len(msg) > max_msg_len:
                msg = msg[:max_msg_len-1] + "…"
            
            target_width = 48
            space_needed = max(1, target_width - len(msg) - len(time_str))
            line = f"{msg}{' ' * space_needed}{time_str}"
            display_lines.append(line)
        
        self.logs_label.text = "\n".join(display_lines)
        total = len(self.manager.logs)
        current = min(end, total)
        self.title.text = f"LOGS ({current}/{total})"

    def update(self, handler, dt):
        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_SETTINGS)
        if handler.was_just_pressed("X"):
            self.manager.clear_logs()
            self.top_line_index = 0
            self.update_view()

        self.scroll_cooldown -= dt
        if self.scroll_cooldown <= 0:
            dirs = handler.get_direction()
            did_scroll = False
            
            if dirs['UP']:
                if self.top_line_index > 0:
                    self.top_line_index -= 1
                    did_scroll = True
            elif dirs['DOWN']:
                total_logs = len(self.manager.logs)
                max_start = max(0, total_logs - self.max_lines_visible)
                if self.top_line_index < max_start:
                    self.top_line_index += 1
                    did_scroll = True
            
            if did_scroll:
                self.update_view()
                self.scroll_cooldown = 0.1

# -----------------------------------------------------------
# STATE MANAGER
# -----------------------------------------------------------
class GameStateManager:
    def __init__(self, main_display_group):
        self.main_group = main_display_group
        self.states = {}
        self.current_state_obj = None
        self.current_state_id = None
        self.previous_state = None
        
        self.logs = []
        self.log_timeout = 300.0 

        self.font_ui = terminalio.FONT
        self.font_game = terminalio.FONT
        
        print("Loading Fonts...")
        try:
            from adafruit_bitmap_font import bitmap_font
            try:
                self.font_ui = bitmap_font.load_font("/Fonts/gameboy.bdf")
            except Exception as e:
                print(f"Error loading gameboy.bdf: {e}")
                self.log("Err: gameboy.bdf missing")

            try:
                self.font_game = bitmap_font.load_font("/Fonts/mario.bdf")
            except Exception as e:
                print(f"Error loading mario.bdf: {e}")
                self.log("Err: mario.bdf missing")
        except ImportError:
            print("adafruit_bitmap_font library not found!")
            self.log("Err: Lib bitmap_font missing")

        from Games.platformer_game import PlatformerGame

        self.states[STATE_MENU] = MenuState(self)
        self.states[STATE_PLATFORMER] = PlatformerGame(self)
        self.states[STATE_GAME_OVER] = GameOverState(self)
        self.states[STATE_SETTINGS] = SettingsState(self)
        self.states[STATE_PAUSE] = PauseState(self)
        self.states[STATE_CONSOLE] = ConsoleState(self)
        
        self.log("System Boot...")

    def log(self, message):
        entry = {'msg': f"> {message}", 'time': time.monotonic()}
        self.logs.append(entry)
        if len(self.logs) > 50: self.logs.pop(0)
        print(f"LOG: {message}")

    def clear_logs(self):
        self.logs = []
        self.log("Logs cleared manually.")

    def change_state(self, state_id):
        if state_id not in self.states: return

        if self.current_state_id != STATE_CONSOLE:
            self.previous_state = self.current_state_id

        if self.current_state_obj:
            self.current_state_obj.exit()

        self.current_state_id = state_id
        self.current_state_obj = self.states[state_id]
        self.current_state_obj.enter()

        self.log(f"State -> {state_id}")

        while len(self.main_group) > 0:
            self.main_group.pop()
        self.main_group.append(self.current_state_obj.get_group())

    def update(self, handler, dt):
        # OPTIMIZATION: Do not clean logs every frame. Prevents GC lag.
        if self.current_state_obj:
            self.current_state_obj.update(handler, dt)
