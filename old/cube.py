#!/usr/bin/env python3
"""
ASCII Rubik's Cube Simulator with Bluetooth Smart Cube Support
Combines visual 3D simulator with real Bluetooth cube control
"""

import curses
import time
import random
import asyncio
import threading
import queue
from pathlib import Path
from typing import List, Dict, Optional
from bleak import BleakScanner, BleakClient

# Bluetooth cube configuration
CUBE_MAC = "D2:E8:EE:1C:1F:49"
CUBE_NAME = "GiS02881"
CHAR_UUID = "0000aadc-0000-1000-8000-00805f9b34fb"

# Cube state matrix (12x9) - stores ANSI color codes
cube_matrix = [
    [101, 101, 101, 101, 101, 101, 101, 101, 101],  # Row 0-2: Top (White)
    [101, 101, 101, 101, 101, 101, 101, 101, 101],
    [101, 101, 101, 101, 101, 101, 101, 101, 101],
    [102, 102, 102, 103, 103, 103, 44, 44, 44],     # Row 3-5: L/F/R (Orange/Green/Red)
    [102, 102, 102, 103, 103, 103, 44, 44, 44],
    [102, 102, 102, 103, 103, 103, 44, 44, 44],
    [0, 0, 0, 45, 45, 45, 0, 0, 0],                  # Row 6-8: Bottom (Yellow)
    [0, 0, 0, 45, 45, 45, 0, 0, 0],
    [0, 0, 0, 45, 45, 45, 0, 0, 0],
    [0, 0, 0, 100, 100, 100, 0, 0, 0],               # Row 9-11: Back (Blue)
    [0, 0, 0, 100, 100, 100, 0, 0, 0],
    [0, 0, 0, 100, 100, 100, 0, 0, 0],
]

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

# Sprite animations cache
animations: Dict[str, List[str]] = {}

# Queue for Bluetooth moves
ble_move_queue = queue.Queue()
ble_connected = False
ble_status_msg = "BLE: Not connected"
ble_thread = None  # Reference to BLE thread for clean shutdown

# Debounce for BLE moves (prevent duplicates)
last_ble_move = None
last_ble_time = 0
BLE_DEBOUNCE_MS = 50  # Ignore same move within 30ms

# Ignore first signal after connection
ble_first_signal_received = False

# View rotation (0=default, 1=90°CW, 2=180°, 3=270°CW)
view_rotation = 0

# Timer state
timer_mode = False  # True when waiting to start or running
timer_running = False  # True when timer is actively counting
timer_start = 0  # Start time in seconds
timer_result = None  # Final time when solved

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

def is_cube_solved() -> bool:
    """Check if the cube is in solved state"""
    for row in range(12):
        for col in range(9):
            if cube_matrix[row][col] != SOLVED_STATE[row][col]:
                return False
    return True

