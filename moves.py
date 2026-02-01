"""
Cube movement logic - all rotation and movement functions
"""

from typing import List
from cube_state import cube_matrix, cube_rotation


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


# Whole cube rotations
def rotate_cube_left():
    """Rotate entire cube 90° to the left (y rotation)"""
    import cube_state
    move_0_left()
    move_1_left()
    move_2_left()
    cube_state.cube_rotation = (cube_state.cube_rotation + 1) % 4


def rotate_cube_right():
    """Rotate entire cube 90° to the right (y' rotation)"""
    import cube_state
    move_0_right()
    move_1_right()
    move_2_right()
    cube_state.cube_rotation = (cube_state.cube_rotation - 1) % 4


def translate_move_for_rotation(move: str) -> str:
    """Translate a move based on current cube rotation."""
    import cube_state
    
    if cube_state.cube_rotation == 0:
        return move
    
    # Handle double moves (U2, R2, etc.)
    is_double = move.endswith("2")
    if is_double:
        base = move[:-1]
        suffix = "2"
    elif move.endswith("'"):
        base = move[:-1]
        suffix = "'"
    else:
        base = move
        suffix = ""
    
    rotation_map = {
        1: {"F": "L", "L": "B", "B": "R", "R": "F"},
        2: {"F": "B", "R": "L", "B": "F", "L": "R"},
        3: {"F": "R", "R": "B", "B": "L", "L": "F"},
    }
    
    # U and D are not affected by y rotation
    if base in ["U", "D"]:
        return move
    
    if base in rotation_map.get(cube_state.cube_rotation, {}):
        return rotation_map[cube_state.cube_rotation][base] + suffix
    
    return move


# Singmaster notation mapping
SINGMASTER_TO_MOVE = {
    "U": (move_0_left, "0Left"),
    "U'": (move_0_right, "0Right"),
    "D": (move_2_right, "2Right"),
    "D'": (move_2_left, "2Left"),
    "L": (move_A_down, "ADown"),
    "L'": (move_A_up, "AUp"),
    "R": (move_C_up, "CUp"),
    "R'": (move_C_down, "CDown"),
    "F": (move_a_cw, "aClockwise"),
    "F'": (move_a_ccw, "aCounterclockwise"),
    "B": (move_c_ccw, "cCounterclockwise"),
    "B'": (move_c_cw, "cClockwise"),
}


def get_inverse_move(move: str) -> str:
    """Get the inverse of a Singmaster move"""
    if move.endswith("'"):
        return move[:-1]
    else:
        return move + "'"
