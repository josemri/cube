"""
GiiKER Cube state parser - converts BLE data to cube state
Based on the GiiKER protocol for smart cubes.
"""

# Face indices
B, D, L, U, R, F = 0, 1, 2, 3, 4, 5
FACES = ['B', 'D', 'L', 'U', 'R', 'F']

# Color indices (GiiKER format)
b, y, o, w, r, g = 0, 1, 2, 3, 4, 5
COLORS = ['blue', 'yellow', 'orange', 'white', 'red', 'green']

# Color mapping from GiiKER to internal ANSI codes
GIIKER_TO_ANSI = {
    'blue': 100,
    'yellow': 45,
    'orange': 102,
    'white': 101,
    'red': 44,
    'green': 103,
}

# Corner colors (solved state)
CORNER_COLORS = [
    [y, r, g],  # Corner 1
    [r, w, g],  # Corner 2
    [w, o, g],  # Corner 3
    [o, y, g],  # Corner 4
    [r, y, b],  # Corner 5
    [w, r, b],  # Corner 6
    [o, w, b],  # Corner 7
    [y, o, b],  # Corner 8
]

# Corner locations (which faces each corner touches)
CORNER_LOCATIONS = [
    [D, R, F],  # Position 0
    [R, U, F],  # Position 1
    [U, L, F],  # Position 2
    [L, D, F],  # Position 3
    [R, D, B],  # Position 4
    [U, R, B],  # Position 5
    [L, U, B],  # Position 6
    [D, L, B],  # Position 7
]

# Edge colors (solved state)
EDGE_COLORS = [
    [g, y],  # Edge 1
    [g, r],  # Edge 2
    [g, w],  # Edge 3
    [g, o],  # Edge 4
    [y, r],  # Edge 5
    [w, r],  # Edge 6
    [w, o],  # Edge 7
    [y, o],  # Edge 8
    [b, y],  # Edge 9
    [b, r],  # Edge 10
    [b, w],  # Edge 11
    [b, o],  # Edge 12
]

# Edge locations (which faces each edge touches)
EDGE_LOCATIONS = [
    [F, D],  # Position 0
    [F, R],  # Position 1
    [F, U],  # Position 2
    [F, L],  # Position 3
    [D, R],  # Position 4
    [U, R],  # Position 5
    [U, L],  # Position 6
    [D, L],  # Position 7
    [B, D],  # Position 8
    [B, R],  # Position 9
    [B, U],  # Position 10
    [B, L],  # Position 11
]


def parse_cube_value(data: bytes) -> dict:
    """
    Parse the 20 bytes from GiiKER cube.
    Returns corner/edge positions and orientations.
    """
    state = {
        'corner_positions': [],
        'corner_orientations': [],
        'edge_positions': [],
        'edge_orientations': [],
    }
    
    for i, byte in enumerate(data):
        high_nibble = byte >> 4
        low_nibble = byte & 0b1111
        
        if i < 4:
            state['corner_positions'].extend([high_nibble, low_nibble])
        elif i < 8:
            state['corner_orientations'].extend([high_nibble, low_nibble])
        elif i < 14:
            state['edge_positions'].extend([high_nibble, low_nibble])
        elif i < 16:
            state['edge_orientations'].append(bool(byte & 0b10000000))
            state['edge_orientations'].append(bool(byte & 0b01000000))
            state['edge_orientations'].append(bool(byte & 0b00100000))
            state['edge_orientations'].append(bool(byte & 0b00010000))
            if i == 14:
                state['edge_orientations'].append(bool(byte & 0b00001000))
                state['edge_orientations'].append(bool(byte & 0b00000100))
                state['edge_orientations'].append(bool(byte & 0b00000010))
                state['edge_orientations'].append(bool(byte & 0b00000001))
    
    return state


def map_corner_colors(corner_colors: list, orientation: int, position: int) -> list:
    """Map corner colors based on orientation."""
    actual_colors = [0, 0, 0]
    
    if orientation != 3:
        if position in [0, 2, 5, 7]:
            orientation = 3 - orientation
    
    if orientation == 1:
        actual_colors[0] = corner_colors[1]
        actual_colors[1] = corner_colors[2]
        actual_colors[2] = corner_colors[0]
    elif orientation == 2:
        actual_colors[0] = corner_colors[2]
        actual_colors[1] = corner_colors[0]
        actual_colors[2] = corner_colors[1]
    else:
        actual_colors[0] = corner_colors[0]
        actual_colors[1] = corner_colors[1]
        actual_colors[2] = corner_colors[2]
    
    return actual_colors


def map_edge_colors(edge_colors: list, orientation: bool) -> list:
    """Map edge colors based on orientation (flipped or not)."""
    if orientation:
        return edge_colors[::-1]
    return edge_colors[:]


def get_cube_state(parsed_state: dict) -> dict:
    """
    Convert parsed state to a readable format with face colors.
    Returns a dict with 'corners' and 'edges' arrays.
    """
    state = {'corners': [], 'edges': []}
    
    for index, corner_pos in enumerate(parsed_state['corner_positions']):
        orientation = parsed_state['corner_orientations'][index]
        corner_colors = CORNER_COLORS[corner_pos - 1]
        mapped_colors = map_corner_colors(corner_colors, orientation, index)
        
        state['corners'].append({
            'position': [FACES[f] for f in CORNER_LOCATIONS[index]],
            'colors': [COLORS[c] for c in mapped_colors],
        })
    
    for index, edge_pos in enumerate(parsed_state['edge_positions']):
        orientation = parsed_state['edge_orientations'][index]
        edge_colors = EDGE_COLORS[edge_pos - 1]
        mapped_colors = map_edge_colors(edge_colors, orientation)
        
        state['edges'].append({
            'position': [FACES[f] for f in EDGE_LOCATIONS[index]],
            'colors': [COLORS[c] for c in mapped_colors],
        })
    
    return state


