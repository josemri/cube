"""
Shuffle functionality for the cube
"""

import random
import time
import queue
import curses

from moves import (
    move_0_left, move_0_right, move_1_left, move_1_right,
    move_2_left, move_2_right, move_A_up, move_A_down,
    move_B_up, move_B_down, move_C_up, move_C_down,
    move_a_cw, move_a_ccw, move_b_cw, move_b_ccw,
    move_c_cw, move_c_ccw, SINGMASTER_TO_MOVE,
    translate_move_for_rotation, get_inverse_move
)
from animations import draw_sprite
from ui import animate_move
import ble_state


def shuffle_cube(stdscr, timer_state: dict = None):
    """Shuffle the cube - animated mode for keyboard"""
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
    
    # Reset move counter before shuffle
    ble_state.move_count = 0
    
    for _ in range(25):
        func, name = random.choice(moves)
        animate_move(stdscr, func, name, timer_state=timer_state)
    
    # Reset move counter after shuffle (solving starts from 0)
    ble_state.move_count = 0


def shuffle_cube_ble(stdscr):
    """BLE shuffle mode - shows moves to perform and tracks correct/incorrect"""
    from ui import draw_instructions
    
    singmaster_moves = ["U", "U'", "D", "D'", "L", "L'", "R", "R'", "F", "F'", "B", "B'"]
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    
    shuffle_sequence = [random.choice(singmaster_moves) for _ in range(20)]
    move_states = ['pending'] * len(shuffle_sequence)
    current_index = 0
    error_stack = []
    
    # Clear BLE queue before starting
    while not ble_state.ble_move_queue.empty():
        try:
            ble_state.ble_move_queue.get_nowait()
        except queue.Empty:
            break
    
    def draw_shuffle_screen():
        stdscr.clear()
        draw_sprite(stdscr, "Default", 0, cube_col)
        
        # Header
        title = "--- SHUFFLE MODE ---"
        stdscr.addstr(h - 11, w // 2 - len(title) // 2, title, curses.A_BOLD)
        
        # Current move indicator (large, prominent)
        if not error_stack and current_index < len(shuffle_sequence):
            next_move = shuffle_sequence[current_index]
            next_label = f"Next: [{next_move}]"
            stdscr.addstr(h - 9, w // 2 - len(next_label) // 2, next_label, 
                         curses.color_pair(9) | curses.A_BOLD)
        elif error_stack:
            # Show what move to undo
            undo_move = get_inverse_move(error_stack[-1])
            undo_label = f"Undo: [{undo_move}]"
            stdscr.addstr(h - 9, w // 2 - len(undo_label) // 2, undo_label,
                         curses.color_pair(8) | curses.A_BOLD)
        
        # Move sequence
        shuffle_row = h - 7
        stdscr.addstr(shuffle_row, 2, "Sequence:", curses.A_DIM)
        col = 12
        
        for i, move in enumerate(shuffle_sequence):
            is_current = (i == current_index and not error_stack)
            
            if move_states[i] == 'correct':
                # Completed moves: green, no brackets
                display = move
                color = curses.color_pair(7)
            elif move_states[i] == 'incorrect':
                # Incorrect: red
                display = move
                color = curses.color_pair(8) | curses.A_BOLD
            elif is_current:
                # Current move: white bold with brackets
                display = f"[{move}]"
                color = curses.color_pair(9) | curses.A_BOLD
            else:
                # Pending moves: dim
                display = move
                color = curses.color_pair(9) | curses.A_DIM
            
            # Add spacing
            if i < len(shuffle_sequence) - 1:
                display += " "
            
            try:
                stdscr.addstr(shuffle_row, col, display, color)
            except:
                pass
            col += len(display)
        
        # Error message with hint
        if error_stack:
            count = len(error_stack)
            plural = "s" if count > 1 else ""
            error_msg = f"[!] {count} wrong move{plural} - perform {get_inverse_move(error_stack[-1])} to undo"
            stdscr.addstr(h - 5, 2, error_msg, curses.color_pair(8))
        
        # Progress bar
        completed = sum(1 for s in move_states if s == 'correct')
        total = len(shuffle_sequence)
        bar_width = 20
        filled = int(bar_width * completed / total)
        bar = "[" + "=" * filled + " " * (bar_width - filled) + "]"
        pct = int(100 * completed / total)
        progress = f"{bar} {pct}%"
        
        # Center the progress bar
        progress_label = "Progress:"
        stdscr.addstr(h - 3, 2, progress_label, curses.A_DIM)
        stdscr.addstr(h - 3, 2 + len(progress_label) + 1, progress)
        
        # Footer
        footer = "Esc = Cancel"
        stdscr.addstr(h - 1, w // 2 - len(footer) // 2, footer, curses.A_DIM)
        
        stdscr.refresh()
    
    draw_shuffle_screen()
    
    while current_index < len(shuffle_sequence):
        try:
            key = stdscr.getch()
            if key == 27:
                break
        except:
            pass
        
        try:
            if not ble_state.ble_move_queue.empty():
                ble_move = ble_state.ble_move_queue.get_nowait()
                translated_move = translate_move_for_rotation(ble_move)
                
                if error_stack:
                    last_error = error_stack[-1]
                    expected_undo = get_inverse_move(last_error)
                    
                    if translated_move == expected_undo:
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        error_stack.pop()
                    else:
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        error_stack.append(translated_move)
                else:
                    expected_move = shuffle_sequence[current_index]
                    
                    if translated_move == expected_move:
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        move_states[current_index] = 'correct'
                        current_index += 1
                    else:
                        if translated_move in SINGMASTER_TO_MOVE:
                            func, _ = SINGMASTER_TO_MOVE[translated_move]
                            func()
                        move_states[current_index] = 'incorrect'
                        error_stack.append(translated_move)
                
                draw_shuffle_screen()
        except queue.Empty:
            pass
        
        time.sleep(0.05)
    
    if current_index >= len(shuffle_sequence):
        stdscr.clear()
        draw_sprite(stdscr, "Default", 0, cube_col)
        
        # Success message centered
        msg1 = "--- SHUFFLE COMPLETE ---"
        msg2 = "Cube is now scrambled"
        msg3 = "Press Space to start timer, or any key to continue"
        
        stdscr.addstr(h - 7, w // 2 - len(msg1) // 2, msg1, curses.color_pair(7) | curses.A_BOLD)
        stdscr.addstr(h - 5, w // 2 - len(msg2) // 2, msg2)
        stdscr.addstr(h - 3, w // 2 - len(msg3) // 2, msg3, curses.A_DIM)
        
        stdscr.refresh()
        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)
    
    # Reset move counter after shuffle (solving starts from 0)
    ble_state.move_count = 0
    
    stdscr.clear()
    draw_sprite(stdscr, "Default", 0, cube_col)
    from ui import draw_instructions
    draw_instructions(stdscr, h - 10)
    stdscr.refresh()