def format_time(seconds: float) -> str:
    """Format time as MM:SS.cc"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"

def init_colors():
    """Initialize curses color pairs with proper orange color"""
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    
    # Try to use 256-color orange
    if curses.COLORS >= 256:
        curses.init_pair(3, curses.COLOR_BLACK, 208)  # Orange
    else:
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    
    # Additional color pairs for shuffle display (text colors, no background)
    curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Green text (correct)
    curses.init_pair(8, curses.COLOR_RED, curses.COLOR_BLACK)     # Red text (incorrect)
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLACK)   # White text (pending)

def load_animations():
    """Load all sprite animations from Assets folder"""
    assets_path = Path("Assets")
    
    # Load default sprite
    default_file = assets_path / "Default.txt"
    if default_file.exists():
        animations["Default"] = default_file.read_text().splitlines()
    
    # Load animation sprites
    anim_names = [
        "0Left", "0Right", "1Left", "1Right", "2Left", "2Right",
        "AUp", "ADown", "BUp", "BDown", "CUp", "CDown",
        "aClockwise", "aCounterclockwise",
        "bClockwise", "bCounterclockwise",
        "cClockwise", "cCounterclockwise"
    ]
    
    for anim_name in anim_names:
        for frame in range(5):
            key = f"{anim_name}_{frame}"
            sprite_file = assets_path / anim_name / f"{frame}.txt"
            if sprite_file.exists():
                animations[key] = sprite_file.read_text().splitlines()

def get_color_for_char(char: str) -> int:
    """Map character to cube color based on C++ logic"""
    if 'A' <= char <= 'L':
        idx = ord(char) - ord('A')
        return cube_matrix[idx][3]
    elif 'M' <= char <= 'X':
        idx = ord(char) - ord('M')
        return cube_matrix[idx][4]
    elif 'a' <= char <= 'l':
        idx = ord(char) - ord('a')
        return cube_matrix[idx][5]
    elif 'm' <= char <= 'x':
        idx = ord(char) - ord('m')
        row = idx // 3
        col = idx % 3
        return cube_matrix[row + 3][col + 6]
    elif '0' <= char <= '8':
        idx = ord(char) - ord('0')
        row = idx // 3
        col = idx % 3
        return cube_matrix[row + 3][col]
    
    return 0

def draw_sprite(stdscr, sprite_name: str, start_row: int, start_col: int):
    """Draw a sprite with dynamic coloring based on cube state"""
    if sprite_name not in animations:
        return
    
    lines = animations[sprite_name]
    
    for row_idx, line in enumerate(lines):
        y = start_row + row_idx
        x = start_col
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if (('A' <= char <= 'Z') or ('a' <= char <= 'z') or ('0' <= char <= '9')):
                j = i
                while j < len(line) and line[j] == char:
                    j += 1
                
                color_code = get_color_for_char(char)
                curses_color = ANSI_TO_CURSES.get(color_code, 0)
                
                span_text = ' ' * (j - i)
                try:
                    if curses_color > 0:
                        stdscr.addstr(y, x, span_text, curses.color_pair(curses_color))
                    else:
                        stdscr.addstr(y, x, span_text)
                except:
                    pass
                
                x += (j - i)
                i = j
            else:
                try:
                    stdscr.addch(y, x, char)
                except:
                    pass
                x += 1
                i += 1

# === Cube movement logic ===

def get_matrix_line(row: int, cols: List[int]) -> List[int]:
    return [cube_matrix[row][c] for c in cols]

def swap_line(row: int, col_start: int, col_end: int, values: List[int]):
    for i, val in enumerate(values):
        cube_matrix[row][col_start + i] = val

def get_matrix_col(col: int, rows: List[int]) -> List[int]:
    return [cube_matrix[r][col] for r in rows]

def swap_col(col: int, row_start: int, row_end: int, values: List[int]):
    for i, val in enumerate(values):
        cube_matrix[row_start + i][col] = val

def rotate_face_cw(r_start: int, c_start: int, r_end: int, c_end: int):
    a = get_matrix_line(r_start, [c_start, c_start + 1, c_end])
    b = get_matrix_col(c_end, [r_end, r_end - 1, r_start])
    c = get_matrix_line(r_end, [c_start, c_start + 1, c_end])
    d = get_matrix_col(c_start, [r_end, r_end - 1, r_start])
    swap_line(r_start, c_start, c_end, d)
    swap_col(c_start, r_start, r_end, c)
    swap_line(r_end, c_start, c_end, b)
    swap_col(c_end, r_start, r_end, a)

def rotate_face_ccw(r_start: int, c_start: int, r_end: int, c_end: int):
    a = get_matrix_line(r_start, [c_end, c_end - 1, c_start])
    b = get_matrix_col(c_end, [r_start, r_end - 1, r_end])
    c = get_matrix_line(r_end, [c_end, c_end - 1, c_start])
    d = get_matrix_col(c_start, [r_start, r_end - 1, r_end])
    swap_line(r_start, c_start, c_end, b)
    swap_col(c_end, r_start, r_end, c)
    swap_line(r_end, c_start, c_end, d)
    swap_col(c_start, r_start, r_end, a)

# Row movements
def move_0_left():
    a = get_matrix_line(3, [0, 1, 2])
    b = get_matrix_line(3, [3, 4, 5])
    c = get_matrix_line(3, [6, 7, 8])
    d = get_matrix_line(11, [3, 4, 5])
    swap_line(3, 0, 2, b)
    swap_line(3, 3, 5, c)
    swap_line(3, 6, 8, list(reversed(d)))
    swap_line(11, 3, 5, list(reversed(a)))
    rotate_face_cw(0, 3, 2, 5)

def move_0_right():
    for _ in range(3): move_0_left()

def move_1_left():
    a = get_matrix_line(4, [0, 1, 2])
    b = get_matrix_line(4, [3, 4, 5])
    c = get_matrix_line(4, [6, 7, 8])
    d = get_matrix_line(10, [3, 4, 5])
    swap_line(4, 0, 2, b)
    swap_line(4, 3, 5, c)
    swap_line(4, 6, 8, list(reversed(d)))
    swap_line(10, 3, 5, list(reversed(a)))

def move_1_right():
    for _ in range(3): move_1_left()

def move_2_left():
    a = get_matrix_line(5, [0, 1, 2])
    b = get_matrix_line(5, [3, 4, 5])
    c = get_matrix_line(5, [6, 7, 8])
    d = get_matrix_line(9, [3, 4, 5])
    swap_line(5, 0, 2, b)
    swap_line(5, 3, 5, c)
    swap_line(5, 6, 8, list(reversed(d)))
    swap_line(9, 3, 5, list(reversed(a)))
    rotate_face_ccw(6, 3, 8, 5)

def move_2_right():
    for _ in range(3): move_2_left()

# Column movements
def move_A_up():
    a = get_matrix_col(3, [0, 1, 2])
    b = get_matrix_col(3, [3, 4, 5])
    c = get_matrix_col(3, [6, 7, 8])
    d = get_matrix_col(3, [9, 10, 11])
    swap_col(3, 0, 2, b)
    swap_col(3, 3, 5, c)
    swap_col(3, 6, 8, d)
    swap_col(3, 9, 11, a)
    rotate_face_ccw(3, 0, 5, 2)

def move_A_down():
    for _ in range(3): move_A_up()

def move_B_up():
    a = get_matrix_col(4, [0, 1, 2])
    b = get_matrix_col(4, [3, 4, 5])
    c = get_matrix_col(4, [6, 7, 8])
    d = get_matrix_col(4, [9, 10, 11])
    swap_col(4, 0, 2, b)
    swap_col(4, 3, 5, c)
    swap_col(4, 6, 8, d)
    swap_col(4, 9, 11, a)

def move_B_down():
    for _ in range(3): move_B_up()

def move_C_up():
    a = get_matrix_col(5, [0, 1, 2])
    b = get_matrix_col(5, [3, 4, 5])
    c = get_matrix_col(5, [6, 7, 8])
    d = get_matrix_col(5, [9, 10, 11])
    swap_col(5, 0, 2, b)
    swap_col(5, 3, 5, c)
    swap_col(5, 6, 8, d)
    swap_col(5, 9, 11, a)
    rotate_face_cw(3, 6, 5, 8)

def move_C_down():
    for _ in range(3): move_C_up()

# Face rotations
def move_a_cw():
    a = get_matrix_line(2, [3, 4, 5])
    b = get_matrix_col(6, [3, 4, 5])
    c = get_matrix_line(6, [3, 4, 5])
    d = get_matrix_col(2, [3, 4, 5])
    swap_line(2, 3, 5, list(reversed(d)))
    swap_col(2, 3, 5, c)
    swap_line(6, 3, 5, list(reversed(b)))
    swap_col(6, 3, 5, a)
    rotate_face_cw(3, 3, 5, 5)

def move_a_ccw():
    for _ in range(3): move_a_cw()

def move_b_cw():
    a = get_matrix_line(1, [3, 4, 5])
    b = get_matrix_col(7, [3, 4, 5])
    c = get_matrix_line(7, [3, 4, 5])
    d = get_matrix_col(1, [3, 4, 5])
    swap_line(1, 3, 5, list(reversed(d)))
    swap_col(1, 3, 5, c)
    swap_line(7, 3, 5, list(reversed(b)))
    swap_col(7, 3, 5, a)

def move_b_ccw():
    for _ in range(3): move_b_cw()

def move_c_cw():
    a = get_matrix_line(0, [3, 4, 5])
    b = get_matrix_col(8, [3, 4, 5])
    c = get_matrix_line(8, [3, 4, 5])
    d = get_matrix_col(0, [3, 4, 5])
    swap_line(0, 3, 5, list(reversed(d)))
    swap_col(0, 3, 5, c)
    swap_line(8, 3, 5, list(reversed(b)))
    swap_col(8, 3, 5, a)
    rotate_face_ccw(9, 3, 11, 5)

def move_c_ccw():
    for _ in range(3): move_c_cw()

# Whole cube rotations (y-axis: rotate cube left/right)
# Track current rotation state (0=0°, 1=90°left, 2=180°, 3=270°left/90°right)
cube_rotation = 0

def rotate_cube_left():
    """Rotate entire cube 90° to the left (y rotation)"""
    global cube_rotation
    move_0_left()
    move_1_left()
    move_2_left()
    cube_rotation = (cube_rotation + 1) % 4

def rotate_cube_right():
    """Rotate entire cube 90° to the right (y' rotation)"""
    global cube_rotation
    move_0_right()
    move_1_right()
    move_2_right()
    cube_rotation = (cube_rotation - 1) % 4

def translate_move_for_rotation(move: str) -> str:
    """Translate a move based on current cube rotation.
    
    When the cube is rotated, BLE moves need to be remapped so they
    affect the correct face relative to the current orientation.
    
    Rotation left (y): Front→Left, Left→Back, Back→Right, Right→Front
    """
    if cube_rotation == 0:
        return move
    
    # Mapping for horizontal faces (affected by y rotation)
    # After 1 left rotation: physical F (green) is now in Left position
    # So BLE "F" should become simulator "L" (to affect green)
    rotation_map = {
        1: {  # 90° left: F→L, L→B, B→R, R→F
            "F": "L", "F'": "L'",
            "L": "B", "L'": "B'",
            "B": "R", "B'": "R'",
            "R": "F", "R'": "F'",
        },
        2: {  # 180°: F→B, R→L, B→F, L→R
            "F": "B", "F'": "B'",
            "R": "L", "R'": "L'",
            "B": "F", "B'": "F'",
            "L": "R", "L'": "R'",
        },
        3: {  # 270° left (90° right): F→R, R→B, B→L, L→F
            "F": "R", "F'": "R'",
            "R": "B", "R'": "B'",
            "B": "L", "B'": "L'",
            "L": "F", "L'": "F'",
        },
    }
    
    # U and D are not affected by y rotation
    if move in ["U", "U'", "D", "D'"]:
        return move
    
    return rotation_map.get(cube_rotation, {}).get(move, move)

# Singmaster to internal move mapping
SINGMASTER_TO_MOVE = {
    "U": (move_0_left, "0Left"),       # White up = row 0 left
    "U'": (move_0_right, "0Right"),
    "D": (move_2_right, "2Right"),     # Yellow down = row 2 right
    "D'": (move_2_left, "2Left"),
    "L": (move_A_down, "ADown"),       # Orange left = col A down
    "L'": (move_A_up, "AUp"),
    "R": (move_C_up, "CUp"),           # Red right = col C up
    "R'": (move_C_down, "CDown"),
    "F": (move_a_cw, "aClockwise"),    # Green front = face a clockwise
    "F'": (move_a_ccw, "aCounterclockwise"),
    "B": (move_c_ccw, "cCounterclockwise"),  # Blue back = face c ccw
    "B'": (move_c_cw, "cClockwise"),
}

def animate_move(stdscr, move_func, move_name: str, skip_logic: bool = False):
    """Animate a move with 5 frames, execute logic FIRST for accurate timing"""
    global timer_running, timer_result, timer_start
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    cube_row = 3  # Leave space for timer at top
    
    # Execute the logical move FIRST (before animation) for accurate timing
    if not skip_logic:
        move_func()
        
        # Check if solved immediately after move (before animation delay)
        if timer_mode and timer_running and is_cube_solved():
            timer_running = False
            timer_result = time.time() - timer_start
    
    # Check if animation exists
    has_animation = any(f"{move_name}_{frame}" in animations for frame in range(5))
    
    if has_animation:
        # Play 5 animation frames
        for frame in range(5):
            stdscr.clear()
            sprite_key = f"{move_name}_{frame}"
            draw_sprite(stdscr, sprite_key, cube_row, cube_col)
            draw_timer_display(stdscr, w)
            draw_instructions(stdscr, h - 8)
            stdscr.refresh()
            time.sleep(0.03)
    else:
        # No animation available, show static state briefly
        stdscr.clear()
        draw_sprite(stdscr, "Default", cube_row, cube_col)
        draw_timer_display(stdscr, w)
        draw_instructions(stdscr, h - 8)
        stdscr.refresh()
        time.sleep(0.1)
    
    # Show final state
    stdscr.clear()
    draw_sprite(stdscr, "Default", cube_row, cube_col)
    draw_timer_display(stdscr, w)
    draw_instructions(stdscr, h - 8)
    stdscr.refresh()


def draw_timer_display(stdscr, width: int):
    """Draw the timer display centered above the cube"""
    if not timer_mode:
        return
    
    if timer_running:
        elapsed = time.time() - timer_start
        timer_text = format_time(elapsed)
        color = curses.color_pair(6) | curses.A_BOLD  # Yellow
    elif timer_result is not None:
        timer_text = format_time(timer_result)
        color = curses.color_pair(7) | curses.A_BOLD  # Green
    else:
        timer_text = "READY"
        color = curses.color_pair(9) | curses.A_BOLD  # White
    
    # Create framed timer display
    frame_width = len(timer_text) + 4
    col = width // 2 - frame_width // 2
    
    try:
        stdscr.addstr(0, col, "╔" + "═" * (frame_width - 2) + "╗", color)
        stdscr.addstr(1, col, "║ " + timer_text + " ║", color)
        stdscr.addstr(2, col, "╚" + "═" * (frame_width - 2) + "╝", color)
    except:
        pass

def draw_instructions(stdscr, start_row: int):
    """Draw control instructions"""
    if ble_connected:
        instructions = [
            "═══ RUBIK'S CUBE SIMULATOR ═══",
            f"{ble_status_msg}",
            ">>> BLE CONNECTED <<<",
            "←/→=Rotate View  X=Shuffle  SPACE=Timer",
            "",
            "ESC=Quit",
        ]
    else:
        instructions = [
            "═══ RUBIK'S CUBE SIMULATOR ═══",
            f"{ble_status_msg}",
            "Rows: 7/9=Top  4/6=Mid  1/3=Bot",
            "Cols: Q/A=Left W/S=Mid E/D=Right",
            "Face: R/F=Front T/G=Mid Y/H=Back",
            "←/→=Rotate  X=Shuffle  SPACE=Timer  ESC=Quit",
        ]
    
    for i, line in enumerate(instructions):
        try:
            stdscr.addstr(start_row + i, 2, line)
        except:
            pass



def shuffle_cube(stdscr):
    """Shuffle the cube - animated mode for keyboard, interactive for BLE"""
    moves = [
        (move_0_left, "0Left"), (move_0_right, "0Right"),
        (move_1_left, "1Left"), (move_1_right, "1Right"),
        (move_2_left, "2Left"), (move_2_right, "2Right"),
        (move_A_up, "AUp"), (move_A_down, "ADown"),
        (move_B_up, "BUp"), (move_B_down, "BDown"),
        (move_C_up, "CUp"), (move_C_down, "CDown"),
        (move_a_cw, "aClockwise"), (move_a_ccw, "aCounterclockwise"),
        (move_b_cw, "bClockwise"), (move_b_ccw, "bCounterclockwise"),
        (move_c_cw, "cClockwise"), (move_c_ccw, "cCounterclockwise"),
    ]
    
    for _ in range(25):
        func, name = random.choice(moves)
        animate_move(stdscr, func, name)


def get_inverse_move(move: str) -> str:
    """Get the inverse of a Singmaster move"""
    if move.endswith("'"):
        return move[:-1]
    else:
        return move + "'"


def shuffle_cube_ble(stdscr):
    """BLE shuffle mode - shows moves to perform and tracks correct/incorrect"""
    global ble_move_queue
    
    # Available moves in Singmaster notation
    singmaster_moves = ["U", "U'", "D", "D'", "L", "L'", "R", "R'", "F", "F'", "B", "B'"]
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    
    # Generate 20 random shuffle moves
    shuffle_sequence = [random.choice(singmaster_moves) for _ in range(20)]
    
    # State tracking for each move: 'pending', 'correct', 'incorrect'
    move_states = ['pending'] * len(shuffle_sequence)
    current_index = 0  # Current move to perform
    error_stack = []   # Stack of incorrect moves that need to be undone
    
    # Clear BLE queue before starting
    while not ble_move_queue.empty():
        try:
            ble_move_queue.get_nowait()
        except queue.Empty:
            break
    
    def draw_shuffle_screen():
        """Redraw the shuffle screen with current state"""
        stdscr.clear()
        draw_sprite(stdscr, "Default", 0, cube_col)
        
        # Title
        stdscr.addstr(h - 10, 2, "═══ SHUFFLE MODE ═══", curses.A_BOLD)
        stdscr.addstr(h - 9, 2, "Perform moves on the physical cube")
        
        # Build the shuffle display line
        shuffle_row = h - 7
        stdscr.addstr(shuffle_row, 2, "Shuffle: ")
        col = 11
        
        for i, move in enumerate(shuffle_sequence):
            # Determine color based on state
            if move_states[i] == 'correct':
                color = curses.color_pair(7) | curses.A_BOLD  # Green
            elif move_states[i] == 'incorrect':
                color = curses.color_pair(8) | curses.A_BOLD  # Red
            else:  # pending
                if i == current_index and not error_stack:
                    color = curses.color_pair(9) | curses.A_BOLD | curses.A_UNDERLINE  # Current
                else:
                    color = curses.color_pair(9)  # White/pending
            
            move_text = move
            if i < len(shuffle_sequence) - 1:
                move_text += ", "
            
            try:
                stdscr.addstr(shuffle_row, col, move_text, color)
            except:
                pass
            col += len(move_text)
        
        # Error indicator
        if error_stack:
            error_msg = f"✗ Undo {len(error_stack)} incorrect move(s)!"
            stdscr.addstr(h - 5, 2, error_msg, curses.color_pair(8) | curses.A_BOLD)
        
        # Progress
        completed = sum(1 for s in move_states if s == 'correct')
        progress = f"Progress: {completed}/{len(shuffle_sequence)}"
        stdscr.addstr(h - 3, 2, progress)
        stdscr.addstr(h - 2, 2, "ESC=Cancel")
        
        stdscr.refresh()
    
    # Initial draw
    draw_shuffle_screen()
    
    # Main loop
    while current_index < len(shuffle_sequence):
        # Check for ESC key
        try:
            key = stdscr.getch()
            if key == 27:  # ESC
                break
        except:
            pass
        
        # Check for BLE moves
        try:
            if not ble_move_queue.empty():
                ble_move = ble_move_queue.get_nowait()
                # Translate move based on current cube rotation
                translated_move = translate_move_for_rotation(ble_move)
                
                if error_stack:
                    # User has made errors, they need to undo them first
                    last_error = error_stack[-1]
                    expected_undo = get_inverse_move(last_error)
                    
                    if translated_move == expected_undo:
                        # Correct undo - execute inverse and remove from error stack
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        error_stack.pop()
                    else:
                        # Wrong move while trying to undo - add to error stack
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        error_stack.append(translated_move)
                else:
                    # Normal mode - check if move is correct
                    expected_move = shuffle_sequence[current_index]
                    
                    if translated_move == expected_move:
                        # Correct move!
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        move_states[current_index] = 'correct'
                        current_index += 1
                    else:
                        # Incorrect move - execute it but mark as error
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        move_states[current_index] = 'incorrect'
                        error_stack.append(translated_move)
                
                draw_shuffle_screen()
        except queue.Empty:
            pass
        
        time.sleep(0.05)
    
    # Shuffle complete or cancelled
    if current_index >= len(shuffle_sequence):
        stdscr.clear()
        draw_sprite(stdscr, "Default", 0, cube_col)
        stdscr.addstr(h - 7, 2, "═══ SHUFFLE COMPLETE! ═══", curses.color_pair(7) | curses.A_BOLD)
        stdscr.addstr(h - 5, 2, "Press any key to continue...")
        stdscr.refresh()
        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)
    
    # Restore normal display
    stdscr.clear()
    draw_sprite(stdscr, "Default", 0, cube_col)
    draw_instructions(stdscr, h - 10)
    stdscr.refresh()

