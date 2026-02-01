"""
Configuration constants for the Rubik's Cube Simulator
"""

# Bluetooth cube configuration
CUBE_MAC = "D2:E8:EE:1C:1F:49"
CUBE_NAME = "GiS02881"
CHAR_UUID = "0000aadc-0000-1000-8000-00805f9b34fb"

# BLE timing
BLE_DEBOUNCE_MS = 50  # Ignore same move within this window

# ANSI to curses color mapping
ANSI_TO_CURSES = {
    100: 1,  # Blue
    101: 2,  # White
    102: 3,  # Orange
    103: 4,  # Green
    44: 5,   # Red
    45: 6,   # Yellow
    0: 0,    # Black/Empty
}

# Solved state reference (to check if cube is solved)
SOLVED_STATE = [
    [101, 101, 101, 101, 101, 101, 101, 101, 101],  # Top (White)
    [101, 101, 101, 101, 101, 101, 101, 101, 101],
    [101, 101, 101, 101, 101, 101, 101, 101, 101],
    [102, 102, 102, 103, 103, 103, 44, 44, 44],     # L/F/R (Orange/Green/Red)
    [102, 102, 102, 103, 103, 103, 44, 44, 44],
    [102, 102, 102, 103, 103, 103, 44, 44, 44],
    [0, 0, 0, 45, 45, 45, 0, 0, 0],                  # Bottom (Yellow)
    [0, 0, 0, 45, 45, 45, 0, 0, 0],
    [0, 0, 0, 45, 45, 45, 0, 0, 0],
    [0, 0, 0, 100, 100, 100, 0, 0, 0],               # Back (Blue)
    [0, 0, 0, 100, 100, 100, 0, 0, 0],
    [0, 0, 0, 100, 100, 100, 0, 0, 0],
]
