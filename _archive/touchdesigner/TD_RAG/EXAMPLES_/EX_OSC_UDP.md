---
title: "OSC and UDP Communication Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "35-50 minutes"
user_personas: ["interactive_designer", "performance_artist", "technical_artist", "system_integrator"]
operators: ["oscoutDAT", "oscinDAT", "udpoutDAT", "udpinDAT", "serialDAT", "tcpipDAT"]
concepts: ["network_communication", "osc_protocol", "udp_protocol", "real_time_data", "binary_data", "message_routing"]
prerequisites: ["Python_fundamentals", "network_basics", "TouchDesigner_DATs"]
workflows: ["interactive_systems", "live_performance", "multi_device_coordination", "sensor_integration"]
keywords: ["osc", "udp", "network", "communication", "protocol", "real-time", "binary"]
tags: ["python", "network", "osc", "udp", "communication", "real-time", "examples"]
related_docs: ["CLASS_oscoutDAT_Class", "CLASS_oscinDAT_Class", "CLASS_udpoutDAT_Class", "EX_EXECUTE_DATS", "HARDWARE_Multiple_Monitors"]
example_count: 19
---

# TouchDesigner Python Examples: OSC and UDP Communication Protocols

## Overview

Comprehensive examples for Open Sound Control (OSC) and UDP network communication in TouchDesigner. These examples demonstrate real-time data transmission, protocol implementation, binary data handling, and network-based interaction patterns for live performance, installation, and inter-application communication.

**Source**: TouchDesigner Help > Python Examples > OSC_UDP  
**Example Count**: 19 files  
**Focus**: Network protocols, real-time communication, data serialization, peer management

## Quick Reference

### OSC Communication