# === Bluetooth functions ===

async def find_cube():
    """Scan for Bluetooth cube"""
    try:
        devices = await BleakScanner.discover(timeout=15)
        for d in devices:
            # Check by MAC address or name
            if d.address and d.address.upper() == CUBE_MAC.upper():
                return d
            if d.name and CUBE_NAME.lower() in d.name.lower():
                return d
    except Exception as e:
        return None
    return None

def on_ble_notify(_, data):
    """Callback for Bluetooth notifications with debounce"""
    global last_ble_move, last_ble_time, ble_first_signal_received
    
    # Ignore the first signal after connection (initialization message)
    if not ble_first_signal_received:
        ble_first_signal_received = True
        return
    
    BLE_MOV = {
        0x11: "B",   0x13: "B'",
        0x21: "D",   0x23: "D'",
        0x31: "L",   0x33: "L'",
        0x41: "U",   0x43: "U'",
        0x51: "R",   0x53: "R'",
        0x61: "F",   0x63: "F'",
    }
    
    code = data[-4]
    move = BLE_MOV.get(code, None)
    
    if move:
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Debounce: ignore if same move within debounce window
        if move == last_ble_move and (current_time - last_ble_time) < BLE_DEBOUNCE_MS:
            return  # Skip duplicate
        
        # Record this move
        last_ble_move = move
        last_ble_time = current_time
        
        # Add to queue
        ble_move_queue.put(move)

