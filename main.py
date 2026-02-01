#!/usr/bin/env python3
"""
ASCII Rubik's Cube Simulator with Bluetooth Smart Cube Support
Main entry point
"""

import curses
import time
import queue

from config import ANSI_TO_CURSES
from cube_state import is_cube_solved, reset_cube
from moves import (
    move_0_left, move_0_right, move_1_left, move_1_right,
    move_2_left, move_2_right, move_A_up, move_A_down,
    move_B_up, move_B_down, move_C_up, move_C_down,
    move_a_cw, move_a_ccw, move_b_cw, move_b_ccw,
    move_c_cw, move_c_ccw, rotate_cube_left, rotate_cube_right,
    translate_move_for_rotation, SINGMASTER_TO_MOVE
)
from animations import init_colors, load_animations, draw_sprite
from ui import draw_timer_display, draw_instructions, animate_move, redraw_screen
from bluetooth import start_ble_connection
from shuffle import shuffle_cube, shuffle_cube_ble
import ble_state


def execute_singmaster_move(stdscr, move: str, timer_state: dict):
    """Execute a Singmaster move (including double moves like U2)"""
    # Handle double moves
    if move.endswith("2"):
        base_move = move[:-1]
        if base_move in SINGMASTER_TO_MOVE:
            func, name = SINGMASTER_TO_MOVE[base_move]
            animate_move(stdscr, func, name, timer_state=timer_state, singmaster_move=base_move)
            animate_move(stdscr, func, name, timer_state=timer_state, singmaster_move=base_move)
    elif move in SINGMASTER_TO_MOVE:
        func, name = SINGMASTER_TO_MOVE[move]
        animate_move(stdscr, func, name, timer_state=timer_state, singmaster_move=move)


def main(stdscr):
    """Main game loop"""
    curses.curs_set(0)
    curses.start_color()
    init_colors()
    load_animations()
    stdscr.nodelay(True)
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    cube_row = 3
    
    # Timer state
    timer_state = {
        'timer_mode': False,
        'timer_running': False,
        'timer_start': 0,
        'timer_result': None
    }
    
    # Draw initial state
    redraw_screen(stdscr, cube_row, cube_col, timer_state)
    
    # Auto-connect to Bluetooth cube
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
        if timer_state['timer_mode'] and timer_state['timer_running']:
            current_time = time.time()
            if current_time - last_timer_update >= 0.05:
                last_timer_update = current_time
                redraw_screen(stdscr, cube_row, cube_col, timer_state)
        
        # Update status message if changed
        if ble_state.ble_status_msg != last_status:
            last_status = ble_state.ble_status_msg
            redraw_screen(stdscr, cube_row, cube_col, timer_state)
        
        # Check for Bluetooth moves
        try:
            while not ble_state.ble_move_queue.empty():
                ble_move = ble_state.ble_move_queue.get_nowait()
                
                translated_move = translate_move_for_rotation(ble_move)
                
                # Start timer on first move if in timer mode
                if (timer_state['timer_mode'] and 
                    not timer_state['timer_running'] and 
                    timer_state['timer_result'] is None):
                    timer_state['timer_running'] = True
                    timer_state['timer_start'] = time.time()
                    ble_state.current_solve_moves = []
                
                execute_singmaster_move(stdscr, translated_move, timer_state)
        except queue.Empty:
            pass
        
        # Check for keyboard input
        try:
            key = stdscr.getch()
            if key != -1:
                if key == 27:  # ESC
                    ble_state.ble_connected = False
                    if ble_state.ble_thread and ble_state.ble_thread.is_alive():
                        stdscr.addstr(h - 1, 2, "Disconnecting BLE...")
                        stdscr.refresh()
                        ble_state.ble_thread.join(timeout=10.0)
                    break
                
                # Handle SPACE for timer mode
                if key == ord(' '):
                    if not timer_state['timer_mode']:
                        if not is_cube_solved():
                            timer_state['timer_mode'] = True
                            timer_state['timer_running'] = False
                            timer_state['timer_result'] = None
                            timer_state['is_pb'] = False
                            ble_state.move_count = 0
                            ble_state.current_solve_moves = []
                            redraw_screen(stdscr, cube_row, cube_col, timer_state)
                    else:
                        timer_state['timer_mode'] = False
                        timer_state['timer_running'] = False
                        timer_state['timer_result'] = None
                        timer_state['is_pb'] = False
                        redraw_screen(stdscr, cube_row, cube_col, timer_state)
                    continue
                
                # Handle arrow keys for cube rotation
                if key == curses.KEY_LEFT:
                    rotate_cube_left()
                    redraw_screen(stdscr, cube_row, cube_col, timer_state)
                    continue
                elif key == curses.KEY_RIGHT:
                    rotate_cube_right()
                    redraw_screen(stdscr, cube_row, cube_col, timer_state)
                    continue
                
                char = chr(key) if key < 256 else ''
                
                # Reset cube (C)
                if char in ['c', 'C']:
                    reset_cube()
                    ble_state.move_count = 0
                    timer_state['timer_mode'] = False
                    timer_state['timer_running'] = False
                    timer_state['timer_result'] = None
                    redraw_screen(stdscr, cube_row, cube_col, timer_state)
                    continue
                
                # Shuffle
                if char in ['x', 'X']:
                    if ble_state.ble_connected:
                        shuffle_cube_ble(stdscr)
                    else:
                        shuffle_cube(stdscr, timer_state)
                    continue
                
                # Reconnect BLE (B) - works even when connected to force reconnect
                if char in ['b', 'B']:
                    if ble_state.ble_connected:
                        ble_state.ble_connected = False
                        ble_state.ble_status_msg = "BLE: Reconnecting..."
                    start_ble_connection()
                    continue
                
                # Only process keyboard moves if BLE not connected
                if not ble_state.ble_connected and char in key_map:
                    func, name = key_map[char]
                    
                    if (timer_state['timer_mode'] and 
                        not timer_state['timer_running'] and 
                        timer_state['timer_result'] is None):
                        timer_state['timer_running'] = True
                        timer_state['timer_start'] = time.time()
                        ble_state.current_solve_moves = []
                    
                    animate_move(stdscr, func, name, timer_state=timer_state)
        except curses.error:
            pass
        
        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
