---
title: "Callback Patterns Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "30-45 minutes"
user_personas: ["script_developer", "interactive_designer", "network_programmer"]
operators: ["oscInDAT", "tcpipDAT", "udpInDAT", "udpOutDAT", "textCOMP", "listCOMP"]
concepts: ["callbacks", "event_handling", "network_communication", "ui_interaction", "drag_and_drop"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "network_protocols"]
workflows: ["interactive_systems", "network_communication", "event_driven_programming"]
keywords: ["callbacks", "osc", "tcp", "udp", "drag_drop", "text_comp", "list_comp", "network"]
tags: ["python", "callbacks", "network", "ui", "events", "examples"]
related_docs: ["EX_EXECUTE_DATS", "EX_OSC_UDP", "EX_UI", "CLASS_DAT_Class"]
example_count: 19
---

# TouchDesigner Python Examples: Callback Patterns

## Overview

Comprehensive examples for implementing callbacks in TouchDesigner, focusing on network communication, UI component interaction, drag-and-drop operations, and event handling patterns. These examples demonstrate how to create responsive systems that react to external data, user interaction, and component events.

**Source**: TouchDesigner Help > Python Examples > Callbacks  
**Example Count**: 19 files  
**Focus**: Network callbacks, UI interaction, drag-and-drop, event handling

## Quick Reference

### Network Communication

