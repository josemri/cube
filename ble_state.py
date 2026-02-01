"""
Shared BLE state - accessible from multiple modules
"""

import queue

# Queue for Bluetooth moves
ble_move_queue = queue.Queue()
ble_connected = False
ble_status_msg = "BLE: Not connected"
ble_thread = None

# Debounce state
last_ble_move = None
last_ble_time = 0

# Ignore first signal after connection
ble_first_signal_received = False

# Statistics
move_count = 0
session_best = None

# BLE cube state (parsed from GiiKER data)
ble_cube_state = None

# Current solve move tracking
current_solve_moves = []
