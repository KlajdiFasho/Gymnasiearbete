import time
import board
import displayio
import framebufferio
import picodvi
import gc

from Handlers import input_handler
from Handlers import gamestate

# -----------------------------------------------------------
# 1. HARDWARE INITIALIZATION
# -----------------------------------------------------------
print("Initializing Hardware...")
displayio.release_displays()

# Setup HDMI
fb = picodvi.Framebuffer(320, 240,
    clk_dp=board.CKP, clk_dn=board.CKN,
    red_dp=board.D0P, red_dn=board.D0N,
    green_dp=board.D1P, green_dn=board.D1N,
    blue_dp=board.D2P, blue_dn=board.D2N,
    color_depth=8)
display = framebufferio.FramebufferDisplay(fb)

# Create Root Group
root = displayio.Group()
display.root_group = root

# -----------------------------------------------------------
# 2. SYSTEM SETUP
# -----------------------------------------------------------
handler = input_handler.InputHandler(sensitivity=1.5)
manager = gamestate.GameStateManager(root)
manager.change_state(gamestate.STATE_MENU)

# Clean up setup memory
gc.collect()

# -----------------------------------------------------------
# 3. MASTER GAME LOOP
# -----------------------------------------------------------
print("Starting Main Loop...")
last_time = time.monotonic()

while True:
    try:
        # A. Time Management
        now = time.monotonic()
        dt = now - last_time
        last_time = now
        
        # Safety Cap: Prevent physics explosions if game freezes momentarily
        if dt > 0.1: dt = 0.1

        # B. Logic Updates
        handler.update()
        manager.update(handler, dt)

        # C. Frame Rate Control
        # We rely on auto_refresh handling the display sync.
        # A small sleep yields CPU to background tasks.
        time.sleep(0.01)

    except Exception as e:
        print(f"CRITICAL LOOP ERROR: {e}")
        time.sleep(1.0)
