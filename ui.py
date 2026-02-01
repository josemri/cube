"""
UI components - timer display, instructions, and screen drawing
"""

import curses
import time

from animations import draw_sprite, animations
import ble_state
from giiker_parser import ble_state_to_matrix
from cube_state import compare_with_ble_state
from history import get_best_time, get_recent_times, generate_sparkline, add_solve, get_statistics


def format_time(seconds: float) -> str:
    """Format time as MM:SS.cc"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


def draw_status_bar(stdscr, width: int, row: int):
    """Draw BLE status and move count"""
    parts = []
    
    # BLE status
    if ble_state.ble_connected:
        status = "[CONNECTED]"
        color = curses.color_pair(7) | curses.A_BOLD
    else:
        msg = ble_state.ble_status_msg.replace("BLE: ", "")
        status = f"[{msg.upper()}]"
        if "error" in msg.lower() or "not found" in msg.lower():
            color = curses.color_pair(8)
        elif "scanning" in msg.lower() or "connecting" in msg.lower():
            color = curses.color_pair(6)
        else:
            color = curses.color_pair(9)
    
    parts.append((status, color))
    
    # Move count
    if ble_state.move_count > 0:
        parts.append((f"  Moves: {ble_state.move_count}", curses.A_DIM))
    
    # Calculate total width and center
    total_width = sum(len(p[0]) for p in parts)
    col = width // 2 - total_width // 2
    
    try:
        for text, attr in parts:
            stdscr.addstr(row, col, text, attr)
            col += len(text)
    except curses.error:
        pass


def draw_history_panel(stdscr):
    """Draw the history panel overlay"""
    h, w = stdscr.getmaxyx()
    
    # Panel dimensions
    panel_width = 50
    panel_height = 16
    start_row = h // 2 - panel_height // 2
    start_col = w // 2 - panel_width // 2
    
    # Draw panel background/border
    try:
        # Top border
        stdscr.addstr(start_row, start_col, "+" + "-" * (panel_width - 2) + "+", curses.A_BOLD)
        
        # Title
        title = " HISTORY "
        title_col = start_col + (panel_width - len(title)) // 2
        stdscr.addstr(start_row, title_col, title, curses.A_BOLD | curses.color_pair(7))
        
        # Empty lines with borders
        for i in range(1, panel_height - 1):
            stdscr.addstr(start_row + i, start_col, "|" + " " * (panel_width - 2) + "|")
        
        # Bottom border
        stdscr.addstr(start_row + panel_height - 1, start_col, "+" + "-" * (panel_width - 2) + "+", curses.A_BOLD)
        
        # Content
        stats = get_statistics()
        content_col = start_col + 3
        row = start_row + 2
        
        if stats["count"] == 0:
            stdscr.addstr(row + 4, start_col + panel_width // 2 - 8, "No solves yet!", curses.A_DIM)
        else:
            # Personal Best
            pb = get_best_time()
            if pb is not None:
                stdscr.addstr(row, content_col, "Personal Best:", curses.A_BOLD)
                stdscr.addstr(row, content_col + 16, format_time(pb), curses.color_pair(7) | curses.A_BOLD)
            row += 2
            
            # Total solves
            stdscr.addstr(row, content_col, f"Total Solves:   {stats['count']}")
            row += 1
            
            # Average
            stdscr.addstr(row, content_col, f"Average:        {format_time(stats['average'])}")
            row += 1
            
            # Worst
            stdscr.addstr(row, content_col, f"Worst:          {format_time(stats['worst'])}")
            row += 2
            
            # Ao5
            if "ao5" in stats:
                stdscr.addstr(row, content_col, f"Ao5:            {format_time(stats['ao5'])}", curses.color_pair(6))
            else:
                stdscr.addstr(row, content_col, "Ao5:            (need 5 solves)", curses.A_DIM)
            row += 1
            
            # Ao12
            if "ao12" in stats:
                stdscr.addstr(row, content_col, f"Ao12:           {format_time(stats['ao12'])}", curses.color_pair(6))
            else:
                stdscr.addstr(row, content_col, "Ao12:           (need 12 solves)", curses.A_DIM)
            row += 2
            
            # Sparkline
            recent_times = get_recent_times(30)
            if recent_times:
                sparkline = generate_sparkline(recent_times, width=30)
                stdscr.addstr(row, content_col, "Last 30:", curses.A_DIM)
                stdscr.addstr(row + 1, content_col, f"[{sparkline}]", curses.color_pair(6))
        
        # Footer
        footer = "Press any key to close"
        footer_col = start_col + (panel_width - len(footer)) // 2
        stdscr.addstr(start_row + panel_height - 2, footer_col, footer, curses.A_DIM)
        
    except curses.error:
        pass
    
    stdscr.refresh()


def draw_timer_display(stdscr, width: int, timer_mode: bool, timer_running: bool, 
                       timer_start: float, timer_result: float, is_pb: bool = False):
    """Draw the timer display centered above the cube"""
    if not timer_mode:
        return
    
    if timer_running:
        elapsed = time.time() - timer_start
        timer_text = format_time(elapsed)
        label = "SOLVING"
        color = curses.color_pair(6) | curses.A_BOLD
    elif timer_result is not None:
        timer_text = format_time(timer_result)
        if is_pb:
            label = "NEW PB!"
            color = curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK
        else:
            label = "SOLVED!"
            color = curses.color_pair(7) | curses.A_BOLD
    else:
        timer_text = "00:00.00"
        label = "READY"
        color = curses.color_pair(9) | curses.A_BOLD
    
    # Create framed timer display with move count
    if ble_state.move_count > 0:
        display_text = f" {label}: {timer_text} ({ble_state.move_count} moves) "
    else:
        display_text = f" {label}: {timer_text} "
    frame_width = len(display_text) + 2
    col = width // 2 - frame_width // 2
    
    try:
        stdscr.addstr(0, col, "+" + "-" * (frame_width - 2) + "+", color)
        stdscr.addstr(1, col, "|" + display_text + "|", color)
        stdscr.addstr(2, col, "+" + "-" * (frame_width - 2) + "+", color)
    except curses.error:
        pass


def draw_instructions(stdscr, start_row: int):
    """Draw control instructions"""
    h, w = stdscr.getmaxyx()
    
    # Draw separator line
    try:
        stdscr.addstr(start_row, 0, "-" * w, curses.A_DIM)
    except curses.error:
        pass
    
    if ble_state.ble_connected:
        lines = [
            ("BLUETOOTH MODE", curses.A_BOLD),
            ("", 0),
            ("Arrow Keys    Rotate cube view", 0),
            ("X             Shuffle cube", 0),
            ("Space         Toggle timer", 0),
            ("H             History", 0),
            ("Esc           Quit", 0),
        ]
    else:
        lines = [
            ("KEYBOARD MODE", curses.A_BOLD),
            ("", 0),
            ("Rows  7/9 Top   4/6 Mid   1/3 Bot", 0),
            ("Cols  Q/A Left  W/S Mid   E/D Right", 0),
            ("Face  R/F Front T/G Mid   Y/H Back", 0),
            ("", 0),
            ("X=Shuffle  Space=Timer  H=History  B=BLE  Esc=Quit", curses.A_DIM),
        ]
    
    for i, (line, attr) in enumerate(lines):
        try:
            stdscr.addstr(start_row + 1 + i, 2, line, attr)
        except curses.error:
            pass
    
    # Draw rotation indicator on the right
    from cube_state import cube_rotation
    if cube_rotation != 0:
        rotations = ["Front", "Left", "Back", "Right"]
        indicator = f"[View: {rotations[cube_rotation]}]"
        try:
            stdscr.addstr(start_row + 1, w - len(indicator) - 2, indicator, curses.A_DIM)
        except curses.error:
            pass
    
    # Draw status at bottom
    draw_status_bar(stdscr, w, start_row + len(lines) + 2)


def animate_move(stdscr, move_func, move_name: str, timer_state: dict = None, 
                 singmaster_move: str = None):
    """Animate a move with 5 frames, execute logic and verify against BLE state"""
    from cube_state import is_cube_solved, sync_from_ble_matrix
    
    h, w = stdscr.getmaxyx()
    cube_col = w // 2 - 30
    cube_row = 3
    
    # Increment move counter
    ble_state.move_count += 1
    
    # Track move for history (only during timed solves)
    if singmaster_move and timer_state and timer_state.get('timer_running'):
        ble_state.current_solve_moves.append(singmaster_move)
    
    # Execute the logical move
    move_func()
    
    # Validate state against BLE cube if available, silently correct if mismatched
    if ble_state.ble_cube_state is not None:
        ble_matrix = ble_state_to_matrix(ble_state.ble_cube_state)
        matches, _, _ = compare_with_ble_state(ble_matrix)
        
        if not matches:
            # State mismatch: silently impose BLE state
            sync_from_ble_matrix(ble_matrix)
    
    # Check if solved immediately after move
    if timer_state and timer_state.get('timer_mode') and timer_state.get('timer_running'):
        if is_cube_solved():
            timer_state['timer_running'] = False
            timer_state['timer_result'] = time.time() - timer_state['timer_start']
            
            # Check if this is a new PB
            current_pb = get_best_time()
            is_pb = current_pb is None or timer_state['timer_result'] < current_pb
            
            # Save solve to history
            add_solve(
                time_seconds=timer_state['timer_result'],
                moves=ble_state.current_solve_moves.copy(),
                is_pb=is_pb
            )
            
            # Update session best
            if ble_state.session_best is None or timer_state['timer_result'] < ble_state.session_best:
                ble_state.session_best = timer_state['timer_result']
            
            # Mark as PB in timer_state for display
            timer_state['is_pb'] = is_pb
    
    # Check if animation exists
    has_animation = any(f"{move_name}_{frame}" in animations for frame in range(5))
    
    if has_animation:
        # Play 5 animation frames
        for frame in range(5):
            stdscr.clear()
            sprite_key = f"{move_name}_{frame}"
            draw_sprite(stdscr, sprite_key, cube_row, cube_col)
            if timer_state:
                draw_timer_display(stdscr, w, timer_state.get('timer_mode', False),
                                   timer_state.get('timer_running', False),
                                   timer_state.get('timer_start', 0),
                                   timer_state.get('timer_result'),
                                   timer_state.get('is_pb', False))
            draw_instructions(stdscr, h - 9)
            stdscr.refresh()
            time.sleep(0.03)
    else:
        # No animation available
        stdscr.clear()
        draw_sprite(stdscr, "Default", cube_row, cube_col)
        if timer_state:
            draw_timer_display(stdscr, w, timer_state.get('timer_mode', False),
                               timer_state.get('timer_running', False),
                               timer_state.get('timer_start', 0),
                               timer_state.get('timer_result'),
                               timer_state.get('is_pb', False))
        draw_instructions(stdscr, h - 9)
        stdscr.refresh()
        time.sleep(0.1)
    
    # Show final state
    stdscr.clear()
    draw_sprite(stdscr, "Default", cube_row, cube_col)
    if timer_state:
        draw_timer_display(stdscr, w, timer_state.get('timer_mode', False),
                           timer_state.get('timer_running', False),
                           timer_state.get('timer_start', 0),
                           timer_state.get('timer_result'),
                           timer_state.get('is_pb', False))
    draw_instructions(stdscr, h - 9)
    stdscr.refresh()


def redraw_screen(stdscr, cube_row: int, cube_col: int, timer_state: dict = None):
    """Redraw the entire screen"""
    h, w = stdscr.getmaxyx()
    stdscr.clear()
    draw_sprite(stdscr, "Default", cube_row, cube_col)
    if timer_state:
        draw_timer_display(stdscr, w, timer_state.get('timer_mode', False),
                           timer_state.get('timer_running', False),
                           timer_state.get('timer_start', 0),
                           timer_state.get('timer_result'),
                           timer_state.get('is_pb', False))
    draw_instructions(stdscr, h - 9)
    stdscr.refresh()