- **[OSC Callbacks](#osc-callbacks)** - Open Sound Control message handling
- **[TCP/IP Callbacks](#tcpip-callbacks)** - TCP network communication patterns  
- **[UDP Callbacks](#udp-callbacks)** - UDP data transmission handling

### UI Component Callbacks

- **[Text COMP Callbacks](#text-comp-callbacks)** - Text component interaction and editing
- **[List COMP Callbacks](#list-comp-callbacks)** - List component formatting and interaction
- **[Panel Callbacks](#panel-callbacks)** - General panel component interactions

### Advanced Interaction Patterns  

- **[Drag-and-Drop Callbacks](#drag-and-drop-callbacks)** - Drag-and-drop implementation
- **[Callback Best Practices](#callback-best-practices)** - Efficient callback patterns
- **[Event Coordination](#event-coordination)** - Managing complex callback interactions

---

## OSC Callbacks

### OSC Message Reception

**Source Files**: `oscin1_callbacks.py`, `test_osc.txt`

**Key Concepts**: OSC message handling, address parsing, argument processing

```python
# Global variables available in OSC In DAT callbacks:
# me - this DAT
# dat - the DAT that received a message
# rowIndex - the row number the message was placed into
# message - an ascii representation of the data
# bytes - a byte array of the message
# timeStamp - the arrival time component of the OSC message
# address - the address component of the OSC message (/path/to/target)
# args - a list of values contained within the OSC message
# peer - a Peer object describing the originating message

def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """Called when OSC message is received"""
    print("onReceiveOSC", dat, rowIndex, message, bytes, timeStamp, address, args, peer, sep='\n\t')
    
    # Parse OSC address for routing
    if address.startswith('/control/'):
        handle_control_message(address, args)
    elif address.startswith('/data/'):
        handle_data_message(address, args)
    elif address.startswith('/trigger/'):
        handle_trigger_message(address, args)
    
    # Access peer information
    sender_address = peer.address
    sender_port = peer.port
    print(f'Message from {sender_address}:{sender_port}')
    
    print('------------------------------------------------')

def handle_control_message(address, args):
    """Handle control-related OSC messages"""
    # Extract control target from address
    # e.g., /control/volume/main -> ['', 'control', 'volume', 'main']
    path_parts = address.split('/')
    
    if len(path_parts) >= 4:
        control_type = path_parts[2]  # 'volume'
        control_target = path_parts[3]  # 'main'
        
        if control_type == 'volume' and len(args) > 0:
            volume_value = float(args[0])
            set_volume(control_target, volume_value)
        
        elif control_type == 'parameter' and len(args) >= 2:
            param_name = str(args[0])
            param_value = args[1]
            set_parameter(control_target, param_name, param_value)

def handle_data_message(address, args):
    """Handle data transmission OSC messages"""
    path_parts = address.split('/')
    
    if len(path_parts) >= 3:
        data_type = path_parts[2]
        
        if data_type == 'sensors' and len(args) >= 3:
            # Sensor data: [x, y, z] accelerometer values
            x, y, z = float(args[0]), float(args[1]), float(args[2])
            update_sensor_data(x, y, z)
        
        elif data_type == 'color' and len(args) >= 3:
            # Color data: [r, g, b] values
            r, g, b = float(args[0]), float(args[1]), float(args[2])
            update_color_values(r, g, b)

def handle_trigger_message(address, args):
    """Handle trigger/event OSC messages"""
    # Triggers often don't need arguments
    trigger_name = address.split('/')[-1]  # Get last part of address
    
    if trigger_name == 'start':
        start_performance()
    elif trigger_name == 'stop':
        stop_performance()
    elif trigger_name == 'reset':
        reset_system()
```

### OSC Message Sending

**Source File**: `test_osc.txt`

```python
# Send OSC messages using OSC Out DAT
def send_osc_message():
    """Send OSC message with mixed argument types"""
    osc_out = op('oscout1')
    
    # Send message with address and argument list
    # Arguments can be: int, float, string
    osc_out.sendOSC("/abc", [1, 2.5, 'a'])
    
    # Send control messages
    osc_out.sendOSC("/control/volume/main", [0.75])
    osc_out.sendOSC("/control/parameter", ["frequency", 440.0])
    
    # Send data arrays
    sensor_data = [0.1, -0.3, 9.8]  # x, y, z acceleration
    osc_out.sendOSC("/data/sensors/accel", sensor_data)
    
    # Send trigger events (no arguments needed)
    osc_out.sendOSC("/trigger/start", [])

# Advanced OSC sending patterns
def send_complex_osc_data():
    """Send complex data structures via OSC"""
    osc_out = op('oscout1')
    
    # Send multiple related values
    position = [10.5, 20.3, 5.8]
    rotation = [0.0, 45.0, 0.0]
    scale = [1.0, 1.0, 1.0]
    
    # Bundle related transforms
    osc_out.sendOSC("/object/transform/position", position)
    osc_out.sendOSC("/object/transform/rotation", rotation)
    osc_out.sendOSC("/object/transform/scale", scale)
    
    # Send state information
    state_data = ["active", 1, 100.0]  # status, id, value
    osc_out.sendOSC("/object/state", state_data)
```

---

## TCP/IP Callbacks

### TCP Connection Management

**Source File**: `tcpip1_callbacks.py`

**Key Concepts**: Connection lifecycle, data reception, peer management

```python
# Global variables available in TCP/IP DAT callbacks:
# me - this DAT
# dat - the DAT that received the data
# rowIndex - the row number the data was placed into
# message - an ascii representation of the data
# bytes - a byte array of the data received
# peer - a Peer object describing the connection

def onConnect(dat, peer):
    """Called when a new TCP connection is established"""
    print(f'TCP connection established from {peer.address}:{peer.port}')
    
    # Store connection information
    connection_info = {
        'address': peer.address,
        'port': peer.port,
        'connect_time': absTime.seconds
    }
    
    # Add to active connections list
    active_connections = me.parent().fetch('active_connections', [])
    active_connections.append(connection_info)
    me.parent().store('active_connections', active_connections)
    
    # Send welcome message to new connection
    welcome_msg = f"Welcome from TouchDesigner at {absTime.seconds}\n"
    send_tcp_message(dat, welcome_msg.encode())
    
    return

def onReceive(dat, rowIndex, message, bytes, peer):
    """Called when TCP data is received"""
    print('onReceive TCP/IP', dat, rowIndex, message, bytes, peer, sep='\n\t')
    
    # Decode message for processing
    try:
        decoded_message = bytes.decode('utf-8').strip()
        process_tcp_command(dat, decoded_message, peer)
    except UnicodeDecodeError:
        # Handle binary data
        process_binary_tcp_data(dat, bytes, peer)

def onClose(dat, peer):
    """Called when TCP connection is closed"""
    print(f'TCP connection closed: {peer.address}:{peer.port}')
    
    # Remove from active connections
    active_connections = me.parent().fetch('active_connections', [])
    active_connections = [conn for conn in active_connections 
                         if not (conn['address'] == peer.address and conn['port'] == peer.port)]
    me.parent().store('active_connections', active_connections)
    
    # Log connection duration
    debug(f'Connection from {peer.address} duration: {absTime.seconds} seconds')
    
    return

def process_tcp_command(dat, command, peer):
    """Process text-based TCP commands"""
    parts = command.split(' ')
    cmd = parts[0].upper() if parts else ''
    
    if cmd == 'GET':
        # Handle GET requests
        if len(parts) > 1:
            parameter = parts[1]
            value = get_system_parameter(parameter)
            response = f"VALUE {parameter} {value}\n"
        else:
            response = "ERROR Missing parameter name\n"
        
        send_tcp_response(dat, response, peer)
    
    elif cmd == 'SET':
        # Handle SET commands
        if len(parts) >= 3:
            parameter = parts[1]
            value = ' '.join(parts[2:])  # Join remaining parts as value
            set_system_parameter(parameter, value)
            response = f"OK Set {parameter} to {value}\n"
        else:
            response = "ERROR Invalid SET command format\n"
        
        send_tcp_response(dat, response, peer)
    
    elif cmd == 'LIST':
        # List available parameters
        params = get_available_parameters()
        response = f"PARAMS {' '.join(params)}\n"
        send_tcp_response(dat, response, peer)
    
    else:
        response = f"ERROR Unknown command: {cmd}\n"
        send_tcp_response(dat, response, peer)

def send_tcp_response(dat, response, peer):
    """Send response back to specific TCP peer"""
    try:
        # For TCP/IP Out DAT, send to specific peer
        tcp_out = op('tcpip_out')  # Corresponding output operator
        if tcp_out:
            tcp_out.send(response.encode(), peer=peer)
    except Exception as e:
        debug(f'Error sending TCP response: {e}')
```

### TCP Protocol Patterns

```python
def process_binary_tcp_data(dat, bytes, peer):
    """Handle binary TCP data protocols"""
    
    # Simple binary protocol example:
    # First byte = message type
    # Next 4 bytes = data length (little endian)
    # Remaining bytes = payload
    
    if len(bytes) < 5:
        debug('TCP: Message too short for binary protocol')
        return
    
    message_type = bytes[0]
    data_length = int.from_bytes(bytes[1:5], byteorder='little')
    
    if len(bytes) < 5 + data_length:
        debug('TCP: Incomplete binary message')
        return
    
    payload = bytes[5:5+data_length]
    
    if message_type == 0x01:  # Position data
        handle_position_data(payload, peer)
    elif message_type == 0x02:  # Color data
        handle_color_data(payload, peer)
    elif message_type == 0x03:  # Control command
        handle_control_data(payload, peer)
    else:
        debug(f'TCP: Unknown binary message type: {message_type}')

def handle_position_data(payload, peer):
    """Handle binary position data (12 bytes: 3 floats)"""
    if len(payload) == 12:
        import struct
        x, y, z = struct.unpack('<fff', payload)  # Little endian floats
        update_position_from_tcp(x, y, z, peer.address)

def create_tcp_server_system():
    """Create a comprehensive TCP server system"""
    # Initialize server state
    server_state = {
        'clients': {},
        'commands': {},
        'broadcast_list': []
    }
    
    me.parent().store('tcp_server_state', server_state)
    
    # Register command handlers
    register_tcp_command('ECHO', handle_echo_command)
    register_tcp_command('TIME', handle_time_command)
    register_tcp_command('STATUS', handle_status_command)

def register_tcp_command(command, handler):
    """Register a command handler for TCP server"""
    server_state = me.parent().fetch('tcp_server_state', {})
    if 'commands' not in server_state:
        server_state['commands'] = {}
    
    server_state['commands'][command] = handler
    me.parent().store('tcp_server_state', server_state)
```

---

## UDP Callbacks

### UDP Data Reception

**Source Files**: `udpin1_callbacks.py`, `test_udp.txt`

**Key Concepts**: UDP message handling, broadcast reception, peer identification

```python
# UDP callbacks similar to TCP but connectionless
# Global variables: me, dat, rowIndex, message, bytes, peer

def onReceive(dat, rowIndex, message, bytes, peer):
    """Called when UDP data is received"""
    print('onReceive UDP', dat, rowIndex, message, bytes, peer)
    
    # UDP is connectionless, so each message is independent
    try:
        decoded_message = bytes.decode('utf-8').strip()
        
        # Handle different UDP message types
        if decoded_message.startswith('BROADCAST:'):
            handle_broadcast_message(decoded_message[10:], peer)
        elif decoded_message.startswith('DISCOVERY:'):
            handle_discovery_request(peer)
        else:
            handle_general_udp_message(decoded_message, peer)
    
    except UnicodeDecodeError:
        handle_binary_udp_data(bytes, peer)

def handle_broadcast_message(message, peer):
    """Handle broadcast messages from network"""
    print(f'Broadcast from {peer.address}: {message}')
    
    # Parse broadcast data
    if message.startswith('TIME:'):
        sync_time = float(message[5:])
        synchronize_with_network_time(sync_time, peer.address)
    
    elif message.startswith('STATE:'):
        state_data = message[6:]
        update_network_state(state_data, peer.address)

def handle_discovery_request(peer):
    """Respond to network discovery requests"""
    # Send response back via UDP Out
    udp_out = op('udpout1')
    
    discovery_response = f"RESPONSE:{me.parent().name}:{absTime.seconds}"
    udp_out.send(discovery_response, peer.address, peer.port)

def handle_binary_udp_data(bytes, peer):
    """Handle binary UDP protocols (sensor data, etc.)"""
    # Example: Simple sensor data protocol
    # 4 bytes per float, expecting 3 floats (x, y, z)
    
    if len(bytes) == 12:  # 3 floats * 4 bytes each
        import struct
        try:
            x, y, z = struct.unpack('!fff', bytes)  # Network byte order
            update_sensor_position(x, y, z, peer.address)
        except struct.error as e:
            debug(f'UDP binary decode error: {e}')
    else:
        debug(f'Unexpected UDP binary message length: {len(bytes)}')

# UDP Broadcasting patterns
def send_udp_broadcast():
    """Send UDP broadcast messages"""
    udp_out = op('udpout1')
    
    # Time sync broadcast
    current_time = absTime.seconds
    time_msg = f"BROADCAST:TIME:{current_time}"
    udp_out.send(time_msg, '255.255.255.255', 8000)  # Broadcast
    
    # State broadcast
    state_msg = f"BROADCAST:STATE:active"
    udp_out.send(state_msg, '255.255.255.255', 8000)

def create_udp_network_discovery():
    """Implement UDP network discovery system"""
    
    # Store discovered peers
    discovered_peers = me.parent().fetch('discovered_peers', {})
    
    def send_discovery_ping():
        udp_out = op('udpout1')
        discovery_msg = f"DISCOVERY:{me.parent().name}"
        udp_out.send(discovery_msg, '255.255.255.255', 9000)
    
    def handle_discovery_response(response, peer):
        parts = response.split(':')
        if len(parts) >= 3 and parts[0] == 'RESPONSE':
            peer_name = parts[1]
            peer_time = float(parts[2])
            
            discovered_peers[peer.address] = {
                'name': peer_name,
                'last_seen': absTime.seconds,
                'time_offset': peer_time - absTime.seconds
            }
            
            me.parent().store('discovered_peers', discovered_peers)
            debug(f'Discovered peer: {peer_name} at {peer.address}')
```

---

## Text COMP Callbacks

### Text Component Interaction

**Source File**: `text1_callbacks.py`

**Key Concepts**: Text editing, focus management, value change detection

```python
# Text Component callbacks for user input handling

def onValueChange(comp, value, prevValue):
    """
    Called when the text component's value parameter changes
    (typing, parameter modification, etc.)
    """
    debug('\nonValueChange comp:', comp.path, '- new value: ', value, ', prev value: ', prevValue)
    
    # Validate input in real-time
    if len(value) > 100:
        debug('Warning: Text exceeds maximum length')
    
    # Update dependent components
    update_text_dependent_systems(comp, value)
    
    # Log text changes for undo/history
    log_text_change(comp, value, prevValue)
    
    print('---------------------------------------------')

def onFocus(comp):
    """
    Called when text component viewer gets keyboard focus
    """
    debug('\nonFocus comp:', comp.path)
    
    # Set up editing environment
    setup_text_editing_mode(comp)
    
    # Highlight related components
    highlight_text_component(comp, True)
    
    print('---------------------------------------------')

def onFocusEnd(comp, info):
    """
    Called when text component viewer loses keyboard focus
    info contains reason: 'enter', 'escape', 'tab', 'unknown'
    """
    debug('\nonFocusEnd comp:', comp.path, '- info:\n', info)
    
    reason = info.get('reason', 'unknown')
    
    if reason == 'enter':
        # User pressed Enter - finalize input
        finalize_text_input(comp)
    elif reason == 'escape':
        # User cancelled - revert changes
        revert_text_changes(comp)
    elif reason == 'tab':
        # User tabbed away - move to next field
        move_to_next_text_field(comp)
    
    # Clean up editing mode
    cleanup_text_editing_mode(comp)
    highlight_text_component(comp, False)
    
    print('---------------------------------------------')

def onTextEdit(comp):
    """
    Called continuously while editing (each character typed)
    Use comp.editText to access current editing content
    """
    current_text = comp.editText
    debug('\nonTextEdit comp:', comp.path, '- text: ', current_text)
    
    # Real-time validation feedback
    provide_realtime_feedback(comp, current_text)
    
    # Auto-completion suggestions
    if len(current_text) > 2:
        show_autocomplete_suggestions(comp, current_text)
    
    print('---------------------------------------------')

def onTextEditEnd(comp, value, prevValue):
    """
    Called when editing finishes and value changed (not in Continuous Edit mode)
    """
    debug('\nonTextEditEnd comp:', comp.path, '- new value: ', value, ', prev value: ', prevValue)
    
    # Final validation
    if validate_final_text(value):
        commit_text_change(comp, value)
    else:
        # Revert invalid input
        comp.par.text = prevValue
        show_validation_error(comp, value)
    
    print('---------------------------------------------')

# Supporting functions for text component callbacks

def setup_text_editing_mode(comp):
    """Prepare UI for text editing"""
    # Change component appearance to indicate editing
    if hasattr(comp.par, 'bgcolorr'):
        comp.par.bgcolorr = 0.9
        comp.par.bgcolorg = 0.9
        comp.par.bgcolorb = 1.0

def cleanup_text_editing_mode(comp):
    """Restore normal component appearance"""
    if hasattr(comp.par, 'bgcolorr'):
        comp.par.bgcolorr = 0.5
        comp.par.bgcolorg = 0.5
        comp.par.bgcolorb = 0.5

def provide_realtime_feedback(comp, current_text):
    """Provide real-time feedback during editing"""
    # Character count feedback
    char_count = len(current_text)
    max_chars = 50
    
    if char_count > max_chars * 0.9:  # Warn at 90% capacity
        debug(f'Approaching character limit: {char_count}/{max_chars}')

def validate_final_text(text):
    """Validate completed text input"""
    # Example validations
    if len(text.strip()) == 0:
        return False  # Empty text not allowed
    
    if len(text) > 100:
        return False  # Too long
    
    # Check for invalid characters
    invalid_chars = ['<', '>', '|', '*']
    if any(char in text for char in invalid_chars):
        return False
    
    return True

def log_text_change(comp, value, prev_value):
    """Log text changes for history/undo functionality"""
    change_log = me.parent().fetch('text_change_log', [])
    
    change_record = {
        'component': comp.path,
        'new_value': value,
        'previous_value': prev_value,
        'timestamp': absTime.seconds,
        'frame': absTime.frame
    }
    
    change_log.append(change_record)
    
    # Keep only last 50 changes
    if len(change_log) > 50:
        change_log.pop(0)
    
    me.parent().store('text_change_log', change_log)
```

---

## List COMP Callbacks

### List Component Formatting and Interaction

**Source File**: `list1_callbacks.py`

**Key Concepts**: Dynamic list formatting, cell styling, user interaction

```python
# List Component callbacks for dynamic table formatting and interaction
# Global variables: comp, row, col, attribs (for formatting callbacks)

def onInitCell(comp, row, col, attribs):
    """Called during Reset or on load for each cell"""
    # Set cell content
    attribs.text = f'{row}, {col}'
    
    # Special formatting for specific cells
    if row == col == 1:
        attribs.bgColor = [0.6, 0, 0, 1]  # Red background for diagonal
    
    # Alternating row colors
    if row % 2 == 0:
        attribs.bgColor = [0.95, 0.95, 0.95, 1]  # Light gray
    
    # Column-specific formatting
    if col == 0:  # First column (headers)
        attribs.fontBold = True
        attribs.textColor = [0, 0, 0.8, 1]  # Dark blue text

def onInitRow(comp, row, attribs):
    """Called for each row during initialization"""
    if row == 1:
        attribs.rowStretch = True  # Make row 1 stretchy
    
    # Set row height based on content
    if row == 0:  # Header row
        attribs.rowHeight = 30
    else:
        attribs.rowHeight = 25

def onInitCol(comp, col, attribs):
    """Called for each column during initialization"""
    attribs.colStretch = True  # Make all columns stretchy
    
    # Column-specific widths
    if col == 0:  # First column
        attribs.colWidth = 100
    elif col == 1:  # Second column
        attribs.colWidth = 150
    else:
        attribs.colWidth = 80

def onInitTable(comp, attribs):
    """Called once during table initialization"""
    attribs.fontBold = True  # Make entire table bold
    # Set default font properties
    attribs.fontSizeX = 12
    attribs.fontSizeY = 12

# Interaction callbacks
def onRollover(comp, row, col, coords, prevRow, prevCol, prevCoords):
    """Called when mouse moves over cells"""
    # Uncomment to see rollover events
    # print('onRollover', row, col)
    
    # Highlight row on rollover
    if row != prevRow and row >= 0:
        highlight_table_row(comp, row, True)
    
    if prevRow >= 0 and prevRow != row:
        highlight_table_row(comp, prevRow, False)
    
    return

def onSelect(comp, startRow, startCol, startCoords, endRow, endCol, endCoords, start, end):
    """Called when selection changes"""
    print('onSelect', startRow, startCol, endRow, endCol, start, end)
    
    # Handle selection events
    if startRow == endRow and startCol == endCol:
        # Single cell selection
        handle_single_cell_selection(comp, startRow, startCol)
    else:
        # Multi-cell selection
        handle_range_selection(comp, startRow, startCol, endRow, endCol)
    
    return

def onRadio(comp, row, col, prevRow, prevCol):
    """Called when radio selection changes"""
    print(f'Radio selection: ({row}, {col}), previous: ({prevRow}, {prevCol})')
    
    # Handle radio button behavior
    update_radio_selection(comp, row, col, prevRow, prevCol)
    
    return

def onFocus(comp, row, col, prevRow, prevCol):
    """Called when cell focus changes"""
    print(f'Focus changed to: ({row}, {col})')
    
    # Update focus indicators
    update_cell_focus_indicators(comp, row, col, prevRow, prevCol)
    
    return

def onEdit(comp, row, col, val):
    """Called when cell editing completes"""
    print(f'Cell edit complete: ({row}, {col}) = {val}')
    
    # Validate and process edited value
    if validate_cell_value(row, col, val):
        commit_cell_edit(comp, row, col, val)
    else:
        reject_cell_edit(comp, row, col, val)
    
    return

# Supporting functions for list component callbacks

def highlight_table_row(comp, row, highlight):
    """Highlight/unhighlight a table row"""
    # This would require custom implementation based on your needs
    # Could update cell backgrounds, add visual indicators, etc.
    pass

def handle_single_cell_selection(comp, row, col):
    """Handle single cell selection events"""
    # Get cell data from source table
    source_table = get_list_data_source(comp)
    if source_table and row < source_table.numRows and col < source_table.numCols:
        cell_value = source_table[row, col]
        
        # Trigger actions based on cell selection
        if col == 0:  # First column might be commands
            execute_table_command(str(cell_value))
        elif row == 0:  # Header row might be sortable
            sort_table_by_column(comp, col)

def handle_range_selection(comp, start_row, start_col, end_row, end_col):
    """Handle multi-cell selection"""
    selection_data = []
    source_table = get_list_data_source(comp)
    
    if source_table:
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if row < source_table.numRows and col < source_table.numCols:
                    selection_data.append(str(source_table[row, col]))
    
    # Process selected data
    process_selection_data(selection_data)

def validate_cell_value(row, col, value):
    """Validate edited cell values"""
    # Column-specific validation
    if col == 0:  # First column might be names
        return len(str(value).strip()) > 0
    elif col == 1:  # Second column might be numbers
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    return True  # Accept other values

def create_dynamic_list_content():
    """Create dynamically updating list content"""
    # This function would be called periodically to update list data
    source_data = generate_list_data()
    
    # Update the table that feeds the list component
    data_table = op('list_data_table')
    if data_table:
        data_table.clear()
        
        # Add headers
        data_table.appendRow(['Name', 'Value', 'Status', 'Time'])
        
        # Add data rows
        for item in source_data:
            data_table.appendRow([
                item.get('name', ''),
                str(item.get('value', 0)),
                item.get('status', 'Unknown'),
                str(item.get('timestamp', absTime.seconds))
            ])
```

---

## Drag-and-Drop Callbacks

### Container Drag-and-Drop Implementation

**Source File**: `container1_dragdrop.py`

**Key Concepts**: Drop acceptance, drag item handling, result reporting

```python
# Drag-and-Drop callbacks for Panel Components

def onHoverStartGetAccept(comp, info):
    """
    Called when component needs to know if dragItems are acceptable
    
    Args:
        comp: the panel component being hovered over
        info: Dictionary with dragItems, callbackPanel
    
    Returns:
        True if comp can receive dragItems
    """
    debug('\nonHoverStartGetAccept comp:', comp.path, '- info:\n', info)
    
    drag_items = info.get('dragItems', [])
    
    # Check what types of items are being dragged
    acceptable_types = []
    
    for item in drag_items:
        if isinstance(item, str):
            # String data (text, file paths, etc.)
            if item.endswith('.jpg') or item.endswith('.png'):
                acceptable_types.append('image')
            elif item.endswith('.wav') or item.endswith('.mp3'):
                acceptable_types.append('audio')
            else:
                acceptable_types.append('text')
        elif hasattr(item, 'path'):
            # TouchDesigner operator
            acceptable_types.append('operator')
    
    # Accept based on component's acceptance criteria
    component_accepts = comp.tags.get('accepts', 'all')
    
    if component_accepts == 'all':
        return True
    elif component_accepts == 'images' and 'image' in acceptable_types:
        return True
    elif component_accepts == 'operators' and 'operator' in acceptable_types:
        return True
    
    return False  # Reject by default

def onHoverEnd(comp, info):
    """
    Called when dragItems leave component's hover area
    """
    debug('\nonHoverEnd comp:', comp.path, '- info:\n', info)
    
    # Clean up hover visual feedback
    remove_drop_target_highlight(comp)

def onDropGetResults(comp, info):
    """
    Called when component receives a drop of dragItems
    Only called if onHoverStartGetAccept returned True
    
    Returns:
        Dictionary of results describing what happened
    """
    debug('\nonDropGetResults comp:', comp.path, '- info:\n', info)
    
    drag_items = info.get('dragItems', [])
    results = {'droppedOn': comp}
    
    created_ops = []
    modified_objects = []
    
    for item in drag_items:
        if isinstance(item, str):
            # Handle string data (file paths, text, etc.)
            result = handle_string_drop(comp, item)
            if result:
                created_ops.extend(result.get('created', []))
                modified_objects.extend(result.get('modified', []))
        
        elif hasattr(item, 'path'):
            # Handle TouchDesigner operator drops
            result = handle_operator_drop(comp, item)
            if result:
                created_ops.extend(result.get('created', []))
                modified_objects.extend(result.get('modified', []))
    
    # Update results dictionary
    if created_ops:
        results['createdOPs'] = created_ops
    if modified_objects:
        results['modified'] = modified_objects
    
    # Clean up drop visual feedback
    remove_drop_target_highlight(comp)
    
    return results

# Drag source callbacks

def onDragStartGetItems(comp, info):
    """
    Called when drag operation starts from this component
    
    Returns:
        List of dragItems to be dragged
    """
    debug('\nonDragStartGetItems comp:', comp.path, '- info:\n', info)
    
    # Determine what to drag based on component content
    drag_items = []
    
    # Example: Drag text content from text component
    if comp.op('text1'):
        text_value = comp.op('text1').par.value.eval()
        drag_items.append(text_value)
    
    # Example: Drag operator references
    child_ops = comp.children
    for child_op in child_ops:
        if hasattr(child_op, 'path'):
            drag_items.append(child_op)
    
    # Example: Drag file references
    if hasattr(comp, 'tags') and 'file_path' in comp.tags:
        drag_items.append(comp.tags['file_path'])
    
    return drag_items

def onDragEnd(comp, info):
    """
    Called when drag operation ends
    
    Args:
        info: Dictionary containing accepted, dropResults, dragItems, callbackPanel
    """
    debug('\nonDragEnd comp:', comp.path, '- info:\n', info)
    
    accepted = info.get('accepted', False)
    drop_results = info.get('dropResults', {})
    drag_items = info.get('dragItems', [])
    
    if accepted:
        # Drag was successful
        handle_successful_drag(comp, drop_results, drag_items)
    else:
        # Drag was rejected or cancelled
        handle_failed_drag(comp, drag_items)

# Supporting functions for drag-and-drop

def handle_string_drop(comp, item):
    """Handle dropping of string data onto component"""
    results = {'created': [], 'modified': []}
    
    # File path handling
    if item.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        # Create Movie File In TOP for image
        movie_in = comp.create(moviefileinTOP, 'dropped_image')
        movie_in.par.file = item
        results['created'].append(movie_in)
    
    elif item.endswith(('.wav', '.mp3', '.aiff')):
        # Create Audio File In CHOP for audio
        audio_in = comp.create(audiofileinCHOP, 'dropped_audio') 
        audio_in.par.file = item
        results['created'].append(audio_in)
    
    else:
        # Create Text DAT for other strings
        text_dat = comp.create(textDAT, 'dropped_text')
        text_dat.text = item
        results['created'].append(text_dat)
    
    return results

def handle_operator_drop(comp, operator):
    """Handle dropping of TouchDesigner operators"""
    results = {'created': [], 'modified': []}
    
    # Create reference to dropped operator
    if hasattr(operator, 'type'):
        op_type = operator.type
        
        # Create appropriate reference operator
        if 'TOP' in str(op_type):
            ref_op = comp.create(inTOP, f'ref_{operator.name}')
            ref_op.par.top = operator
        elif 'CHOP' in str(op_type):
            ref_op = comp.create(inCHOP, f'ref_{operator.name}')
            ref_op.par.chop = operator
        elif 'DAT' in str(op_type):
            ref_op = comp.create(inDAT, f'ref_{operator.name}')
            ref_op.par.dat = operator
        else:
            # Create null operator with path reference
            ref_op = comp.create(nullTOP, f'ref_{operator.name}')
            ref_op.comment = f'Reference to: {operator.path}'
        
        results['created'].append(ref_op)
    
    return results

def remove_drop_target_highlight(comp):
    """Remove visual feedback for drop target"""
    # Example: Reset component color to normal
    if hasattr(comp.par, 'bgcolorr'):
        comp.par.bgcolorr = 0.5
        comp.par.bgcolorg = 0.5  
        comp.par.bgcolorb = 0.5

def handle_successful_drag(comp, drop_results, drag_items):
    """Handle successful completion of drag operation"""
    created_ops = drop_results.get('createdOPs', [])
    
    debug(f'Drag successful: {len(created_ops)} operators created')
    
    # Log successful drag operation
    log_drag_operation(comp, drag_items, drop_results, success=True)

def handle_failed_drag(comp, drag_items):
    """Handle failed or cancelled drag operation"""
    debug(f'Drag cancelled or failed for {len(drag_items)} items')
    
    # Log failed drag operation
    log_drag_operation(comp, drag_items, {}, success=False)

def log_drag_operation(comp, drag_items, results, success):
    """Log drag operations for analysis"""
    drag_log = me.parent().fetch('drag_log', [])
    
    log_entry = {
        'timestamp': absTime.seconds,
        'source_component': comp.path,
        'drag_items': [str(item) for item in drag_items],
        'success': success,
        'results': results
    }
    
    drag_log.append(log_entry)
    
    # Keep only last 100 operations
    if len(drag_log) > 100:
        drag_log.pop(0)
    
    me.parent().store('drag_log', drag_log)
```

---

## Callback Best Practices

### Efficient Callback Patterns

```python
# Performance considerations for callbacks
def optimized_callback_pattern():
    """Template for efficient callback implementation"""
    
    # 1. Early exit for irrelevant events
    def onValueChange(par, prev):
        # Skip processing for tiny changes
        if abs(par.eval() - prev) < 0.001:
            return
        
        # Skip processing for specific parameters
        if par.name in ['tx', 'ty', 'tz'] and not monitor_position:
            return
        
        # Actual processing
        process_parameter_change(par, prev)
    
    # 2. Batch processing for multiple events
    def batch_callback_processing():
        callback_queue = me.parent().fetch('callback_queue', [])
        
        # Process callbacks in batches
        if len(callback_queue) > 10:
            process_callback_batch(callback_queue)
            me.parent().store('callback_queue', [])
    
    # 3. Debouncing for rapid events
    def debounced_text_callback(comp, value, prev_value):
        last_change_time = me.parent().fetch('last_text_change', 0)
        current_time = absTime.seconds
        
        # Only process if enough time has passed
        if current_time - last_change_time > 0.5:  # 500ms debounce
            process_text_change(comp, value, prev_value)
            me.parent().store('last_text_change', current_time)

def error_handling_in_callbacks():
    """Robust error handling for callbacks"""
    
    def safe_callback_wrapper(callback_func):
        """Wrapper to safely execute callbacks"""
        def wrapped_callback(*args, **kwargs):
            try:
                return callback_func(*args, **kwargs)
            except Exception as e:
                debug(f'Callback error in {callback_func.__name__}: {e}')
                # Optional: Log to file, send alert, etc.
                return None
        return wrapped_callback
    
    # Use wrapper for all callbacks
    @safe_callback_wrapper
    def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
        # Callback implementation
        process_osc_message(address, args)

def callback_state_management():
    """Manage state across callback invocations"""
    
    def initialize_callback_state():
        """Initialize persistent state for callbacks"""
        initial_state = {
            'message_count': 0,
            'last_message_time': 0,
            'active_connections': [],
            'error_count': 0
        }
        
        # Only initialize if not already present
        for key, value in initial_state.items():
            if not me.parent().fetch(key, None):
                me.parent().store(key, value)
    
    def update_callback_statistics(event_type):
        """Update statistics for callback monitoring"""
        stats = me.parent().fetch('callback_stats', {})
        
        if event_type not in stats:
            stats[event_type] = {'count': 0, 'last_time': 0}
        
        stats[event_type]['count'] += 1
        stats[event_type]['last_time'] = absTime.seconds
        
        me.parent().store('callback_stats', stats)
        
        # Periodic reporting
        total_events = sum(s['count'] for s in stats.values())
        if total_events % 100 == 0:
            debug(f'Callback statistics: {stats}')
```

---

## Event Coordination

### Multi-Callback Coordination

```python
class CallbackCoordinator:
    """Coordinate multiple callback systems"""
    
    def __init__(self):
        self.event_queue = []
        self.subscribers = {}
        self.processing = False
    
    def subscribe(self, event_type, callback_func):
        """Subscribe to specific event types"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback_func)
    
    def publish_event(self, event_type, event_data):
        """Publish event to all subscribers"""
        self.event_queue.append({
            'type': event_type,
            'data': event_data,
            'timestamp': absTime.seconds
        })
        
        # Process events if not already processing
        if not self.processing:
            self.process_event_queue()
    
    def process_event_queue(self):
        """Process all queued events"""
        self.processing = True
        
        try:
            while self.event_queue:
                event = self.event_queue.pop(0)
                self.dispatch_event(event)
        finally:
            self.processing = False
    
    def dispatch_event(self, event):
        """Dispatch event to appropriate subscribers"""
        event_type = event['type']
        event_data = event['data']
        
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    debug(f'Error in event callback: {e}')

# Global coordinator instance
if not hasattr(parent(), '_callback_coordinator'):
    parent().store('_callback_coordinator', CallbackCoordinator())

coordinator = parent().fetch('_callback_coordinator')

# Use in various callbacks:
def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """OSC callback that publishes events"""
    coordinator.publish_event('osc_message', {
        'address': address,
        'args': args,
        'peer': peer.address
    })

def onValueChange(par, prev):
    """Parameter callback that publishes events"""
    coordinator.publish_event('parameter_change', {
        'parameter': par.name,
        'value': par.eval(),
        'previous': prev,
        'operator': par.owner.path
    })

# Subscribe to coordinated events
def setup_event_subscriptions():
    """Set up event subscriptions for coordinated behavior"""
    
    def handle_osc_events(event_data):
        """Handle OSC events"""
        address = event_data['address']
        if address.startswith('/sync/'):
            handle_sync_message(event_data)
    
    def handle_parameter_events(event_data):
        """Handle parameter change events"""
        if event_data['parameter'] in ['tx', 'ty', 'tz']:
            handle_position_change(event_data)
    
    coordinator.subscribe('osc_message', handle_osc_events)
    coordinator.subscribe('parameter_change', handle_parameter_events)

# Initialize coordination system
setup_event_subscriptions()
```

---

## Cross-References

### Related Documentation

- **[EX_EXECUTE_DATS.md](./EX_EXECUTE_DATS.md)** - Execute DAT callback patterns
- **[EX_OSC_UDP.md](./EX_OSC_UDP.md)** - Network communication examples
- **[PY_CallbacksExtExtension.md](../PYTHON_/PY_CallbacksExtExtension.md)** - Callback system concepts

### Related Examples

- **[EX_EXTENSIONS.md](./EX_EXTENSIONS.md)** - Extension callback integration
- **[EX_UI.md](./EX_UI.md)** - UI component callback patterns
- **[EX_PANELS.md](./EX_PANELS.md)** - Panel component interactions

### Callback-Enabled Operators

- **OSC In DAT** - OSC message callbacks
- **TCP/IP In DAT** - TCP connection and data callbacks  
- **UDP In DAT** - UDP message callbacks
- **Text COMP** - Text editing and focus callbacks
- **List COMP** - Cell formatting and interaction callbacks
- **Panel COMPs** - Drag-and-drop callbacks

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/Callbacks/`

**Key Files**:

- `oscin1_callbacks.py` - OSC message handling
- `tcpip1_callbacks.py` - TCP/IP connection management  
- `text1_callbacks.py` - Text component interaction
- `list1_callbacks.py` - List component formatting
- `container1_dragdrop.py` - Drag-and-drop implementation
- `test_osc.txt` - OSC message sending examples

**Total Examples**: 19 files covering all major callback patterns for network communication, UI interaction, and event handling.

---

*These examples provide the foundation for creating responsive, interactive TouchDesigner systems that react efficiently to network data, user input, and component events.*
