import time
import board
import displayio
import framebufferio
import picodvi
from Handlers import input_handler
from Handlers import gamestate 

# 1. Setup Display
displayio.release_displays()
fb = picodvi.Framebuffer(320, 240,
    clk_dp=board.CKP, clk_dn=board.CKN,
    red_dp=board.D0P, red_dn=board.D0N,
    green_dp=board.D1P, green_dn=board.D1N,
    blue_dp=board.D2P, blue_dn=board.D2N,
    color_depth=8)
display = framebufferio.FramebufferDisplay(fb)
root = displayio.Group()
display.root_group = root

# 2. Setup Input
handler = input_handler.InputHandler(sensitivity=1.5)

# 3. Setup Game State Machine
# We pass 'root' so the manager can swap out the graphics
manager = gamestate.GameStateManager(root)
manager.change_state(gamestate.STATE_MENU)

# 4. Main Loop
last_time = time.monotonic()

while True:
    now = time.monotonic()
    dt = now - last_time
    last_time = now

    # A. Update Inputs
    handler.update()

    # B. Update Game State
    # The manager figures out if we are in Menu, Game, or Settings
    # and runs the correct logic.
    manager.update(handler, dt)

    # Small sleep to keep things cool
    time.sleep(0.01)
