"""
Cube state management - matrix and state checking functions
"""

from config import SOLVED_STATE

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

# Cube rotation state (0=0°, 1=90°left, 2=180°, 3=270°left)
cube_rotation = 0


def is_cube_solved() -> bool:
    """Check if the cube is in solved state"""
    for row in range(12):
        for col in range(9):
            if cube_matrix[row][col] != SOLVED_STATE[row][col]:
                return False
    return True


def reset_cube():
    """Reset cube to solved state"""
    global cube_rotation
    for row in range(12):
        for col in range(9):
            cube_matrix[row][col] = SOLVED_STATE[row][col]
    cube_rotation = 0


def sync_from_ble_matrix(ble_matrix: list):
    """Sync internal cube_matrix from BLE-derived matrix"""
    for row in range(12):
        for col in range(9):
            cube_matrix[row][col] = ble_matrix[row][col]


def compare_with_ble_state(ble_matrix: list) -> tuple:
    """
    Compare internal cube_matrix with BLE-derived matrix.
    Returns (matches: bool, diff_count: int, first_diff: str)
    """
    diff_count = 0
    first_diff = ""
    
    for row in range(12):
        for col in range(9):
            internal = cube_matrix[row][col]
            external = ble_matrix[row][col]
            
            # Skip empty positions (value 0) - these aren't actual cube faces
            if internal == 0 and external == 0:
                continue
            
            if internal != external:
                diff_count += 1
                if not first_diff:
                    first_diff = f"row={row},col={col}: interno={internal} vs ble={external}"
    
    return (diff_count == 0, diff_count, first_diff)