async def ble_connect_task():
    """Async task to connect to Bluetooth cube"""
    global ble_connected, ble_status_msg, ble_first_signal_received
    
    # Try direct connection first (if already paired)
    ble_status_msg = "BLE: Connecting..."
    try:
        client = BleakClient(CUBE_MAC)
        await client.connect(timeout=10)
        
        if client.is_connected:
            ble_status_msg = f"BLE: Connected to {CUBE_NAME}"
            ble_connected = True
            ble_first_signal_received = False
            await client.start_notify(CHAR_UUID, on_ble_notify)
            
            while ble_connected:
                await asyncio.sleep(0.1)
            
            await client.stop_notify(CHAR_UUID)
            await client.disconnect()
            return
    except Exception:
        # Direct connection failed, try scanning
        pass
    
    # Fallback: scan for device
    ble_status_msg = "BLE: Scanning..."
    device = await find_cube()
    
    if not device:
        ble_status_msg = "BLE: Cube not found"
        return
    
    try:
        async with BleakClient(device) as client:
            ble_status_msg = f"BLE: Connected to {device.name}"
            ble_connected = True
            ble_first_signal_received = False  # Reset flag for new connection
            await client.start_notify(CHAR_UUID, on_ble_notify)
            
            while ble_connected:
                await asyncio.sleep(0.1)
            
            await client.stop_notify(CHAR_UUID)
    except Exception as e:
        ble_status_msg = f"BLE: Error - {str(e)[:20]}"
        ble_connected = False

