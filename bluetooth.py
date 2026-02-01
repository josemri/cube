"""
Bluetooth connectivity for smart cube
"""

import asyncio
import time
from bleak import BleakScanner, BleakClient

from config import CUBE_MAC, CUBE_NAME, CHAR_UUID, BLE_DEBOUNCE_MS
import ble_state
from giiker_parser import parse_ble_data, ble_state_to_matrix
from cube_state import compare_with_ble_state, sync_from_ble_matrix


async def find_cube():
    """Scan for Bluetooth cube"""
    try:
        devices = await BleakScanner.discover(timeout=15)
        for d in devices:
            if d.address and d.address.upper() == CUBE_MAC.upper():
                return d
            if d.name and CUBE_NAME.lower() in d.name.lower():
                return d
    except Exception:
        return None
    return None


def on_ble_notify(_, data):
    """Callback for Bluetooth notifications with debounce"""
    
    # Parse cube state from ALL notifications (store for validation)
    cube_state = parse_ble_data(data)
    if cube_state:
        ble_state.ble_cube_state = cube_state
    
    # First signal syncs state completely, doesn't count as a move
    if not ble_state.ble_first_signal_received:
        ble_state.ble_first_signal_received = True
        if cube_state:
            ble_matrix = ble_state_to_matrix(cube_state)
            sync_from_ble_matrix(ble_matrix)
        return
    
    BLE_MOV = {
        0x11: "B",   0x12: "B2",  0x13: "B'",
        0x21: "D",   0x22: "D2",  0x23: "D'",
        0x31: "L",   0x32: "L2",  0x33: "L'",
        0x41: "U",   0x42: "U2",  0x43: "U'",
        0x51: "R",   0x52: "R2",  0x53: "R'",
        0x61: "F",   0x62: "F2",  0x63: "F'",
    }
    
    if len(data) < 4:
        return
    
    code = data[-4]
    move = BLE_MOV.get(code, None)
    
    if move:
        current_time = time.time() * 1000
        
        # Debounce: ignore if same move within debounce window
        if (move == ble_state.last_ble_move and 
            (current_time - ble_state.last_ble_time) < BLE_DEBOUNCE_MS):
            return
        
        ble_state.last_ble_move = move
        ble_state.last_ble_time = current_time
        # Put move for processing (will be executed and verified)
        ble_state.ble_move_queue.put(move)


async def ble_connect_task():
    """Async task to connect to Bluetooth cube"""
    ble_state.ble_status_msg = "BLE: Connecting..."
    
    try:
        client = BleakClient(CUBE_MAC)
        await client.connect(timeout=10)
        
        if client.is_connected:
            ble_state.ble_status_msg = f"BLE: Connected to {CUBE_NAME}"
            ble_state.ble_connected = True
            ble_state.ble_first_signal_received = False
            await client.start_notify(CHAR_UUID, on_ble_notify)
            
            while ble_state.ble_connected:
                await asyncio.sleep(0.1)
            
            await client.stop_notify(CHAR_UUID)
            await client.disconnect()
            return
    except Exception:
        pass
    
    # Fallback: scan for device
    ble_state.ble_status_msg = "BLE: Scanning..."
    device = await find_cube()
    
    if not device:
        ble_state.ble_status_msg = "BLE: Cube not found"
        return
    
    try:
        async with BleakClient(device) as client:
            ble_state.ble_status_msg = f"BLE: Connected to {device.name}"
            ble_state.ble_connected = True
            ble_state.ble_first_signal_received = False
            await client.start_notify(CHAR_UUID, on_ble_notify)
            
            while ble_state.ble_connected:
                await asyncio.sleep(0.1)
            
            await client.stop_notify(CHAR_UUID)
    except Exception as e:
        ble_state.ble_status_msg = f"BLE: Error - {str(e)[:20]}"
        ble_state.ble_connected = False


def start_ble_connection():
    """Start BLE connection in background thread"""
    import threading
    
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ble_connect_task())
    
    ble_state.ble_thread = threading.Thread(target=run_async, daemon=True)
    ble_state.ble_thread.start()
    return ble_state.ble_thread