def ble_state_to_matrix(ble_state: dict) -> list:
    """
    Convert GiiKER state to a 12x9 matrix format matching cube_matrix.
    
    Matrix layout:
    - Rows 0-2: Top face (U) - White
    - Rows 3-5: Left(L)/Front(F)/Right(R) middle band
    - Rows 6-8: Bottom face (D) - Yellow
    - Rows 9-11: Back face (B) - Blue
    """
    # Initialize with zeros (black/empty)
    matrix = [[0 for _ in range(9)] for _ in range(12)]
    
    # Face arrays (9 stickers each, indexed 0-8)
    # Sticker positions on each face:
    #   0 1 2
    #   3 4 5
    #   6 7 8
    faces = {
        'U': [0] * 9,  # Top (white)
        'D': [0] * 9,  # Bottom (yellow)
        'F': [0] * 9,  # Front (green)
        'B': [0] * 9,  # Back (blue)
        'L': [0] * 9,  # Left (orange)
        'R': [0] * 9,  # Right (red)
    }
    
    # Set center colors (fixed)
    faces['U'][4] = 'white'
    faces['D'][4] = 'yellow'
    faces['F'][4] = 'green'
    faces['B'][4] = 'blue'
    faces['L'][4] = 'orange'
    faces['R'][4] = 'red'
    
    # Corner sticker positions on each face
    # GiiKER corner order: [face1, face2, face3] -> colors[0], colors[1], colors[2]
    # Face sticker indices (looking at face from outside):
    #   0 1 2
    #   3 4 5
    #   6 7 8
    CORNER_STICKERS = {
        # Corner 0: D-R-F position
        0: [('D', 8), ('R', 6), ('F', 8)],
        # Corner 1: R-U-F position  
        1: [('R', 0), ('U', 8), ('F', 2)],
        # Corner 2: U-L-F position
        2: [('U', 6), ('L', 2), ('F', 0)],
        # Corner 3: L-D-F position
        3: [('L', 8), ('D', 6), ('F', 6)],
        # Corner 4: R-D-B position
        4: [('R', 8), ('D', 2), ('B', 6)],
        # Corner 5: U-R-B position
        5: [('U', 2), ('R', 2), ('B', 0)],
        # Corner 6: L-U-B position
        6: [('L', 0), ('U', 0), ('B', 2)],
        # Corner 7: D-L-B position
        7: [('D', 0), ('L', 6), ('B', 8)],
    }
    
    # Edge sticker positions on each face
    EDGE_STICKERS = {
        # Edge 0: F-D
        0: [('F', 7), ('D', 7)],
        # Edge 1: F-R
        1: [('F', 5), ('R', 3)],
        # Edge 2: F-U
        2: [('F', 1), ('U', 7)],
        # Edge 3: F-L
        3: [('F', 3), ('L', 5)],
        # Edge 4: D-R
        4: [('D', 5), ('R', 7)],
        # Edge 5: U-R
        5: [('U', 5), ('R', 1)],
        # Edge 6: U-L
        6: [('U', 3), ('L', 1)],
        # Edge 7: D-L
        7: [('D', 3), ('L', 7)],
        # Edge 8: B-D
        8: [('B', 7), ('D', 1)],
        # Edge 9: B-R
        9: [('B', 3), ('R', 5)],
        # Edge 10: B-U
        10: [('B', 1), ('U', 1)],
        # Edge 11: B-L
        11: [('B', 5), ('L', 3)],
    }
    
    # Fill corners
    for i, corner in enumerate(ble_state['corners']):
        stickers = CORNER_STICKERS[i]
        for j, (face, pos) in enumerate(stickers):
            faces[face][pos] = corner['colors'][j]
    
    # Fill edges
    for i, edge in enumerate(ble_state['edges']):
        stickers = EDGE_STICKERS[i]
        for j, (face, pos) in enumerate(stickers):
            faces[face][pos] = edge['colors'][j]
    
    # Convert faces to matrix
    # Top face (U): rows 0-2, all 9 columns
    for i in range(3):
        for j in range(9):
            face_col = j % 3
            color = faces['U'][i * 3 + face_col]
            matrix[i][j] = GIIKER_TO_ANSI.get(color, 0)
    
    # Middle band: Left (cols 0-2), Front (cols 3-5), Right (cols 6-8)
    for i in range(3):
        for j in range(3):
            # Left face
            color = faces['L'][i * 3 + j]
            matrix[i + 3][j] = GIIKER_TO_ANSI.get(color, 0)
            # Front face
            color = faces['F'][i * 3 + j]
            matrix[i + 3][j + 3] = GIIKER_TO_ANSI.get(color, 0)
            # Right face
            color = faces['R'][i * 3 + j]
            matrix[i + 3][j + 6] = GIIKER_TO_ANSI.get(color, 0)
    
    # Bottom face (D): rows 6-8, cols 3-5 only
    for i in range(3):
        for j in range(3):
            color = faces['D'][i * 3 + j]
            matrix[i + 6][j + 3] = GIIKER_TO_ANSI.get(color, 0)
    
    # Back face (B): rows 9-11, cols 3-5 only
    for i in range(3):
        for j in range(3):
            color = faces['B'][i * 3 + j]
            matrix[i + 9][j + 3] = GIIKER_TO_ANSI.get(color, 0)
    
    return matrix


def parse_ble_data(data: bytes) -> dict:
    """
    Main entry point: parse BLE data and return structured state.
    Returns the full cube state with corners and edges.
    """
    if len(data) < 16:
        return None
    
    parsed = parse_cube_value(data)
    return get_cube_state(parsed)
