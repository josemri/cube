"""
Animation loading and sprite rendering
"""

import curses
from pathlib import Path
from typing import Dict, List

from config import ANSI_TO_CURSES
from cube_state import cube_matrix

# Sprite animations cache
animations: Dict[str, List[str]] = {}


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
    
    # Additional color pairs for shuffle display
    curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Green text
    curses.init_pair(8, curses.COLOR_RED, curses.COLOR_BLACK)     # Red text
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLACK)   # White text


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
                except curses.error:
                    pass
                
                x += (j - i)
                i = j
            else:
                try:
                    stdscr.addch(y, x, char)
                except curses.error:
                    pass
                x += 1
                i += 1