- **[OSC Message Sending](#osc-message-sending)** - Structured message transmission with addresses and arguments
- **[OSC Data Types](#osc-data-types)** - Support for complex data structures and type conversion
- **[OSC Callbacks](#osc-callbacks)** - Receiving and parsing OSC messages
- **[OSC Address Routing](#osc-address-routing)** - Message routing and filtering patterns

### UDP Communication  

- **[UDP Text Transmission](#udp-text-transmission)** - String-based communication with termination control
- **[UDP Binary Data](#udp-binary-data)** - Binary protocols and struct-based data packing
- **[UDP Callbacks](#udp-callbacks)** - Raw data reception and processing
- **[UDP Broadcast Patterns](#udp-broadcast-patterns)** - Network discovery and broadcasting

### Advanced Patterns

- **[Protocol Design](#protocol-design)** - Creating custom network protocols
- **[Network Synchronization](#network-synchronization)** - Multi-device coordination
- **[Error Handling](#error-handling)** - Robust network communication
- **[Performance Optimization](#performance-optimization)** - Efficient data transmission

---

## OSC Message Sending

### Basic OSC Transmission

**Source File**: `test_sendOSC.txt`

**Key Concepts**: OSC addressing, mixed data types, message formatting

```python
# Send OSC messages with various data types
print('test_sendOSC')

# OSC supports complex mixed data types
vals = [1, 'apple', [1,2,3], b'ghi', (11,12), True, None, float("infinity")]
op('oscout1').sendOSC('/abc', vals)

def demonstrate_osc_data_types():
    """Demonstrate OSC support for various Python data types"""
    
    osc_out = op('oscout1')
    
    # Basic data types
    osc_out.sendOSC('/basic/int', [42])
    osc_out.sendOSC('/basic/float', [3.14159])
    osc_out.sendOSC('/basic/string', ['Hello TouchDesigner'])
    osc_out.sendOSC('/basic/bool', [True, False])
    
    # Collections
    osc_out.sendOSC('/collections/list', [[1, 2, 3, 4, 5]])
    osc_out.sendOSC('/collections/tuple', [(10, 20, 30)])
    osc_out.sendOSC('/collections/mixed', [1, 'text', 3.14, True])
    
    # Binary data
    binary_data = b'TouchDesigner binary data'
    osc_out.sendOSC('/binary/data', [binary_data])
    
    # Special values
    osc_out.sendOSC('/special/none', [None])
    osc_out.sendOSC('/special/infinity', [float('inf')])
    osc_out.sendOSC('/special/nan', [float('nan')])
    
    # Nested structures (OSC will flatten appropriately)
    complex_data = [
        'control_surface',
        {'x': 0.5, 'y': 0.3},  # Will be converted to OSC format
        [1, 2, 3, 4],          # Array data
        'end_marker'
    ]
    osc_out.sendOSC('/complex/data', complex_data)

def create_osc_control_system():
    """Create OSC-based control system for TouchDesigner"""
    
    osc_out = op('oscout1')
    
    # Control surface messages
    def send_control_value(control_id, value, control_type='slider'):
        """Send standardized control messages"""
        address = f'/control/{control_type}/{control_id}'
        timestamp = absTime.seconds
        osc_out.sendOSC(address, [value, timestamp])
    
    # Animation control
    def send_animation_frame(layer_id, x, y, rotation, scale):
        """Send animation data for specific layer"""
        address = f'/animation/layer/{layer_id}'
        osc_out.sendOSC(address, [x, y, rotation, scale, absTime.frame])
    
    # Audio analysis data
    def send_audio_analysis(fft_data, peak_level, beat_detected):
        """Send audio analysis results"""
        # Send peak level
        osc_out.sendOSC('/audio/peak', [peak_level])
        
        # Send beat detection
        if beat_detected:
            osc_out.sendOSC('/audio/beat', [absTime.seconds])
        
        # Send FFT data (limit to prevent large messages)
        simplified_fft = fft_data[::8]  # Every 8th sample
        osc_out.sendOSC('/audio/spectrum', simplified_fft)
    
    # System status messages
    def send_system_status():
        """Send TouchDesigner system status"""
        status_data = {
            'frame': absTime.frame,
            'fps': project.cookRate,
            'time': absTime.seconds,
            'performance': {
                'gpu_mem': 'TODO: get GPU memory usage',
                'cpu_usage': 'TODO: get CPU usage'
            }
        }
        
        # Send as separate messages for better parsing
        osc_out.sendOSC('/system/frame', [status_data['frame']])
        osc_out.sendOSC('/system/fps', [status_data['fps']])
        osc_out.sendOSC('/system/time', [status_data['time']])
    
    return send_control_value, send_animation_frame, send_audio_analysis, send_system_status

# Example usage patterns
def osc_messaging_patterns():
    """Common OSC messaging patterns"""
    
    osc_out = op('oscout1')
    
    # Pattern 1: Hierarchical addressing
    def send_hierarchical_data():
        """Use OSC address hierarchy for organization"""
        # Video controls
        osc_out.sendOSC('/video/layer/1/opacity', [0.8])
        osc_out.sendOSC('/video/layer/1/position', [0.5, 0.3])
        osc_out.sendOSC('/video/layer/2/opacity', [0.6])
        
        # Audio controls
        osc_out.sendOSC('/audio/master/volume', [0.7])
        osc_out.sendOSC('/audio/channel/1/gain', [0.5])
        osc_out.sendOSC('/audio/channel/1/pan', [0.2])
    
    # Pattern 2: Bundled data transmission
    def send_bundled_updates():
        """Send related data in logical groups"""
        current_time = absTime.seconds
        
        # Send all position data together
        positions = [
            ('object1', 0.1, 0.2, 0.0),
            ('object2', 0.5, 0.8, 0.3),
            ('object3', 0.9, 0.1, 0.7)
        ]
        
        for obj_name, x, y, z in positions:
            osc_out.sendOSC(f'/objects/{obj_name}/position', [x, y, z, current_time])
    
    # Pattern 3: Event-driven messaging
    def send_event_messages():
        """Send event-based OSC messages"""
        current_time = absTime.seconds
        
        # Trigger events
        osc_out.sendOSC('/events/trigger/start', [current_time])
        osc_out.sendOSC('/events/trigger/cue', [5, current_time])  # Cue number 5
        
        # State change events
        osc_out.sendOSC('/events/state/scene_change', ['scene_2', current_time])
        osc_out.sendOSC('/events/state/mode_change', ['performance', current_time])
    
    return send_hierarchical_data, send_bundled_updates, send_event_messages
```

---

## OSC Data Types

### Advanced Data Type Handling

```python
def advanced_osc_data_handling():
    """Advanced patterns for OSC data type handling"""
    
    osc_out = op('oscout1')
    
    # Color data
    def send_color_data(color_name, r, g, b, a=1.0):
        """Send color information via OSC"""
        # Method 1: As separate RGBA values
        osc_out.sendOSC(f'/color/{color_name}/rgba', [r, g, b, a])
        
        # Method 2: As hex string
        hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        osc_out.sendOSC(f'/color/{color_name}/hex', [hex_color])
        
        # Method 3: As HSV
        h, s, v = rgb_to_hsv(r, g, b)
        osc_out.sendOSC(f'/color/{color_name}/hsv', [h, s, v])
    
    # Matrix data
    def send_matrix_data(matrix_name, matrix_4x4):
        """Send 4x4 transformation matrix"""
        # Flatten matrix for transmission
        flat_matrix = [val for row in matrix_4x4 for val in row]
        osc_out.sendOSC(f'/matrix/{matrix_name}', flat_matrix)
        
        # Send as separate components for easier parsing
        osc_out.sendOSC(f'/matrix/{matrix_name}/translation', matrix_4x4[3][:3])
        
        # Send rotation as quaternion if available
        # quat = matrix_to_quaternion(matrix_4x4)
        # osc_out.sendOSC(f'/matrix/{matrix_name}/rotation', quat)
    
    # Time-based data
    def send_timeline_data():
        """Send time and animation data"""
        current_frame = absTime.frame
        current_time = absTime.seconds
        bpm = 120  # Example BPM
        
        # Time information
        osc_out.sendOSC('/timeline/frame', [current_frame])
        osc_out.sendOSC('/timeline/seconds', [current_time])
        osc_out.sendOSC('/timeline/bpm', [bpm])
        
        # Beat/bar information
        beats_per_bar = 4
        seconds_per_beat = 60.0 / bpm
        current_beat = int(current_time / seconds_per_beat) % beats_per_bar
        current_bar = int(current_time / (seconds_per_beat * beats_per_bar))
        
        osc_out.sendOSC('/timeline/beat', [current_beat, current_bar])
    
    # Sensor data aggregation
    def send_sensor_data(sensor_id, raw_data, processed_data):
        """Send both raw and processed sensor data"""
        timestamp = absTime.seconds
        
        # Raw sensor readings
        osc_out.sendOSC(f'/sensors/{sensor_id}/raw', raw_data + [timestamp])
        
        # Processed/calibrated data
        osc_out.sendOSC(f'/sensors/{sensor_id}/processed', processed_data + [timestamp])
        
        # Statistical data
        if len(processed_data) >= 3:  # Assuming x,y,z data
            magnitude = sum(x*x for x in processed_data[:3]) ** 0.5
            osc_out.sendOSC(f'/sensors/{sensor_id}/magnitude', [magnitude, timestamp])
    
    return send_color_data, send_matrix_data, send_timeline_data, send_sensor_data

def osc_data_validation():
    """Validation and sanitization for OSC data"""
    
    def validate_osc_data(data):
        """Validate data before OSC transmission"""
        validated_data = []
        
        for item in data:
            # Handle different data types
            if isinstance(item, (int, float)):
                # Check for NaN and infinity
                if item != item:  # NaN check
                    validated_data.append(0.0)
                elif item == float('inf') or item == float('-inf'):
                    validated_data.append(float('inf'))  # OSC supports infinity
                else:
                    validated_data.append(item)
            
            elif isinstance(item, str):
                # Ensure string is not too long
                max_length = 1024  # Reasonable OSC string limit
                if len(item) > max_length:
                    validated_data.append(item[:max_length])
                else:
                    validated_data.append(item)
            
            elif isinstance(item, bool):
                validated_data.append(item)
            
            elif isinstance(item, (list, tuple)):
                # Recursively validate nested data
                validated_data.extend(validate_osc_data(item))
            
            elif isinstance(item, bytes):
                validated_data.append(item)
            
            elif item is None:
                validated_data.append(None)  # OSC supports null
            
            else:
                # Convert unknown types to string
                validated_data.append(str(item))
        
        return validated_data
    
    def safe_osc_send(osc_out, address, data):
        """Safely send OSC data with validation"""
        try:
            # Validate address
            if not address.startswith('/'):
                address = '/' + address
            
            # Validate and clean data
            validated_data = validate_osc_data(data)
            
            # Send OSC message
            osc_out.sendOSC(address, validated_data)
            return True
        
        except Exception as e:
            debug(f'OSC send error: {e}')
            return False
    
    return validate_osc_data, safe_osc_send
```

---

## OSC Callbacks

### OSC Message Reception and Parsing

**Source File**: `oscin2_callbacks.py`

**Key Concepts**: OSC callback handling, address parsing, argument processing

```python
# OSC In callback - simplified version from examples
def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """Basic OSC message reception"""
    print(address)
    print('\t', args)

# Enhanced OSC callback system
def enhanced_osc_callback_system():
    """Comprehensive OSC callback handling system"""
    
    # Address-based routing system
    OSC_HANDLERS = {}
    
    def register_osc_handler(address_pattern, handler_func):
        """Register handler function for OSC address pattern"""
        OSC_HANDLERS[address_pattern] = handler_func
    
    def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
        """Enhanced OSC callback with routing"""
        
        # Log incoming message
        debug(f'OSC: {address} <- {peer.address}:{peer.port}')
        debug(f'  Args: {args}')
        debug(f'  Time: {timeStamp}')
        
        # Route message to appropriate handler
        route_osc_message(address, args, peer, timeStamp)
        
        # Store message for analysis
        store_osc_message(address, args, peer, timeStamp)
    
    def route_osc_message(address, args, peer, timestamp):
        """Route OSC message to registered handlers"""
        
        # Try exact match first
        if address in OSC_HANDLERS:
            try:
                OSC_HANDLERS[address](address, args, peer, timestamp)
                return
            except Exception as e:
                debug(f'OSC handler error for {address}: {e}')
        
        # Try pattern matching
        for pattern, handler in OSC_HANDLERS.items():
            if match_osc_pattern(pattern, address):
                try:
                    handler(address, args, peer, timestamp)
                    return
                except Exception as e:
                    debug(f'OSC pattern handler error for {pattern}: {e}')
        
        # No handler found
        debug(f'No OSC handler for: {address}')
    
    def match_osc_pattern(pattern, address):
        """Simple OSC address pattern matching"""
        # Convert OSC pattern to regex-like matching
        
        if '*' in pattern:
            # Wildcard matching
            pattern_parts = pattern.split('*')
            address_pos = 0
            
            for part in pattern_parts:
                if part:
                    pos = address.find(part, address_pos)
                    if pos == -1:
                        return False
                    address_pos = pos + len(part)
            return True
        
        elif pattern.endswith('/*'):
            # Prefix matching
            prefix = pattern[:-2]
            return address.startswith(prefix)
        
        return pattern == address
    
    def store_osc_message(address, args, peer, timestamp):
        """Store OSC message for analysis and debugging"""
        osc_log = me.parent().fetch('osc_message_log', [])
        
        message_record = {
            'address': address,
            'args': args,
            'peer_address': peer.address,
            'peer_port': peer.port,
            'timestamp': timestamp,
            'local_time': absTime.seconds
        }
        
        osc_log.append(message_record)
        
        # Keep only last 1000 messages
        if len(osc_log) > 1000:
            osc_log.pop(0)
        
        me.parent().store('osc_message_log', osc_log)
    
    # Example handlers
    def handle_control_message(address, args, peer, timestamp):
        """Handle control surface messages"""
        path_parts = address.split('/')
        if len(path_parts) >= 4:  # e.g., /control/slider/volume
            control_type = path_parts[2]
            control_id = path_parts[3]
            
            if len(args) > 0:
                value = float(args[0])
                
                # Update TouchDesigner parameters
                update_control_parameter(control_type, control_id, value)
    
    def handle_animation_message(address, args, peer, timestamp):
        """Handle animation control messages"""
        if len(args) >= 4:  # x, y, rotation, scale
            x, y, rotation, scale = args[:4]
            
            # Extract layer ID from address
            path_parts = address.split('/')
            if len(path_parts) >= 4:
                layer_id = path_parts[3]
                update_animation_layer(layer_id, x, y, rotation, scale)
    
    def handle_audio_message(address, args, peer, timestamp):
        """Handle audio analysis messages"""
        if 'peak' in address and len(args) > 0:
            peak_level = float(args[0])
            update_audio_visualizer('peak', peak_level)
        
        elif 'beat' in address:
            handle_beat_detection(timestamp)
        
        elif 'spectrum' in address and len(args) > 0:
            spectrum_data = [float(x) for x in args]
            update_spectrum_analyzer(spectrum_data)
    
    # Register handlers
    register_osc_handler('/control/*', handle_control_message)
    register_osc_handler('/animation/*', handle_animation_message) 
    register_osc_handler('/audio/*', handle_audio_message)
    
    return onReceiveOSC, register_osc_handler

def osc_message_analysis():
    """Analysis tools for OSC message streams"""
    
    def analyze_osc_traffic():
        """Analyze OSC message patterns"""
        osc_log = me.parent().fetch('osc_message_log', [])
        
        if not osc_log:
            return {'total_messages': 0}
        
        # Count messages by address
        address_counts = {}
        peer_counts = {}
        
        for msg in osc_log:
            address = msg['address']
            peer = f"{msg['peer_address']}:{msg['peer_port']}"
            
            address_counts[address] = address_counts.get(address, 0) + 1
            peer_counts[peer] = peer_counts.get(peer, 0) + 1
        
        # Calculate message rate
        if len(osc_log) > 1:
            time_span = osc_log[-1]['timestamp'] - osc_log[0]['timestamp']
            message_rate = len(osc_log) / time_span if time_span > 0 else 0
        else:
            message_rate = 0
        
        analysis = {
            'total_messages': len(osc_log),
            'unique_addresses': len(address_counts),
            'unique_peers': len(peer_counts),
            'message_rate': message_rate,
            'top_addresses': sorted(address_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'active_peers': list(peer_counts.keys())
        }
        
        debug(f'OSC Analysis: {analysis}')
        return analysis
    
    def detect_osc_patterns():
        """Detect patterns in OSC message timing"""
        osc_log = me.parent().fetch('osc_message_log', [])
        
        # Group messages by address
        address_groups = {}
        for msg in osc_log:
            address = msg['address']
            if address not in address_groups:
                address_groups[address] = []
            address_groups[address].append(msg['timestamp'])
        
        patterns = {}
        for address, timestamps in address_groups.items():
            if len(timestamps) > 2:
                # Calculate intervals
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                avg_interval = sum(intervals) / len(intervals)
                
                patterns[address] = {
                    'avg_interval': avg_interval,
                    'frequency_hz': 1.0 / avg_interval if avg_interval > 0 else 0,
                    'message_count': len(timestamps)
                }
        
        return patterns
    
    return analyze_osc_traffic, detect_osc_patterns
```

---

## UDP Text Transmission

### String-Based UDP Communication

**Source File**: `test_sendUDP.txt`

**Key Concepts**: Text transmission, termination control, message formatting

```python
# Send strings with different termination modes
print('test_sendUDP')

n = op('udpout1')

# Multiple strings in one packet, null terminated
n.send('apple', 'banana', 'carrot')

# Custom termination
n.send('def', append='\r\n')  # Carriage return and newline
n.send('ghi', append='')      # No termination
n.send('jkl')                 # Default null termination

def advanced_udp_text_patterns():
    """Advanced patterns for UDP text communication"""
    
    udp_out = op('udpout1')
    
    # Protocol 1: Line-based communication
    def send_line_protocol(command, data=None):
        """Send command using line-based protocol"""
        if data is not None:
            message = f"{command}:{data}"
        else:
            message = command
        
        # Send with newline termination for easy parsing
        udp_out.send(message, append='\n')
    
    # Protocol 2: JSON-based communication
    def send_json_message(message_type, payload):
        """Send structured data as JSON"""
        import json
        
        message_dict = {
            'type': message_type,
            'timestamp': absTime.seconds,
            'frame': absTime.frame,
            'payload': payload
        }
        
        json_string = json.dumps(message_dict)
        udp_out.send(json_string, append='\n')
    
    # Protocol 3: CSV-style data streaming
    def send_csv_data(data_rows):
        """Send data in CSV format"""
        import csv
        from io import StringIO
        
        # Create CSV string
        output = StringIO()
        writer = csv.writer(output)
        
        # Add timestamp column
        timestamped_rows = []
        current_time = absTime.seconds
        
        for row in data_rows:
            timestamped_rows.append([current_time] + list(row))
        
        writer.writerows(timestamped_rows)
        csv_string = output.getvalue()
        
        # Send each line separately
        for line in csv_string.strip().split('\n'):
            udp_out.send(line, append='\n')
    
    # Protocol 4: Key-value pairs
    def send_keyvalue_data(data_dict):
        """Send data as key=value pairs"""
        for key, value in data_dict.items():
            message = f"{key}={value}"
            udp_out.send(message, append='\n')
        
        # Send end marker
        udp_out.send("END", append='\n')
    
    # Example usage
    def demonstrate_text_protocols():
        """Demonstrate different text-based UDP protocols"""
        
        # Line protocol
        send_line_protocol("SET_VOLUME", "0.8")
        send_line_protocol("GET_STATUS")
        send_line_protocol("RESET")
        
        # JSON protocol
        send_json_message("sensor_data", {
            "temperature": 22.5,
            "humidity": 45.2,
            "pressure": 1013.25
        })
        
        send_json_message("user_input", {
            "mouse_x": 0.5,
            "mouse_y": 0.3,
            "clicked": True
        })
        
        # CSV protocol
        sensor_readings = [
            [22.1, 45.0, 1013.1],
            [22.3, 45.1, 1013.2],
            [22.5, 45.2, 1013.3]
        ]
        send_csv_data(sensor_readings)
        
        # Key-value protocol
        system_status = {
            "fps": project.cookRate,
            "frame": absTime.frame,
            "memory_usage": "TODO",
            "cpu_usage": "TODO"
        }
        send_keyvalue_data(system_status)
    
    return send_line_protocol, send_json_message, send_csv_data, send_keyvalue_data

def udp_text_reliability():
    """Patterns for reliable UDP text communication"""
    
    udp_out = op('udpout1')
    
    def send_with_acknowledgment(message_id, message):
        """Send message with acknowledgment request"""
        # Add message ID and ACK request
        full_message = f"ID:{message_id}:ACK:{message}"
        udp_out.send(full_message, append='\n')
        
        # Store for potential resend
        pending_messages = me.parent().fetch('pending_udp_messages', {})
        pending_messages[message_id] = {
            'message': full_message,
            'send_time': absTime.seconds,
            'retry_count': 0
        }
        me.parent().store('pending_udp_messages', pending_messages)
    
    def send_with_sequence_number(message):
        """Send message with sequence number"""
        sequence_number = me.parent().fetch('udp_sequence', 0) + 1
        me.parent().store('udp_sequence', sequence_number)
        
        sequenced_message = f"SEQ:{sequence_number}:{message}"
        udp_out.send(sequenced_message, append='\n')
        
        return sequence_number
    
    def send_heartbeat():
        """Send periodic heartbeat message"""
        heartbeat_msg = f"HEARTBEAT:{absTime.seconds}"
        udp_out.send(heartbeat_msg, append='\n')
    
    def resend_pending_messages():
        """Resend unacknowledged messages"""
        pending_messages = me.parent().fetch('pending_udp_messages', {})
        current_time = absTime.seconds
        timeout = 5.0  # 5 second timeout
        
        messages_to_remove = []
        
        for msg_id, msg_data in pending_messages.items():
            if current_time - msg_data['send_time'] > timeout:
                if msg_data['retry_count'] < 3:  # Max 3 retries
                    # Resend message
                    udp_out.send(msg_data['message'], append='\n')
                    msg_data['send_time'] = current_time
                    msg_data['retry_count'] += 1
                else:
                    # Give up after 3 retries
                    debug(f"UDP message {msg_id} failed after 3 retries")
                    messages_to_remove.append(msg_id)
        
        # Remove failed messages
        for msg_id in messages_to_remove:
            del pending_messages[msg_id]
        
        me.parent().store('pending_udp_messages', pending_messages)
    
    return send_with_acknowledgment, send_with_sequence_number, send_heartbeat, resend_pending_messages
```

---

## UDP Binary Data

### Binary Protocol Implementation  

**Source File**: `test_sendBytes.txt`

**Key Concepts**: Binary data transmission, struct packing, protocol design

```python
# Binary UDP communication examples
print('test_sendBytes')

n = op('udpout2')

# Send bytes in different formats
n.sendBytes('abc')        # String as bytes
n.sendBytes(65, 66)       # Decimal values
n.sendBytes(0x35)         # Hexadecimal value

# Using struct module for binary protocols
from struct import *
a = pack('hhl', 1, 2, 3)  # Pack two shorts and a long
print('a is ', a)
n.sendBytes(a)

def advanced_binary_protocols():
    """Advanced binary protocol implementation"""
    
    udp_out = op('udpout2')
    
    # Protocol 1: Fixed-length binary messages
    def create_sensor_message(sensor_id, x, y, z, timestamp):
        """Create binary sensor data message"""
        # Message format: [header][sensor_id][x][y][z][timestamp][checksum]
        # Header: 2 bytes (0xAA, 0xBB)
        # Sensor ID: 2 bytes (uint16)  
        # X, Y, Z: 4 bytes each (float32)
        # Timestamp: 8 bytes (double)
        # Checksum: 2 bytes (uint16)
        
        import struct
        
        # Pack main data
        data = struct.pack('<HHfffQ', 
                          0xAABB,        # Header
                          sensor_id,     # Sensor ID
                          x, y, z,       # Position data
                          int(timestamp * 1000))  # Timestamp in ms
        
        # Calculate simple checksum
        checksum = sum(data) % 65536
        
        # Pack with checksum
        full_message = data + struct.pack('<H', checksum)
        
        return full_message
    
    def send_sensor_data(sensor_id, x, y, z):
        """Send binary sensor data"""
        message = create_sensor_message(sensor_id, x, y, z, absTime.seconds)
        udp_out.sendBytes(message)
    
    # Protocol 2: Variable-length binary messages
    def create_variable_message(message_type, data):
        """Create variable-length binary message"""
        import struct
        
        # Message format: [length][type][data]
        # Length: 4 bytes (uint32)
        # Type: 2 bytes (uint16)
        # Data: variable length
        
        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        length = len(data_bytes) + 6  # Include length and type fields
        
        message = struct.pack('<IH', length, message_type) + data_bytes
        return message
    
    def send_variable_message(message_type, data):
        """Send variable-length message"""
        message = create_variable_message(message_type, data)
        udp_out.sendBytes(message)
    
    # Protocol 3: Image data transmission
    def send_image_data(width, height, pixel_data, compression=None):
        """Send image data over UDP"""
        import struct
        
        # Image header: [magic][width][height][format][compression][data_length]
        # Magic: 4 bytes (0x494D4720 = "IMG ")  
        # Width/Height: 4 bytes each (uint32)
        # Format: 2 bytes (uint16) - 0=RGB, 1=RGBA, 2=GRAY
        # Compression: 2 bytes (uint16) - 0=None, 1=ZIP, 2=JPEG
        # Data length: 4 bytes (uint32)
        
        magic = 0x494D4720
        format_type = 0  # Assume RGB
        compression_type = compression or 0
        
        # Compress data if requested
        if compression == 1:  # ZIP compression
            import zlib
            pixel_data = zlib.compress(pixel_data)
        
        header = struct.pack('<IIIHHII', 
                           magic, width, height, 
                           format_type, compression_type, 
                           len(pixel_data))
        
        # Send header first
        udp_out.sendBytes(header)
        
        # Send image data in chunks (UDP has size limits)
        chunk_size = 1024
        for i in range(0, len(pixel_data), chunk_size):
            chunk = pixel_data[i:i+chunk_size]
            udp_out.sendBytes(chunk)
    
    # Protocol 4: Multi-part messages
    def send_multipart_message(data, part_size=1024):
        """Send large data as multiple UDP packets"""
        import struct
        
        total_parts = (len(data) + part_size - 1) // part_size
        message_id = int(absTime.seconds * 1000) % 65536  # Unique message ID
        
        for part_num in range(total_parts):
            start = part_num * part_size
            end = min(start + part_size, len(data))
            part_data = data[start:end]
            
            # Header: [message_id][part_num][total_parts][part_data]
            header = struct.pack('<HHH', message_id, part_num, total_parts)
            packet = header + part_data
            
            udp_out.sendBytes(packet)
            
            # Small delay between parts to avoid overwhelming receiver
            # In TouchDesigner, you might use run() with delay instead
            # run(f"continue_multipart_send({part_num + 1})", delayFrames=1)
    
    return send_sensor_data, send_variable_message, send_image_data, send_multipart_message

def binary_data_utilities():
    """Utilities for working with binary data"""
    
    def bytes_to_hex_string(data):
        """Convert bytes to hex string for debugging"""
        return ' '.join(f'{b:02x}' for b in data)
    
    def validate_binary_message(data, expected_format):
        """Validate binary message format"""
        import struct
        
        try:
            # Unpack according to expected format
            unpacked = struct.unpack(expected_format, data)
            return True, unpacked
        except struct.error as e:
            return False, str(e)
    
    def create_crc_checksum(data):
        """Create CRC checksum for binary data"""
        # Simple CRC-16 implementation
        crc = 0xFFFF
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        
        return crc
    
    def encode_string_for_binary(text, max_length=None):
        """Encode string for binary protocol"""
        encoded = text.encode('utf-8')
        
        if max_length and len(encoded) > max_length:
            encoded = encoded[:max_length]
        
        # Null-terminate if needed
        return encoded + b'\x00'
    
    return bytes_to_hex_string, validate_binary_message, create_crc_checksum, encode_string_for_binary
```

---

## UDP Callbacks

### UDP Data Reception

**Source File**: `udpin3_callbacks.py`

**Key Concepts**: Raw UDP data handling, message parsing, connection management

```python
# Basic UDP callback from examples
def onReceive(dat, rowIndex, message, bytes, peer):
    """Basic UDP message reception"""
    print(message)

def enhanced_udp_callback_system():
    """Enhanced UDP callback handling with protocol support"""
    
    def onReceive(dat, rowIndex, message, bytes, peer):
        """Enhanced UDP callback with protocol detection"""
        
        # Log incoming data
        debug(f'UDP from {peer.address}:{peer.port}: {len(bytes)} bytes')
        
        # Attempt to detect protocol and parse accordingly
        protocol_type = detect_udp_protocol(bytes)
        
        if protocol_type == 'text':
            handle_text_message(message, peer)
        elif protocol_type == 'json':
            handle_json_message(message, peer)
        elif protocol_type == 'binary':
            handle_binary_message(bytes, peer)
        elif protocol_type == 'osc':
            # Some OSC implementations might use UDP directly
            handle_osc_like_message(bytes, peer)
        else:
            handle_unknown_message(message, bytes, peer)
    
    def detect_udp_protocol(data):
        """Detect the protocol type of UDP data"""
        
        # Try to decode as text
        try:
            text = data.decode('utf-8')
            
            # Check for JSON
            if text.strip().startswith(('{', '[')):
                return 'json'
            
            # Check for common text patterns
            if all(ord(c) < 128 for c in text):
                return 'text'
        
        except UnicodeDecodeError:
            pass
        
        # Check for common binary patterns
        if len(data) >= 4:
            # Check for common magic bytes
            magic = data[:4]
            if magic == b'IMG ' or magic == b'\xAA\xBB\xCC\xDD':
                return 'binary'
        
        # Default to binary
        return 'binary'
    
    def handle_text_message(message, peer):
        """Handle text-based UDP messages"""
        lines = message.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                # Key-value pair
                key, value = line.split(':', 1)
                process_keyvalue_command(key.strip(), value.strip(), peer)
            
            elif '=' in line:
                # Assignment format
                key, value = line.split('=', 1)
                process_assignment_command(key.strip(), value.strip(), peer)
            
            else:
                # Simple command
                process_simple_command(line.strip(), peer)
    
    def handle_json_message(message, peer):
        """Handle JSON UDP messages"""
        import json
        
        try:
            data = json.loads(message)
            
            # Extract message type
            msg_type = data.get('type', 'unknown')
            payload = data.get('payload', {})
            timestamp = data.get('timestamp', absTime.seconds)
            
            # Route based on type
            if msg_type == 'sensor_data':
                process_sensor_data(payload, peer, timestamp)
            elif msg_type == 'user_input':
                process_user_input(payload, peer, timestamp)
            elif msg_type == 'system_status':
                process_system_status(payload, peer, timestamp)
            else:
                debug(f'Unknown JSON message type: {msg_type}')
        
        except json.JSONDecodeError as e:
            debug(f'JSON decode error: {e}')
    
    def handle_binary_message(data, peer):
        """Handle binary UDP messages"""
        
        if len(data) < 4:
            debug('Binary message too short')
            return
        
        # Check for sensor data format
        if len(data) >= 26:  # Size of sensor message
            try:
                import struct
                unpacked = struct.unpack('<HHfffQH', data[:26])
                
                header, sensor_id, x, y, z, timestamp_ms, checksum = unpacked
                
                if header == 0xAABB:
                    # Validate checksum
                    data_without_checksum = data[:-2]
                    calculated_checksum = sum(data_without_checksum) % 65536
                    
                    if calculated_checksum == checksum:
                        process_binary_sensor_data(sensor_id, x, y, z, timestamp_ms/1000.0, peer)
                    else:
                        debug('Binary sensor data checksum mismatch')
                    return
            except struct.error:
                pass
        
        # Check for image data
        if len(data) >= 20:  # Size of image header
            try:
                import struct
                magic, width, height, format_type, compression, data_length = struct.unpack('<IIIHHII', data[:20])
                
                if magic == 0x494D4720:  # "IMG " magic
                    process_image_data(width, height, format_type, compression, data[20:], peer)
                    return
            except struct.error:
                pass
        
        # Unknown binary format
        debug(f'Unknown binary format from {peer.address}: {len(data)} bytes')
    
    def process_sensor_data(payload, peer, timestamp):
        """Process sensor data from JSON message"""
        sensor_values = ['temperature', 'humidity', 'pressure']
        
        for sensor in sensor_values:
            if sensor in payload:
                value = float(payload[sensor])
                update_sensor_display(sensor, value, peer.address)
    
    def process_binary_sensor_data(sensor_id, x, y, z, timestamp, peer):
        """Process binary sensor data"""
        debug(f'Sensor {sensor_id}: ({x:.2f}, {y:.2f}, {z:.2f}) from {peer.address}')
        
        # Update TouchDesigner visualization
        update_3d_sensor_position(sensor_id, x, y, z)
    
    return onReceive

def udp_connection_management():
    """Manage UDP connections and peer tracking"""
    
    def track_udp_peers():
        """Track active UDP peers"""
        udp_peers = me.parent().fetch('udp_peers', {})
        current_time = absTime.seconds
        
        # Clean up old peers (inactive for more than 30 seconds)
        inactive_timeout = 30.0
        peers_to_remove = []
        
        for peer_addr, peer_data in udp_peers.items():
            if current_time - peer_data['last_seen'] > inactive_timeout:
                peers_to_remove.append(peer_addr)
        
        for peer_addr in peers_to_remove:
            del udp_peers[peer_addr]
            debug(f'Removed inactive UDP peer: {peer_addr}')
        
        me.parent().store('udp_peers', udp_peers)
        return udp_peers
    
    def update_peer_activity(peer):
        """Update peer activity timestamp"""
        udp_peers = me.parent().fetch('udp_peers', {})
        peer_key = f"{peer.address}:{peer.port}"
        
        if peer_key not in udp_peers:
            udp_peers[peer_key] = {
                'first_seen': absTime.seconds,
                'message_count': 0,
                'peer_address': peer.address,
                'peer_port': peer.port
            }
            debug(f'New UDP peer detected: {peer_key}')
        
        udp_peers[peer_key]['last_seen'] = absTime.seconds
        udp_peers[peer_key]['message_count'] += 1
        
        me.parent().store('udp_peers', udp_peers)
    
    def get_peer_statistics():
        """Get statistics about UDP peers"""
        udp_peers = me.parent().fetch('udp_peers', {})
        
        stats = {
            'total_peers': len(udp_peers),
            'active_peers': [],
            'total_messages': sum(p['message_count'] for p in udp_peers.values()),
            'peer_details': udp_peers
        }
        
        current_time = absTime.seconds
        recent_timeout = 10.0  # Consider peer active if seen within 10 seconds
        
        for peer_addr, peer_data in udp_peers.items():
            if current_time - peer_data['last_seen'] <= recent_timeout:
                stats['active_peers'].append(peer_addr)
        
        return stats
    
    return track_udp_peers, update_peer_activity, get_peer_statistics
```

---

## Protocol Design

### Creating Custom Network Protocols

```python
def create_custom_protocol():
    """Framework for creating custom UDP/OSC protocols"""
    
    class TouchDesignerProtocol:
        """Custom protocol for TouchDesigner communication"""
        
        def __init__(self, protocol_version=1):
            self.version = protocol_version
            self.message_types = {
                'HANDSHAKE': 0x01,
                'DATA': 0x02,
                'COMMAND': 0x03,
                'STATUS': 0x04,
                'ERROR': 0x05
            }
        
        def create_handshake_message(self, client_id, capabilities):
            """Create handshake message"""
            import struct
            import json
            
            capabilities_json = json.dumps(capabilities).encode('utf-8')
            
            # Header: version, message_type, client_id, data_length
            header = struct.pack('<BBHH', self.version, self.message_types['HANDSHAKE'], 
                               client_id, len(capabilities_json))
            
            return header + capabilities_json
        
        def create_data_message(self, data_type, payload):
            """Create data message"""
            import struct
            
            if isinstance(payload, str):
                payload_bytes = payload.encode('utf-8')
            else:
                payload_bytes = payload
            
            header = struct.pack('<BBHH', self.version, self.message_types['DATA'],
                               data_type, len(payload_bytes))
            
            return header + payload_bytes
        
        def parse_message(self, message_bytes):
            """Parse received message"""
            import struct
            
            if len(message_bytes) < 6:  # Minimum header size
                return None
            
            # Parse header
            version, msg_type, data_id, data_length = struct.unpack('<BBHH', message_bytes[:6])
            
            if version != self.version:
                return {'error': 'Version mismatch'}
            
            # Extract payload
            payload = message_bytes[6:6+data_length]
            
            # Find message type name
            type_name = None
            for name, code in self.message_types.items():
                if code == msg_type:
                    type_name = name
                    break
            
            return {
                'version': version,
                'type': type_name,
                'type_code': msg_type,
                'data_id': data_id,
                'payload': payload
            }
    
    # Example usage
    def demonstrate_custom_protocol():
        """Demonstrate custom protocol usage"""
        
        protocol = TouchDesignerProtocol()
        udp_out = op('udpout1')
        
        # Send handshake
        capabilities = {
            'video_outputs': 4,
            'audio_inputs': 8,
            'supports_osc': True,
            'max_resolution': '4K'
        }
        
        handshake = protocol.create_handshake_message(12345, capabilities)
        udp_out.sendBytes(handshake)
        
        # Send data message
        sensor_data = {
            'accelerometer': [0.1, -0.3, 9.8],
            'gyroscope': [0.02, -0.01, 0.05],
            'timestamp': absTime.seconds
        }
        
        import json
        data_msg = protocol.create_data_message(100, json.dumps(sensor_data))
        udp_out.sendBytes(data_msg)
    
    return TouchDesignerProtocol, demonstrate_custom_protocol

def protocol_discovery_system():
    """Automatic protocol discovery and negotiation"""
    
    def send_discovery_broadcast():
        """Send discovery broadcast to find other TouchDesigner instances"""
        
        udp_out = op('udpout1')
        
        discovery_message = {
            'type': 'DISCOVERY',
            'sender_id': project.name,
            'timestamp': absTime.seconds,
            'capabilities': {
                'protocol_version': 1,
                'supported_formats': ['OSC', 'UDP', 'JSON'],
                'device_type': 'TouchDesigner',
                'services': ['visualization', 'audio_analysis', 'control']
            }
        }
        
        import json
        message = json.dumps(discovery_message)
        
        # Broadcast on standard discovery port
        # Note: This would need proper broadcast setup
        udp_out.send(message, append='\n')
    
    def handle_discovery_response(response_data, peer):
        """Handle discovery response from other devices"""
        
        try:
            import json
            data = json.loads(response_data)
            
            if data.get('type') == 'DISCOVERY':
                # Register discovered device
                discovered_devices = me.parent().fetch('discovered_devices', {})
                
                device_key = f"{peer.address}:{peer.port}"
                discovered_devices[device_key] = {
                    'sender_id': data.get('sender_id'),
                    'capabilities': data.get('capabilities', {}),
                    'last_seen': absTime.seconds,
                    'peer_info': {'address': peer.address, 'port': peer.port}
                }
                
                me.parent().store('discovered_devices', discovered_devices)
                debug(f'Discovered device: {data.get("sender_id")} at {device_key}')
                
                # Send response
                send_discovery_response(peer)
        
        except json.JSONDecodeError:
            pass
    
    def send_discovery_response(peer):
        """Send discovery response to requesting peer"""
        
        response = {
            'type': 'DISCOVERY_RESPONSE',
            'sender_id': project.name,
            'timestamp': absTime.seconds,
            'responding_to': f"{peer.address}:{peer.port}",
            'capabilities': {
                'protocol_version': 1,
                'supported_formats': ['OSC', 'UDP', 'JSON'],
                'device_type': 'TouchDesigner',
                'services': ['visualization', 'audio_analysis']
            }
        }
        
        import json
        message = json.dumps(response)
        
        # Send directly to requesting peer
        udp_out = op('udpout1')
        udp_out.send(message, append='\n')
    
    return send_discovery_broadcast, handle_discovery_response, send_discovery_response
```

---

## Cross-References

### Related Documentation

- **[EX_CALLBACKS.md](./EX_CALLBACKS.md)** - Network callback patterns
- **[PY_CallbacksExtExtension.md](../PYTHON_/PY_CallbacksExtExtension.md)** - Callback system concepts  
- **[REF_Network_Communication.md](../REFERENCE_/REF_Network_Communication.md)** - Network configuration

### Related Examples

- **[EX_EXECUTE_DATS.md](./EX_EXECUTE_DATS.md)** - Execute DAT network monitoring
- **[EX_MODULES.md](./EX_MODULES.md)** - Network utility modules
- **[EX_EXTENSIONS.md](./EX_EXTENSIONS.md)** - Network extension development

### Network Operators

- **OSC In DAT** - OSC message reception with callbacks
- **OSC Out DAT** - OSC message transmission
- **UDP In DAT** - UDP data reception with callbacks  
- **UDP Out DAT** - UDP data transmission
- **TCP/IP In/Out DAT** - TCP connection-based communication

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/OSC_UDP/`

**Key Files**:

- `test_sendOSC.txt` - OSC message transmission patterns
- `test_sendUDP.txt` - UDP text communication  
- `test_sendBytes.txt` - Binary UDP protocols
- `oscin2_callbacks.py` - OSC reception handling
- `udpin3_callbacks.py` - UDP data callbacks

**Total Examples**: 19 files covering all aspects of network communication from basic message sending to advanced protocol design and peer management.

---

*These examples provide the foundation for creating networked TouchDesigner systems that can communicate with other applications, devices, and TouchDesigner instances in real-time for live performance, installations, and collaborative workflows.*
