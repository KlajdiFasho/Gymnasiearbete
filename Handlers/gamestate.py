import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

# --- CONSTANTS ---
STATE_MENU = "MENU"
STATE_PLATFORMER = "PLATFORMER"
STATE_GAME_OVER = "GAME_OVER"
STATE_SETTINGS = "SETTINGS"

# -----------------------------------------------------------
# BASE STATE (The template for all other states)
# -----------------------------------------------------------
class BaseState:
    def __init__(self, manager):
        self.manager = manager
        self.root_group = displayio.Group()

    def enter(self):
        """Called once when this state becomes active."""
        pass

    def exit(self):
        """Called once when leaving this state."""
        pass

    def update(self, handler, dt):
        """Handle input and game logic here."""
        pass

    def get_group(self):
        """Returns the display group to show."""
        return self.root_group


# -----------------------------------------------------------
# STATE 1: MAIN MENU
# -----------------------------------------------------------
class MenuState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        # UI Setup
        self.bg = Rect(0, 0, 320, 240, fill=0x000044) # Dark Blue
        self.title = label.Label(terminalio.FONT, text="MAIN MENU", scale=3, x=60, y=60, color=0xFFFFFF)
        self.instr = label.Label(terminalio.FONT, text="Press A to Start\nPress SEL for Settings", scale=2, x=40, y=140, color=0xAAAAAA)

        self.root_group.append(self.bg)
        self.root_group.append(self.title)
        self.root_group.append(self.instr)

    def update(self, handler, dt):
        # Navigation Logic
        if handler.was_just_pressed("A"):
            self.manager.change_state(STATE_PLATFORMER)
        elif handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_SETTINGS)


# -----------------------------------------------------------
# STATE 2: GAME PLATFORMER (The actual game)
# -----------------------------------------------------------
class PlatformerState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        # UI Setup
        self.bg = Rect(0, 0, 320, 240, fill=0x000000) # Black
        self.player = Rect(150, 110, 20, 20, fill=0x00FF00) # Green Player
        self.hud = label.Label(terminalio.FONT, text="PLAYING... (Press B to Die)", x=10, y=10, color=0xFFFFFF)

        self.root_group.append(self.bg)
        self.root_group.append(self.player)
        self.root_group.append(self.hud)

        # Game Variables
        self.px = 150.0
        self.py = 110.0
        self.speed = 100.0 # Pixels per second

    def enter(self):
        # Reset position on entry so game restarts fresh every time
        self.px, self.py = 150.0, 110.0
        self.player.x = int(self.px)
        self.player.y = int(self.py)

    def update(self, handler, dt):
        # 1. Player Movement (Using Joystick)
        ax, ay = handler.get_axis()

        # Move logic (Position = Position + (Direction * Speed * Time))
        self.px += ax * self.speed * dt
        self.py += ay * (-self.speed) * dt # -speed because Y=0 is the top of the screen

        # Screen wrapping (Teleport to other side if out of bounds)
        if self.px > 320: self.px = 0
        if self.px < 0: self.px = 320
        if self.py > 240: self.py = 0
        if self.py < 0: self.py = 240

        # Update graphic (must be int for displayio)
        self.player.x = int(self.px)
        self.player.y = int(self.py)

        # 2. State Logic
        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_GAME_OVER)

        # Pause functionality example
        if handler.was_just_pressed("SEL"):
            self.manager.change_state(STATE_MENU)


# -----------------------------------------------------------
# STATE 3: GAME OVER
# -----------------------------------------------------------
class GameOverState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x440000) # Dark Red
        self.msg = label.Label(terminalio.FONT, text="GAME OVER", scale=3, x=60, y=100, color=0xFF0000)
        self.sub = label.Label(terminalio.FONT, text="Press A to Restart", scale=2, x=50, y=150, color=0xFFFFFF)

        self.root_group.append(self.bg)
        self.root_group.append(self.msg)
        self.root_group.append(self.sub)

    def update(self, handler, dt):
        if handler.was_just_pressed("A"):
            self.manager.change_state(STATE_MENU)


# -----------------------------------------------------------
# STATE 4: SETTINGS
# -----------------------------------------------------------
class SettingsState(BaseState):
    def __init__(self, manager):
        super().__init__(manager)
        self.bg = Rect(0, 0, 320, 240, fill=0x444444) # Grey
        self.text = label.Label(terminalio.FONT, text="SETTINGS\n\nSensitivity: ...", scale=2, x=20, y=40, color=0xFFFFFF)
        self.help = label.Label(terminalio.FONT, text="Press X to Toggle", x=20,y=150, color=0xFFFFFF)
        self.back = label.Label(terminalio.FONT, text="Press B to Back", x=20, y=200, color=0xFFFFFF)

        self.root_group.append(self.bg)
        self.root_group.append(self.text)
        self.root_group.append(self.help)
        self.root_group.append(self.back)

    def update_label(self, sensitivity):
        """Helper to format the text based on current value"""
        if sensitivity > 1.5:
            self.text.text = "SETTINGS\n\nSensitivity: HIGH"
        else:
            self.text.text = "SETTINGS\n\nSensitivity: NORMAL"

    def enter(self):
        # When entering settings, make sure label matches current reality
        # We need a way to access the current sensitivity.
        # Since we don't have the handler in 'enter', we will update it in the first 'update' loop
        # or we just let the text be default until updated.
        pass

    def update(self, handler, dt):
        # Ensure label is correct on first frame of this state
        self.update_label(handler.sensitivity)

        if handler.was_just_pressed("B"):
            self.manager.change_state(STATE_MENU)

        # Toggle Logic
        if handler.was_just_pressed("X"):
            if handler.sensitivity == 1.5:
                handler.sensitivity = 2.0
            else:
                handler.sensitivity = 1.5
            # Visual update happens at start of next update() call


# -----------------------------------------------------------
# THE STATE MANAGER (The Brain)
# -----------------------------------------------------------
class GameStateManager:
    def __init__(self, main_display_group):
        self.main_group = main_display_group
        self.states = {}
        self.current_state_id = None
        self.current_state_obj = None

        # Register states
        self.states[STATE_MENU] = MenuState(self)
        self.states[STATE_PLATFORMER] = PlatformerState(self)
        self.states[STATE_GAME_OVER] = GameOverState(self)
        self.states[STATE_SETTINGS] = SettingsState(self)

    def change_state(self, state_id):
        """Switches the active state, handling exit/enter logic and display swapping."""
        if state_id not in self.states:
            print(f"Error: State {state_id} not found")
            return

        # 1. Exit previous state
        if self.current_state_obj:
            self.current_state_obj.exit()

        # 2. Swap internal tracker
        self.current_state_id = state_id
        self.current_state_obj = self.states[state_id]

        # 3. Enter new state
        self.current_state_obj.enter()

        # 4. Update Display (Remove old graphics, add new ones)
        # We assume main_group is the display.root_group
        while len(self.main_group) > 0:
            self.main_group.pop()

        self.main_group.append(self.current_state_obj.get_group())
        print(f"State changed to: {state_id}")

    def update(self, handler, dt):
        """Passes the update loop to the active state."""
        if self.current_state_obj:
            self.current_state_obj.update(handler, dt)
