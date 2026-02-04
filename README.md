# cube

**ASCII Rubik's Cube with GiiKER Smart Cube support**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)

A terminal-based Rubik's Cube simulator that connects to GiiKER smart cubes via Bluetooth. Tracks your solves, shows animated moves in ASCII art, and keeps a history of your times with statistics.

## demo


## features

- **Bluetooth connectivity** - Auto-connects to GiiKER i3S smart cube
- **Animated ASCII cube** - Smooth move animations in the terminal
- **Timer with statistics** - Tracks solves, PBs, Ao5/Ao12 averages
- **Keyboard fallback** - Full keyboard controls when no cube is connected

## usage

```bash
pip install bleak  # Bluetooth dependency
python3 main.py
```

## project structure

```
cube/
├── main.py           # Entry point and game loop
├── bluetooth.py      # BLE connection handling
├── giiker_parser.py  # GiiKER protocol parser
├── cube_state.py     # Cube state management
├── moves.py          # Move logic and mappings
├── animations.py     # ASCII animation loading
├── ui.py             # Timer, instructions, history panel
├── history.py        # Solve history and statistics
├── shuffle.py        # Scramble generation
└── assets/           # ASCII animation frames
```

## credits

[hakatashi/giiker](https://github.com/hakatashi/giiker) - GiiKER Bluetooth protocol documentation and parsing logic
[Icaro-Lima/ASCII-Rubiks-Cube-Simulator](https://github.com/Icaro-Lima/ASCII-Rubiks-Cube-Simulator) - ASCII cube rendering, animation system, and keyboard control mapping

## license

[![GNU GPLv3](https://www.gnu.org/graphics/gplv3-127x51.png)](https://www.gnu.org/licenses/gpl-3.0.en.html)

**cube** is Free Software under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.en.html).

---

<div align="center">
  <b>Made with 🧊 by <a href="https://github.com/josemri">josemri</a></b>
</div>
