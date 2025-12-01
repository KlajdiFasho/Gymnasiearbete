import time
import math # Added for sensitivity calculations

# try imports for FeatherWing / I2C mode first
try:
    import busio
    import board as _board
    from adafruit_featherwing import joy_featherwing
    _FEATHERWING_AVAILABLE = True
except Exception:
    _FEATHERWING_AVAILABLE = False

# fallback imports for direct-pin mode
try:
    import board
    import digitalio
except Exception:
    board = None
    digitalio = None

try:
    import analogio
except Exception:
    analogio = None

# ----- internal helper: Normalize with calibration -----
def _norm_axis(raw, center, max_val):
    if raw is None: return 0.0
    delta = raw - center
    half_range = max_val / 2.0
    if half_range < 1: half_range = 1
    val = delta / half_range
    if val > 1.0: return 1.0
    if val < -1.0: return -1.0
    return val

class _GPIOButton:
    def __init__(self, name, pin, pull_up=True, invert=True):
        self.name = name
        self.pin = pin
        self.pull_up = pull_up
        self.invert = invert
        self.pin_obj = None
        self._raw = False
        self._stable = False
        self._last_raw_change = time.monotonic()
        self._setup_pin()

    def _setup_pin(self):
        if digitalio is None or self.pin is None:
            self.pin_obj = None
            return
        try:
            di = digitalio.DigitalInOut(self.pin)
            di.direction = digitalio.Direction.INPUT
            try:
                di.pull = digitalio.Pull.UP if self.pull_up else digitalio.Pull.DOWN
            except Exception: pass
            self.pin_obj = di
        except Exception: self.pin_obj = None

    def read_raw(self):
        if self.pin_obj is None: return False
        try: v = self.pin_obj.value
        except Exception: v = False
        logical = (not v) if self.invert else v
        self._raw = bool(logical)
        return self._raw

