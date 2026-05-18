# PocketPenguin - Gameboy Emulator Project
<img width="382.5" height="510" alt="1000008397" src="https://github.com/user-attachments/assets/ec4d96be-9518-4469-ba07-626618e40eba" /> <img width="382.5" height="510" alt="1000008406" src="https://github.com/user-attachments/assets/54662f19-4685-41a3-a0f9-9aafbddba113" />


## Overview

**PocketPenguin** is a **Gameboy emulator/simulator project** written in **Python**. Originally developed as a "Gymnasiearbete" (a Swedish upper secondary school graduation project), this endeavor combines the nostalgia of classic handheld gaming with a modern, modular interface. PocketPenguin allows users to explore custom games (like Block Breaker and Platformers) while showcasing innovative designs in game development and system emulation.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Screenshots](#screenshots)
4. [Project Structure](#project-structure)
5. [Included Games](#included-games)
6. [Requirements](#requirements)
7. [Setup and Usage](#setup-and-usage)
8. [Future Enhancements](#future-enhancements)
9. [Contributing](#contributing)
10. [Acknowledgments](#acknowledgments)
11. [License](#license)

---

## Introduction

PocketPenguin aims to simulate Gameboy hardware while providing a platform for experimentation with retro gaming. By integrating classic game mechanics, a robust state management system, and custom 8-bit font rendering, this project serves as both an educational tool and a fun gaming experience.

Whether you're nostalgic for Gameboy classics or looking for a customizable emulator as a hobby project, **PocketPenguin** is the perfect starting point.

---

## Features

PocketPenguin includes the following features:

- **Gameboy-Style Emulation**: Simulates the Gameboy's display and functional behavior.
- **Custom Games**:
  - **Block Breaker**: An arcade-style game where you destroy bricks using a bouncing ball.
  - **Platformer**: A 2D side-scrolling game with enemies and platform challenges.
- **Dynamic Game States and UI**:
  - Main Menu, Pause Menu, Settings, Game Over, and Leaderboard management.
- **Custom Fonts**:
  - Retro `.bdf` fonts like `gameboy.bdf` and `mario.bdf` deliver authentic 8-bit aesthetics.
- **High Score Saving**: Scores are saved persistently in a JSON file.
- **Modular Architecture**: Developers can easily add new games or modify system behavior.

---

## Screenshots

<img width="765" height="1020" alt="1000008397" src="https://github.com/user-attachments/assets/ec4d96be-9518-4469-ba07-626618e40eba" />
<img width="263" height="198" alt="Screenshot 2026-05-03 at 17 18 20" src="https://github.com/user-attachments/assets/fc0f8994-9ec5-4bf8-8c43-797279bf2e6b" />
<img width="765" height="1020" alt="1000008406" src="https://github.com/user-attachments/assets/54662f19-4685-41a3-a0f9-9aafbddba113" />
<img width="765" height="1020" alt="1000008412" src="https://github.com/user-attachments/assets/a761a3d2-40b8-46d9-b5f6-32e40783dafc" />
<img width="765" height="1020" alt="1000008410" src="https://github.com/user-attachments/assets/8129437d-5554-4328-a761-d7749c764008" />


---

## Project Structure

### Core Directories

- **Games**: Contains the game logic for `blockbreaker_game.py` and `platformer_game.py`.
- **Handlers**: Includes functionality for input, state management, and system configuration.
- **Fonts**: Directory for `.bdf` fonts like `gameboy.bdf` and `mario.bdf`.
- **code.py**: The main entry point for the project.
- **README.md**: Documentation for the project.

### Additional Resources

- **CadModel**: 3D design files for a physical Gameboy-like case (if applicable).
- **Libraries**: Third-party dependencies or libraries used in the project.
- **Sprites**: Asset directory for icons, images, and other visual resources.

---

## Included Games

### Block Breaker

Bounce a ball to break all bricks on the screen, progressing through levels. The game features responsive paddle movement and escalating difficulty.

### Platformer

Guide the player character through platforms, dodge enemies, and overcome obstacles. This side-scroller includes enemy AI and jumping mechanics.

---

## Requirements

To run this project, you will need:

- **Python 3.7+**
- **Adafruit CircuitPython 8.0.0+**
- Dependencies (installable via `pip`):
  - `adafruit-circuitpython-display-text`
  - `adafruit-circuitpython-displayio-shapes`
  - `adafruit-circuitpython-bitmap-font`

Additional hardware (optional):
- Adafruit FeatherWing joypad or similar for physical controls.

---

## Setup and Usage

### 1. Clone the Repository
```bash
git clone https://github.com/KlajdiFasho/PocketPenguin.git
cd PocketPenguin
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Connect Hardware
Connect a compatible display, joypad (e.g., Adafruit FeatherWing with I2C), and set up inputs as specified in `Handlers/input_handler.py`.

### 4. Run the Simulator
```bash
python code.py
```

The main menu will appear, allowing you to select a game or view the leaderboard.

---

## Future Enhancements

Planned updates include:

- **Gameboy ROM Support**: Add support for loading and running Gameboy ROMs.
- **Additional Games**: Develop more in-built games, such as RPG-style or puzzle games.
- **Save States**: Introduce game save/load functionality.
- **Enhanced Graphics**: Improve the rendering of sprites and animations.

---

## Contributing

Contributions are welcome! To get started:

1. Fork this repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to your branch (`git push origin feature-name`).
5. Open a Pull Request.

Please ensure your code adheres to the project's coding standards and includes proper documentation.

---

## Acknowledgments

Special thanks to:

- **Adafruit**: For providing the CircuitPython libraries and inspiration.
- **FontForge**: For the `.bdf` font utilities.
- Developers of the Python ecosystem for enabling projects like this.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.