def start_ble_connection():
    """Start BLE connection in background thread"""
    global ble_thread
    
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ble_connect_task())
    
    ble_thread = threading.Thread(target=run_async, daemon=True)
    ble_thread.start()
    return ble_thread

def main(stdscr):
    """Main game loop"""
    global ble_connected, timer_mode, timer_running, timer_start, timer_result
    
    curses.curs_set(0)
    curses.start_color()
    init_colors()
    load_animations()
    stdscr.nodelay(True)  # Non-blocking input
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    cube_row = 3  # Leave space for timer at top
    
    # Draw initial state
    stdscr.clear()
    draw_sprite(stdscr, "Default", cube_row, cube_col)
    draw_timer_display(stdscr, w)
    draw_instructions(stdscr, h - 8)
    stdscr.refresh()
    
    # Auto-connect to Bluetooth cube on startup
    start_ble_connection()
    
    # Key mappings
    key_map = {
        '7': (move_0_left, "0Left"),
        '9': (move_0_right, "0Right"),
        '4': (move_1_left, "1Left"),
        '6': (move_1_right, "1Right"),
        '1': (move_2_left, "2Left"),
        '3': (move_2_right, "2Right"),
        'q': (move_A_up, "AUp"), 'Q': (move_A_up, "AUp"),
        'a': (move_A_down, "ADown"), 'A': (move_A_down, "ADown"),
        'w': (move_B_up, "BUp"), 'W': (move_B_up, "BUp"),
        's': (move_B_down, "BDown"), 'S': (move_B_down, "BDown"),
        'e': (move_C_up, "CUp"), 'E': (move_C_up, "CUp"),
        'd': (move_C_down, "CDown"), 'D': (move_C_down, "CDown"),
        'r': (move_a_cw, "aClockwise"), 'R': (move_a_cw, "aClockwise"),
        'f': (move_a_ccw, "aCounterclockwise"), 'F': (move_a_ccw, "aCounterclockwise"),
        't': (move_b_cw, "bClockwise"), 'T': (move_b_cw, "bClockwise"),
        'g': (move_b_ccw, "bCounterclockwise"), 'G': (move_b_ccw, "bCounterclockwise"),
        'y': (move_c_cw, "cClockwise"), 'Y': (move_c_cw, "cClockwise"),
        'h': (move_c_ccw, "cCounterclockwise"), 'H': (move_c_ccw, "cCounterclockwise"),
    }
    
    last_status = ""
    last_timer_update = 0
    
    while True:
        # Update timer display if running
        if timer_mode and timer_running:
            current_time = time.time()
            if current_time - last_timer_update >= 0.05:  # Update every 50ms
                last_timer_update = current_time
                stdscr.clear()
                draw_sprite(stdscr, "Default", cube_row, cube_col)
                draw_timer_display(stdscr, w)
                draw_instructions(stdscr, h - 8)
                stdscr.refresh()
        
        # Update status message if changed
        if ble_status_msg != last_status:
            last_status = ble_status_msg
            stdscr.clear()
            draw_sprite(stdscr, "Default", cube_row, cube_col)
            draw_timer_display(stdscr, w)
            draw_instructions(stdscr, h - 8)
            stdscr.refresh()
        
        # Check for Bluetooth moves
        try:
            while not ble_move_queue.empty():
                ble_move = ble_move_queue.get_nowait()
                # Translate move based on current cube rotation
                translated_move = translate_move_for_rotation(ble_move)
                if translated_move in SINGMASTER_TO_MOVE:
                    func, name = SINGMASTER_TO_MOVE[translated_move]
                    
                    # Start timer on first move if in timer mode
                    if timer_mode and not timer_running and timer_result is None:
                        timer_running = True
                        timer_start = time.time()
                    
                    animate_move(stdscr, func, name)
        except queue.Empty:
            pass
        
        # Check for keyboard input
        try:
            key = stdscr.getch()
            if key != -1:  # Key was pressed
                if key == 27:  # ESC
                    # Set flag to stop BLE loop (will disconnect in background thread)
                    ble_connected = False
                    
                    # Wait for BLE thread to finish disconnecting (max 3 seconds)
                    if ble_thread and ble_thread.is_alive():
                        stdscr.addstr(h - 1, 2, "Disconnecting BLE...")
                        stdscr.refresh()
                        ble_thread.join(timeout=10.0)
                    
                    break
                
                # Handle SPACE for timer mode
                if key == ord(' '):
                    if not timer_mode:
                        # Enter timer mode only if cube is NOT solved (scrambled)
                        if not is_cube_solved():
                            timer_mode = True
                            timer_running = False
                            timer_result = None
                            stdscr.clear()
                            draw_sprite(stdscr, "Default", cube_row, cube_col)
                            draw_timer_display(stdscr, w)
                            draw_instructions(stdscr, h - 8)
                            stdscr.refresh()
                    else:
                        # Exit timer mode
                        timer_mode = False
                        timer_running = False
                        timer_result = None
                        stdscr.clear()
                        draw_sprite(stdscr, "Default", cube_row, cube_col)
                        draw_timer_display(stdscr, w)
                        draw_instructions(stdscr, h - 8)
                        stdscr.refresh()
                    continue
                
                # Handle arrow keys for cube rotation (works in both modes)
                if key == curses.KEY_LEFT:
                    rotate_cube_left()
                    stdscr.clear()
                    draw_sprite(stdscr, "Default", cube_row, cube_col)
                    draw_timer_display(stdscr, w)
                    draw_instructions(stdscr, h - 8)
                    stdscr.refresh()
                    continue
                elif key == curses.KEY_RIGHT:
                    rotate_cube_right()
                    stdscr.clear()
                    draw_sprite(stdscr, "Default", cube_row, cube_col)
                    draw_timer_display(stdscr, w)
                    draw_instructions(stdscr, h - 8)
                    stdscr.refresh()
                    continue
                
                char = chr(key) if key < 256 else ''
                
                # Shuffle works in both modes (different behavior)
                if char in ['x', 'X']:
                    if ble_connected:
                        shuffle_cube_ble(stdscr)
                    else:
                        shuffle_cube(stdscr)
                # Only process other keyboard commands if BLE is not connected
                elif not ble_connected:
                    if char in ['b', 'B']:
                        start_ble_connection()
                    elif char in key_map:
                        func, name = key_map[char]
                        
                        # Start timer on first move if in timer mode
                        if timer_mode and not timer_running and timer_result is None:
                            timer_running = True
                            timer_start = time.time()
                        
                        animate_move(stdscr, func, name)
        except:
            pass
        
        time.sleep(0.05)  # Small delay to reduce CPU usage

if __name__ == "__main__":
    curses.wrapper(main)