class InputHandler:
    def __init__(self, button_pins=None, joystick_pins=None,
                 debounce_ms=20, hold_ms=600, repeat_ms=200,
                 joystick_deadzone=0.15, map_joystick_dirs=True,
                 sensitivity=1.0, # 1.0 = Linear, 2.0 = Precision/Curved
                 debug=False, force_mode=None):

        self.debug = bool(debug)
        self.debounce_s = max(0.001, debounce_ms / 1000.0)
        self.hold_s = max(0.01, hold_ms / 1000.0)
        self.repeat_s = max(0.01, repeat_ms / 1000.0)
        self.joystick_deadzone = float(joystick_deadzone)
        self.map_joystick_dirs = bool(map_joystick_dirs)
        self.sensitivity = float(sensitivity)

        self._now = time.monotonic()
        self._callbacks = {}

        # --- STATE ---
        self.buttons = {} # Name -> Object or None
        self.axis = (0.0, 0.0)
        self.directions = {'UP': False, 'DOWN': False, 'LEFT': False, 'RIGHT': False}

        # Frame-based state (For polling "was just pressed")
        self._just_pressed = set()
        self._just_released = set()

        # Calibration & Config
        self._center_xy = (512, 512)
        self._range_max = 1023

        # Hardware Config (Defaults)
        self.config = {
            'swap_xy': False,  # Swap X and Y axes
            'invert_x': False, # Multiply X by -1
            'invert_y': False  # Multiply Y by -1
        }

        # --- HARDWARE INIT ---
        mode = force_mode
        if mode is None:
            mode = 'featherwing' if _FEATHERWING_AVAILABLE else 'direct'
        self.mode = mode

        self._fw = None
        if self.mode == 'featherwing':
            self._init_featherwing()
            # FIX: Switched invert_y to False.
            # If you were getting -1 for UP, this will flip it back to 1.
            self.config['swap_xy'] = True
            self.config['invert_y'] = False

        if self.mode == 'direct':
            self._init_direct(button_pins, joystick_pins)

    # ---------------- INIT HELPERS ----------------
    def _init_featherwing(self):
        try:
            i2c = busio.I2C(_board.SCL, _board.SDA)
            t0 = time.monotonic()
            while not i2c.try_lock() and (time.monotonic() - t0) < 0.25: pass
            try: i2c.scan()
            finally:
                try: i2c.unlock()
                except: pass

            self._fw = joy_featherwing.JoyFeatherWing(i2c)
            self._fw_map = { "A": "button_a", "B": "button_b", "X": "button_x", "Y": "button_y", "SEL": "button_select" }
            for k in self._fw_map.keys(): self.buttons[k] = None

            # Calibration
            try:
                cx, cy = self._fw.joystick
                if cx > 20000 or cy > 20000: self._range_max = 65535
                elif cx > 1500 or cy > 1500: self._range_max = 4095
                elif cx > 200 or cy > 200: self._range_max = 1023
                else: self._range_max = 255
                self._center_xy = (cx, cy)
                if self.debug: print(f"Calibrated: Center={self._center_xy}, Max={self._range_max}")
            except: pass
        except Exception as e:
            self._fw = None
            self.mode = 'direct' # Fallback
            if self.debug: print("FW Init failed, fallback.", e)

    def _init_direct(self, button_pins, joystick_pins):
        button_pins = button_pins or {}
        for name, pin in button_pins.items():
            self.buttons[name] = _GPIOButton(name, pin)
        self._analog = None
        if joystick_pins and analogio is not None:
            try:
                ax = analogio.AnalogIn(joystick_pins[0])
                ay = analogio.AnalogIn(joystick_pins[1])
                self._analog = (ax, ay)
                self._range_max = 65535
                self._center_xy = (32768, 32768)
            except: self._analog = None

    # ---------------- PUBLIC API ----------------
    def set_axis_config(self, swap_xy=False, invert_x=False, invert_y=False):
        """Reconfigure axis mapping at runtime"""
        self.config['swap_xy'] = swap_xy
        self.config['invert_x'] = invert_x
        self.config['invert_y'] = invert_y

    def on(self, name, event, func):
        if name not in self._callbacks: self._callbacks[name] = {}
        if event not in self._callbacks[name]: self._callbacks[name][event] = []
        self._callbacks[name][event].append(func)

    def update(self):
        """Call this once per main loop iteration"""
        self._now = time.monotonic()
        # Reset frame-based buffers
        self._just_pressed.clear()
        self._just_released.clear()

        if self.mode == 'featherwing' and self._fw is not None:
            self._update_from_featherwing()
        else:
            self._update_from_direct()

    # --- POLLING API (Better for Game Loops) ---
    def is_pressed(self, name):
        """Is the button currently held down?"""
        if self.mode == 'featherwing' and self._fw is not None:
            # FW logic relies on cached state to be fast
            return getattr(self, "_prev_" + name, False)
        else:
            b = self.buttons.get(name)
            return bool(b and b._stable)

    def was_just_pressed(self, name):
        """Did the button go from Up->Down *this frame*?"""
        return name in self._just_pressed

    def was_just_released(self, name):
        """Did the button go from Down->Up *this frame*?"""
        return name in self._just_released

    def get_axis(self):
        return self.axis

    def get_direction(self):
        return dict(self.directions)

    # ---------------- INTERNAL UPDATES ----------------
    def _process_axis(self, raw_x, raw_y):
        cx, cy = self._center_xy
        rmax = self._range_max

        # 1. Normalize
        nx = _norm_axis(raw_x, cx, rmax)
        ny = _norm_axis(raw_y, cy, rmax)

        # 2. Configurable Swap
        if self.config['swap_xy']:
            nx, ny = ny, nx

        # 3. Configurable Invert
        if self.config['invert_x']: nx = -nx
        if self.config['invert_y']: ny = -ny

        # 4. Deadzone
        if abs(nx) < self.joystick_deadzone: nx = 0.0
        if abs(ny) < self.joystick_deadzone: ny = 0.0

        # 5. Sensitivity Curve (Exponential)
        # Sign * (AbsValue ^ Sensitivity)
        if self.sensitivity != 1.0:
            if nx != 0: nx = math.copysign(abs(nx) ** self.sensitivity, nx)
            if ny != 0: ny = math.copysign(abs(ny) ** self.sensitivity, ny)

        self.axis = (nx, ny)

        if self.map_joystick_dirs:
            self.directions['UP'] = ny > self.joystick_deadzone
            self.directions['DOWN'] = ny < -self.joystick_deadzone
            self.directions['LEFT'] = nx < -self.joystick_deadzone
            self.directions['RIGHT'] = nx > self.joystick_deadzone

    def _handle_button_logic(self, name, cur_state):
        prev = getattr(self, "_prev_" + name, False)

        # Detect Edges
        if cur_state and not prev:
            self._just_pressed.add(name)
            self._fire_callbacks(name, "pressed")
            setattr(self, "_press_time_" + name, self._now)
            setattr(self, "_hold_fired_" + name, False)
            setattr(self, "_last_repeat_" + name, self._now)
        elif not cur_state and prev:
            self._just_released.add(name)
            self._fire_callbacks(name, "released")
            setattr(self, "_press_time_" + name, None)

        setattr(self, "_prev_" + name, cur_state)

        # Handle Holds/Repeats
        press_time = getattr(self, "_press_time_" + name, None)
        if press_time is not None:
            if (not getattr(self, "_hold_fired_" + name, False)) and (self._now - press_time >= self.hold_s):
                setattr(self, "_hold_fired_" + name, True)
                self._fire_callbacks(name, "held")
                setattr(self, "_last_repeat_" + name, self._now)
            if getattr(self, "_hold_fired_" + name, False) and (self._now - getattr(self, "_last_repeat_" + name, 0) >= self.repeat_s):
                setattr(self, "_last_repeat_" + name, self._now)
                self._fire_callbacks(name, "repeat")

    def _update_from_featherwing(self):
        try:
            rx, ry = self._fw.joystick
            self._process_axis(rx, ry)
        except: pass

        for name, attr in self._fw_map.items():
            try: cur = bool(getattr(self._fw, attr))
            except: cur = False
            self._handle_button_logic(name, cur)

    def _update_from_direct(self):
        # Buttons
        for name, b in self.buttons.items():
            raw = b.read_raw()
            # Simple software debounce
            if raw != getattr(b, "_prev_raw", None):
                b._prev_raw = raw
                b._last_raw_change = self._now

            cur_stable = getattr(b, "_stable", False)
            if (self._now - b._last_raw_change) >= self.debounce_s:
                if raw != cur_stable:
                    b._stable = raw

            # Use the unified handler logic, passing the stable state
            self._handle_button_logic(name, b._stable)

        # Joystick
        if getattr(self, "_analog", None) is not None:
            ax, ay = self._analog
            try:
                self._process_axis(ax.value, ay.value)
            except: pass

    def _fire_callbacks(self, name, event):
        if name in self._callbacks and event in self._callbacks[name]:
            for cb in self._callbacks[name][event]:
                try: cb(name)
                except: pass
