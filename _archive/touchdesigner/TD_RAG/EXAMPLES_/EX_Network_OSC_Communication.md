---
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: 50-70 minutes
operators:
- OSC_In_DAT
- OSC_Out_DAT
- TCP_IP_DAT
- UDP_In_DAT
- UDP_Out_DAT
- Web_Client_DAT
- Web_Server_DAT
- WebSocket_DAT
- Serial_DAT
- MQTT_Client_DAT
- Execute_DAT
- Convert_DAT
- Text_DAT
- Table_DAT
concepts:
- network_communication
- osc_protocol
- tcp_ip_networking
- udp_communication
- websockets
- serial_communication
- mqtt_messaging
- protocol_handling
- real_time_networking
- device_integration
prerequisites:
- TouchDesigner_fundamentals
- Basic_networking_concepts
- Python_scripting
workflows:
- device_integration
- remote_control_systems
- multi_machine_setups
- iot_integration
- live_performance_networking
keywords:
- osc
- network communication
- tcp ip
- udp
- websockets
- serial
- mqtt
- remote control
- device integration
- protocol
- real-time networking
tags:
- network
- communication
- osc
- tcp
- udp
- websockets
- serial
- mqtt
- integration
- real-time
relationships:
  EX_Advanced_Python_API_Patterns: strong
  EX_Audio_Reactive_Systems: medium
  PY_Debugging_Error_Handling: medium
  REF_Troubleshooting_Guide: medium
  PERF_Optimize: medium
related_docs:
- EX_Advanced_Python_API_Patterns
- EX_Audio_Reactive_Systems
- PY_Debugging_Error_Handling
- REF_Troubleshooting_Guide
- PERF_Optimize
hierarchy:
  secondary: advanced_examples
  tertiary: network_communication
question_patterns:
- Network communication in TouchDesigner?
- OSC integration examples?
- How to connect TouchDesigner to external devices?
- Multi-machine TouchDesigner setups?
common_use_cases:
- device_integration
- remote_control_systems
- multi_machine_setups
- iot_integration
---

# Network and OSC Communication in TouchDesigner

## 🎯 Quick Reference

**Purpose**: Advanced network communication patterns for device integration and remote control
**Difficulty**: Advanced
**Time to read**: 50-70 minutes
**Use for**: device_integration, remote_control_systems, multi_machine_setups

## 🔗 Learning Path

**Prerequisites**: [TouchDesigner Fundamentals] → [Basic Networking Concepts] → [Python Scripting]
**This document**: EXAMPLES advanced network communication
**Next steps**: Production deployment and system integration

## OSC Communication Systems

### Comprehensive OSC Manager

```python
class OSCManager:
    """Advanced OSC communication management system"""
    
    def __init__(self):
        self.osc_inputs = {}
        self.osc_outputs = {}
        self.message_handlers = {}
        self.address_mappings = {}
        self.connection_monitor = {}
        self.setup_osc_system()
    
    def setup_osc_system(self):
        """Initialize OSC communication infrastructure"""
        # Create OSC container
        parent_comp = op('/project1') or root
        self.osc_container = parent_comp.create(baseCOMP, 'osc_system')
        
        # Create message history for debugging
        self.message_history = []
        
        debug("OSC Manager initialized")
    
    def create_osc_input(self, input_name, config):
        """Create OSC input with comprehensive error handling"""
        try:
            container = self.osc_container
            
            # Create OSC In DAT
            osc_in = container.create(oscinDAT, f"{input_name}_in")
            
            # Configure OSC input parameters
            osc_in.par.port = config.get('port', 9000)
            osc_in.par.active = True
            
            # Create execute DAT for message handling
            execute_dat = container.create(executeDAT, f"{input_name}_execute")
            execute_dat.par.active = True
            
            # Set up callback script
            callback_script = self.generate_osc_callback_script(input_name)
            execute_dat.text = callback_script
            
            # Create message parser
            parser_dat = container.create(textDAT, f"{input_name}_parser")
            
            # Store OSC input configuration
            input_config = {
                'osc_in': osc_in,
                'execute_dat': execute_dat,
                'parser_dat': parser_dat,
                'config': config,
                'active': True,
                'message_count': 0,
                'last_message_time': 0
            }
            
            self.osc_inputs[input_name] = input_config
            
            # Set up connection monitoring
            self.setup_connection_monitoring(input_name, 'input')
            
            debug(f"Created OSC input: {input_name} on port {config.get('port', 9000)}")
            return input_config
            
        except Exception as e:
            debug(f"Error creating OSC input {input_name}: {str(e)}")
            return None
    
    def create_osc_output(self, output_name, config):
        """Create OSC output with connection management"""
        try:
            container = self.osc_container
            
            # Create OSC Out DAT
            osc_out = container.create(oscoutDAT, f"{output_name}_out")
            
            # Configure OSC output parameters
            osc_out.par.networkaddress = config.get('address', '127.0.0.1')
            osc_out.par.networkport = config.get('port', 9001)
            osc_out.par.active = True
            
            # Create message queue for reliable sending
            queue_dat = container.create(textDAT, f"{output_name}_queue")
            
            # Store OSC output configuration
            output_config = {
                'osc_out': osc_out,
                'queue_dat': queue_dat,
                'config': config,
                'active': True,
                'message_count': 0,
                'connection_status': 'unknown'
            }
            
            self.osc_outputs[output_name] = output_config
            
            # Set up connection monitoring
            self.setup_connection_monitoring(output_name, 'output')
            
            debug(f"Created OSC output: {output_name} to {config.get('address')}:{config.get('port')}")
            return output_config
            
        except Exception as e:
            debug(f"Error creating OSC output {output_name}: {str(e)}")
            return None
    
    def generate_osc_callback_script(self, input_name):
        """Generate callback script for OSC message handling"""
        script = f'''
# OSC callback script for {input_name}
import json

def onReceive(dat, rowIndex, message, address, args, peer):
    """Handle incoming OSC messages"""
    try:
        # Log message for debugging
        message_data = {{
            'timestamp': absTime.seconds,
            'address': address,
            'args': args,
            'peer': str(peer),
            'input_name': '{input_name}'
        }}
        
        # Call global OSC manager handler
        if hasattr(mod, 'osc_manager'):
            mod.osc_manager.handle_osc_message('{input_name}', message_data)
        else:
            debug(f"OSC message received on {input_name}: {{address}} {{args}}")
            
    except Exception as e:
        debug(f"Error in OSC callback for {input_name}: {{str(e)}}")

def onConnect(dat, peer):
    """Handle OSC connection events"""
    try:
        debug(f"OSC client connected to {input_name}: {{str(peer)}}")
        if hasattr(mod, 'osc_manager'):
            mod.osc_manager.handle_connection_event('{input_name}', 'connect', peer)
    except Exception as e:
        debug(f"Error in OSC connect callback: {{str(e)}}")

def onDisconnect(dat, peer):
    """Handle OSC disconnection events"""
    try:
        debug(f"OSC client disconnected from {input_name}: {{str(peer)}}")
        if hasattr(mod, 'osc_manager'):
            mod.osc_manager.handle_connection_event('{input_name}', 'disconnect', peer)
    except Exception as e:
        debug(f"Error in OSC disconnect callback: {{str(e)}}")
'''
        return script
    
    def handle_osc_message(self, input_name, message_data):
        """Handle incoming OSC message with routing and processing"""
        try:
            # Update message statistics
            if input_name in self.osc_inputs:
                self.osc_inputs[input_name]['message_count'] += 1
                self.osc_inputs[input_name]['last_message_time'] = absTime.seconds
            
            # Add to message history
            self.message_history.append(message_data)
            if len(self.message_history) > 1000:
                self.message_history = self.message_history[-500:]  # Keep last 500
            
            address = message_data['address']
            args = message_data['args']
            
            # Route message to registered handlers
            if address in self.message_handlers:
                handler = self.message_handlers[address]
                handler(message_data)
            else:
                # Try pattern matching for handlers
                self.route_message_by_pattern(address, message_data)
            
            # Apply address mappings if configured
            if address in self.address_mappings:
                mapping = self.address_mappings[address]
                self.apply_address_mapping(mapping, args)
                
        except Exception as e:
            debug(f"Error handling OSC message: {str(e)}")
    
    def route_message_by_pattern(self, address, message_data):
        """Route messages using pattern matching"""
        for pattern, handler in self.message_handlers.items():
            if '*' in pattern or '?' in pattern:
                # Simple pattern matching
                if self.match_osc_pattern(pattern, address):
                    handler(message_data)
                    return
    
    def match_osc_pattern(self, pattern, address):
        """Simple OSC address pattern matching"""
        import re
        # Convert OSC pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return re.match(f"^{regex_pattern}$", address) is not None
    
    def register_message_handler(self, address_pattern, handler_func):
        """Register handler for OSC address pattern"""
        self.message_handlers[address_pattern] = handler_func
        debug(f"Registered OSC handler for pattern: {address_pattern}")
    
    def register_address_mapping(self, osc_address, target_config):
        """Register direct OSC address to parameter mapping"""
        self.address_mappings[osc_address] = target_config
        debug(f"Registered address mapping: {osc_address}")
    
    def apply_address_mapping(self, mapping, args):
        """Apply OSC message directly to TouchDesigner parameter"""
        try:
            target_op_path = mapping['operator']
            param_name = mapping['parameter']
            
            target_op = op(target_op_path)
            if not target_op or not hasattr(target_op.par, param_name):
                return
            
            # Get value from OSC args
            if len(args) == 0:
                return
            
            osc_value = args[0]  # Use first argument
            
            # Apply scaling and offset if configured
            final_value = osc_value
            if 'scale' in mapping:
                final_value *= mapping['scale']
            if 'offset' in mapping:
                final_value += mapping['offset']
            
            # Apply range limiting
            if 'min_value' in mapping:
                final_value = max(mapping['min_value'], final_value)
            if 'max_value' in mapping:
                final_value = min(mapping['max_value'], final_value)
            
            # Set parameter
            setattr(target_op.par, param_name, final_value)
            
        except Exception as e:
            debug(f"Error applying address mapping: {str(e)}")
    
    def send_osc_message(self, output_name, address, *args):
        """Send OSC message with error handling and queuing"""
        try:
            if output_name not in self.osc_outputs:
                debug(f"OSC output not found: {output_name}")
                return False
            
            output_config = self.osc_outputs[output_name]
            osc_out = output_config['osc_out']
            
            if not osc_out or not output_config['active']:
                debug(f"OSC output {output_name} not active")
                return False
            
            # Send message
            osc_out.sendOSC(address, *args)
            
            # Update statistics
            output_config['message_count'] += 1
            
            debug(f"Sent OSC message: {address} {args} via {output_name}")
            return True
            
        except Exception as e:
            debug(f"Error sending OSC message via {output_name}: {str(e)}")
            return False
    
    def setup_connection_monitoring(self, connection_name, connection_type):
        """Set up connection monitoring for OSC endpoints"""
        self.connection_monitor[connection_name] = {
            'type': connection_type,
            'status': 'unknown',
            'last_activity': absTime.seconds,
            'message_count': 0,
            'errors': []
        }
    
    def handle_connection_event(self, connection_name, event_type, peer):
        """Handle connection events"""
        if connection_name in self.connection_monitor:
            monitor_info = self.connection_monitor[connection_name]
            monitor_info['status'] = event_type
            monitor_info['last_activity'] = absTime.seconds
            
            if event_type == 'connect':
                monitor_info['peer'] = str(peer)
            elif event_type == 'disconnect':
                monitor_info['peer'] = None
    
    def get_connection_status(self):
        """Get status of all OSC connections"""
        status = {
            'inputs': {},
            'outputs': {},
            'total_messages': len(self.message_history)
        }
        
        for name, config in self.osc_inputs.items():
            status['inputs'][name] = {
                'active': config['active'],
                'port': config['config'].get('port'),
                'message_count': config['message_count'],
                'last_message': config['last_message_time']
            }
        
        for name, config in self.osc_outputs.items():
            status['outputs'][name] = {
                'active': config['active'],
                'address': config['config'].get('address'),
                'port': config['config'].get('port'),
                'message_count': config['message_count']
            }
        
        return status

# Global OSC manager
osc_manager = OSCManager()

# Make available to module system
if hasattr(mod, '__dict__'):
    mod.osc_manager = osc_manager
```

### OSC Control Surface Integration

```python
class OSCControlSurface:
    """Integration with OSC control surfaces like TouchOSC, Lemur, etc."""
    
    def __init__(self, surface_name, config):
        self.surface_name = surface_name
        self.config = config
        self.controls = {}
        self.layouts = {}
        self.setup_control_surface()
    
    def setup_control_surface(self):
        """Set up control surface integration"""
        # Create OSC input for receiving from surface
        input_config = {
            'port': self.config.get('receive_port', 9000),
            'address': self.config.get('surface_address', '0.0.0.0')
        }
        
        self.osc_input = osc_manager.create_osc_input(
            f"{self.surface_name}_input", 
            input_config
        )
        
        # Create OSC output for sending to surface
        output_config = {
            'address': self.config.get('surface_ip', '192.168.1.100'),
            'port': self.config.get('send_port', 9001)
        }
        
        self.osc_output = osc_manager.create_osc_output(
            f"{self.surface_name}_output", 
            output_config
        )
        
        # Register message handlers for surface
        self.register_surface_handlers()
        
        debug(f"Control surface {self.surface_name} initialized")
    
    def register_surface_handlers(self):
        """Register OSC handlers for control surface messages"""
        # Fader handlers
        osc_manager.register_message_handler(
            '/*/fader*', 
            self.handle_fader_message
        )
        
        # Button handlers
        osc_manager.register_message_handler(
            '/*/push*', 
            self.handle_button_message
        )
        
        # XY pad handlers
        osc_manager.register_message_handler(
            '/*/xy*', 
            self.handle_xy_message
        )
        
        # Rotary encoder handlers
        osc_manager.register_message_handler(
            '/*/rotary*', 
            self.handle_rotary_message
        )
    
    def handle_fader_message(self, message_data):
        """Handle fader control messages"""
        try:
            address = message_data['address']
            args = message_data.get('args', [])
            
            if len(args) == 0:
                return
            
            fader_value = args[0]  # Typically 0.0 to 1.0
            
            # Extract fader number from address
            fader_id = self.extract_control_id(address, 'fader')
            
            if fader_id in self.controls:
                control_config = self.controls[fader_id]
                self.apply_control_mapping(control_config, fader_value)
            else:
                debug(f"Unmapped fader: {address} = {fader_value}")
                
        except Exception as e:
            debug(f"Error handling fader message: {str(e)}")
    
    def handle_button_message(self, message_data):
        """Handle button press messages"""
        try:
            address = message_data['address']
            args = message_data.get('args', [])
            
            if len(args) == 0:
                return
            
            button_state = args[0]  # Typically 0 or 1
            
            # Extract button number from address
            button_id = self.extract_control_id(address, 'push')
            
            if button_id in self.controls:
                control_config = self.controls[button_id]
                
                if button_state == 1:  # Button pressed
                    self.handle_button_press(control_config)
                else:  # Button released
                    self.handle_button_release(control_config)
            else:
                debug(f"Unmapped button: {address} = {button_state}")
                
        except Exception as e:
            debug(f"Error handling button message: {str(e)}")
    
    def handle_xy_message(self, message_data):
        """Handle XY pad control messages"""
        try:
            address = message_data['address']
            args = message_data.get('args', [])
            
            if len(args) < 2:
                return
            
            x_value = args[0]
            y_value = args[1]
            
            # Extract XY pad ID
            xy_id = self.extract_control_id(address, 'xy')
            
            if xy_id in self.controls:
                control_config = self.controls[xy_id]
                self.apply_xy_mapping(control_config, x_value, y_value)
            else:
                debug(f"Unmapped XY pad: {address} = ({x_value}, {y_value})")
                
        except Exception as e:
            debug(f"Error handling XY message: {str(e)}")
    
    def handle_rotary_message(self, message_data):
        """Handle rotary encoder messages"""
        try:
            address = message_data['address']
            args = message_data.get('args', [])
            
            if len(args) == 0:
                return
            
            rotary_value = args[0]
            
            # Extract rotary ID
            rotary_id = self.extract_control_id(address, 'rotary')
            
            if rotary_id in self.controls:
                control_config = self.controls[rotary_id]
                self.apply_control_mapping(control_config, rotary_value)
            else:
                debug(f"Unmapped rotary: {address} = {rotary_value}")
                
        except Exception as e:
            debug(f"Error handling rotary message: {str(e)}")
    
    def extract_control_id(self, address, control_type):
        """Extract control ID from OSC address"""
        import re
        
        # Pattern to match control type and number
        pattern = f'.*/{control_type}(\\d+)'
        match = re.search(pattern, address)
        
        if match:
            return f"{control_type}_{match.group(1)}"
        else:
            return f"{control_type}_unknown"
    
    def register_control_mapping(self, control_id, mapping_config):
        """Register control mapping configuration"""
        self.controls[control_id] = mapping_config
        debug(f"Registered control mapping: {control_id}")
    
    def apply_control_mapping(self, control_config, value):
        """Apply control value to TouchDesigner parameters"""
        try:
            for target in control_config.get('targets', []):
                target_op_path = target['operator']
                param_name = target['parameter']
                
                target_op = op(target_op_path)
                if not target_op or not hasattr(target_op.par, param_name):
                    continue
                
                # Apply scaling and range mapping
                final_value = value
                
                if 'input_range' in target and 'output_range' in target:
                    input_min, input_max = target['input_range']
                    output_min, output_max = target['output_range']
                    
                    # Map from input range to output range
                    normalized = (value - input_min) / (input_max - input_min)
                    final_value = output_min + normalized * (output_max - output_min)
                
                # Set parameter
                setattr(target_op.par, param_name, final_value)
                
        except Exception as e:
            debug(f"Error applying control mapping: {str(e)}")
    
    def apply_xy_mapping(self, control_config, x_value, y_value):
        """Apply XY pad values to TouchDesigner parameters"""
        try:
            targets = control_config.get('targets', [])
            
            for target in targets:
                if target['axis'] == 'x':
                    self.apply_control_mapping({'targets': [target]}, x_value)
                elif target['axis'] == 'y':
                    self.apply_control_mapping({'targets': [target]}, y_value)
                    
        except Exception as e:
            debug(f"Error applying XY mapping: {str(e)}")
    
    def handle_button_press(self, control_config):
        """Handle button press actions"""
        try:
            action_type = control_config.get('action', 'parameter')
            
            if action_type == 'pulse':
                # Pulse a parameter
                for target in control_config.get('targets', []):
                    target_op = op(target['operator'])
                    if target_op and hasattr(target_op.par, target['parameter']):
                        getattr(target_op.par, target['parameter']).pulse()
            
            elif action_type == 'toggle':
                # Toggle a boolean parameter
                for target in control_config.get('targets', []):
                    target_op = op(target['operator'])
                    if target_op and hasattr(target_op.par, target['parameter']):
                        param = getattr(target_op.par, target['parameter'])
                        current_value = param.eval()
                        new_value = 1 if current_value == 0 else 0
                        param.val = new_value
            
            elif action_type == 'scene_change':
                # Change scene or preset
                scene_name = control_config.get('scene_name')
                if scene_name and hasattr(mod, 'av_performance'):
                    mod.av_performance.switch_scene(scene_name)
                    
        except Exception as e:
            debug(f"Error handling button press: {str(e)}")
    
    def handle_button_release(self, control_config):
        """Handle button release actions"""
        # Most button actions happen on press, but some might need release handling
        pass
    
    def send_feedback(self, control_id, value):
        """Send feedback to control surface"""
        try:
            if control_id in self.controls:
                control_config = self.controls[control_id]
                feedback_address = control_config.get('feedback_address')
                
                if feedback_address:
                    osc_manager.send_osc_message(
                        f"{self.surface_name}_output",
                        feedback_address,
                        value
                    )
                    
        except Exception as e:
            debug(f"Error sending feedback: {str(e)}")

# Create control surface instances
def create_touchosc_surface():
    """Create TouchOSC control surface integration"""
    touchosc_config = {
        'surface_ip': '192.168.1.100',
        'receive_port': 9000,
        'send_port': 9001
    }
    
    surface = OSCControlSurface('touchosc', touchosc_config)
    
    # Register control mappings
    surface.register_control_mapping('fader_1', {
        'targets': [
            {
                'operator': '/project1/geo1',
                'parameter': 'sx',
                'input_range': [0.0, 1.0],
                'output_range': [0.1, 3.0]
            }
        ]
    })
    
    surface.register_control_mapping('push_1', {
        'action': 'scene_change',
        'scene_name': 'high_energy'
    })
    
    surface.register_control_mapping('xy_1', {
        'targets': [
            {
                'operator': '/project1/cam1',
                'parameter': 'tx',
                'axis': 'x',
                'input_range': [0.0, 1.0],
                'output_range': [-10.0, 10.0]
            },
            {
                'operator': '/project1/cam1',
                'parameter': 'tz',
                'axis': 'y',
                'input_range': [0.0, 1.0],
                'output_range': [-10.0, 10.0]
            }
        ]
    })
    
    return surface

touchosc_surface = create_touchosc_surface()
```

## TCP/IP and UDP Communication

### Robust Network Communication Manager

```python
class NetworkCommunicationManager:
    """Advanced TCP/IP and UDP communication management"""
    
    def __init__(self):
        self.tcp_connections = {}
        self.udp_connections = {}
        self.protocol_handlers = {}
        self.connection_monitor = {}
        self.message_queues = {}
        self.setup_network_system()
    
    def setup_network_system(self):
        """Initialize network communication infrastructure"""
        parent_comp = op('/project1') or root
        self.network_container = parent_comp.create(baseCOMP, 'network_system')
        
        debug("Network Communication Manager initialized")
    
    def create_tcp_server(self, server_name, config):
        """Create TCP server with comprehensive connection handling"""
        try:
            container = self.network_container
            
            # Create TCP/IP DAT in server mode
            tcp_dat = container.create(tcpipDAT, f"{server_name}_server")
            tcp_dat.par.protocol = 'TCP'
            tcp_dat.par.mode = 'Server'
            tcp_dat.par.port = config.get('port', 8080)
            tcp_dat.par.active = True
            
            # Create execute DAT for connection handling
            execute_dat = container.create(executeDAT, f"{server_name}_execute")
            execute_dat.text = self.generate_tcp_callback_script(server_name, 'server')
            
            # Create message queue
            queue_dat = container.create(textDAT, f"{server_name}_queue")
            
            # Store configuration
            connection_config = {
                'tcp_dat': tcp_dat,
                'execute_dat': execute_dat,
                'queue_dat': queue_dat,
                'type': 'server',
                'config': config,
                'active': True,
                'connected_clients': {},
                'message_count': 0
            }
            
            self.tcp_connections[server_name] = connection_config
            self.setup_connection_monitoring(server_name, 'tcp_server')
            
            debug(f"Created TCP server: {server_name} on port {config.get('port', 8080)}")
            return connection_config
            
        except Exception as e:
            debug(f"Error creating TCP server {server_name}: {str(e)}")
            return None
    
    def create_tcp_client(self, client_name, config):
        """Create TCP client with automatic reconnection"""
        try:
            container = self.network_container
            
            # Create TCP/IP DAT in client mode
            tcp_dat = container.create(tcpipDAT, f"{client_name}_client")
            tcp_dat.par.protocol = 'TCP'
            tcp_dat.par.mode = 'Client'
            tcp_dat.par.networkaddress = config.get('address', '127.0.0.1')
            tcp_dat.par.networkport = config.get('port', 8080)
            tcp_dat.par.active = True
            
            # Create execute DAT for connection handling
            execute_dat = container.create(executeDAT, f"{client_name}_execute")
            execute_dat.text = self.generate_tcp_callback_script(client_name, 'client')
            
            # Create message queue
            queue_dat = container.create(textDAT, f"{client_name}_queue")
            
            # Store configuration
            connection_config = {
                'tcp_dat': tcp_dat,
                'execute_dat': execute_dat,
                'queue_dat': queue_dat,
                'type': 'client',
                'config': config,
                'active': True,
                'connection_status': 'connecting',
                'message_count': 0,
                'reconnect_attempts': 0
            }
            
            self.tcp_connections[client_name] = connection_config
            self.setup_connection_monitoring(client_name, 'tcp_client')
            
            debug(f"Created TCP client: {client_name} to {config.get('address')}:{config.get('port')}")
            return connection_config
            
        except Exception as e:
            debug(f"Error creating TCP client {client_name}: {str(e)}")
            return None
    
    def create_udp_connection(self, connection_name, config):
        """Create UDP connection for sending/receiving"""
        try:
            container = self.network_container
            
            if config.get('mode') == 'output':
                # Create UDP Out DAT
                udp_dat = container.create(udpoutDAT, f"{connection_name}_udp")
                udp_dat.par.networkaddress = config.get('address', '127.0.0.1')
                udp_dat.par.networkport = config.get('port', 8000)
                udp_dat.par.active = True
                
            else:
                # Create UDP In DAT
                udp_dat = container.create(udpinDAT, f"{connection_name}_udp")
                udp_dat.par.port = config.get('port', 8000)
                udp_dat.par.active = True
                
                # Create execute DAT for message handling
                execute_dat = container.create(executeDAT, f"{connection_name}_execute")
                execute_dat.text = self.generate_udp_callback_script(connection_name)
            
            # Create message queue
            queue_dat = container.create(textDAT, f"{connection_name}_queue")
            
            connection_config = {
                'udp_dat': udp_dat,
                'execute_dat': execute_dat if config.get('mode') != 'output' else None,
                'queue_dat': queue_dat,
                'config': config,
                'active': True,
                'message_count': 0
            }
            
            self.udp_connections[connection_name] = connection_config
            self.setup_connection_monitoring(connection_name, 'udp')
            
            debug(f"Created UDP connection: {connection_name}")
            return connection_config
            
        except Exception as e:
            debug(f"Error creating UDP connection {connection_name}: {str(e)}")
            return None
    
    def generate_tcp_callback_script(self, connection_name, connection_type):
        """Generate callback script for TCP connections"""
        script = f'''
# TCP callback script for {connection_name} ({connection_type})

def onConnect(dat, peer):
    """Handle TCP connection events"""
    try:
        debug(f"TCP connection established: {{str(peer)}}")
        if hasattr(mod, 'network_manager'):
            mod.network_manager.handle_tcp_connection('{connection_name}', 'connect', peer)
    except Exception as e:
        debug(f"Error in TCP connect callback: {{str(e)}}")

def onDisconnect(dat, peer):
    """Handle TCP disconnection events"""
    try:
        debug(f"TCP connection lost: {{str(peer)}}")
        if hasattr(mod, 'network_manager'):
            mod.network_manager.handle_tcp_connection('{connection_name}', 'disconnect', peer)
    except Exception as e:
        debug(f"Error in TCP disconnect callback: {{str(e)}}")

def onReceive(dat, rowIndex, message, peer):
    """Handle incoming TCP messages"""
    try:
        message_data = {{
            'timestamp': absTime.seconds,
            'message': message,
            'peer': str(peer),
            'connection_name': '{connection_name}',
            'type': 'tcp'
        }}
        
        if hasattr(mod, 'network_manager'):
            mod.network_manager.handle_network_message('{connection_name}', message_data)
        else:
            debug(f"TCP message from {{str(peer)}}: {{message}}")
            
    except Exception as e:
        debug(f"Error in TCP receive callback: {{str(e)}}")
'''
        return script
    
    def generate_udp_callback_script(self, connection_name):
        """Generate callback script for UDP connections"""
        script = f'''
# UDP callback script for {connection_name}

def onReceive(dat, rowIndex, message, peer):
    """Handle incoming UDP messages"""
    try:
        message_data = {{
            'timestamp': absTime.seconds,
            'message': message,
            'peer': str(peer),
            'connection_name': '{connection_name}',
            'type': 'udp'
        }}
        
        if hasattr(mod, 'network_manager'):
            mod.network_manager.handle_network_message('{connection_name}', message_data)
        else:
            debug(f"UDP message from {{str(peer)}}: {{message}}")
            
    except Exception as e:
        debug(f"Error in UDP receive callback: {{str(e)}}")
'''
        return script
    
    def handle_tcp_connection(self, connection_name, event_type, peer):
        """Handle TCP connection events"""
        try:
            if connection_name in self.tcp_connections:
                config = self.tcp_connections[connection_name]
                
                if event_type == 'connect':
                    if config['type'] == 'server':
                        # Add client to connected clients list
                        config['connected_clients'][str(peer)] = {
                            'peer': peer,
                            'connect_time': absTime.seconds,
                            'message_count': 0
                        }
                    else:
                        # Client connected successfully
                        config['connection_status'] = 'connected'
                        config['reconnect_attempts'] = 0
                
                elif event_type == 'disconnect':
                    if config['type'] == 'server':
                        # Remove client from connected clients list
                        if str(peer) in config['connected_clients']:
                            del config['connected_clients'][str(peer)]
                    else:
                        # Client disconnected - may need to reconnect
                        config['connection_status'] = 'disconnected'
                        self.schedule_reconnection(connection_name)
                
                # Update monitoring
                if connection_name in self.connection_monitor:
                    self.connection_monitor[connection_name]['last_event'] = {
                        'type': event_type,
                        'timestamp': absTime.seconds,
                        'peer': str(peer)
                    }
                    
        except Exception as e:
            debug(f"Error handling TCP connection event: {str(e)}")
    
    def handle_network_message(self, connection_name, message_data):
        """Handle incoming network messages with protocol processing"""
        try:
            # Update message statistics
            if connection_name in self.tcp_connections:
                self.tcp_connections[connection_name]['message_count'] += 1
            elif connection_name in self.udp_connections:
                self.udp_connections[connection_name]['message_count'] += 1
            
            # Process message based on registered protocol handlers
            message_text = message_data.get('message', '')
            
            # Try to match message with protocol handlers
            for protocol_name, handler in self.protocol_handlers.items():
                if self.message_matches_protocol(message_text, protocol_name):
                    handler(message_data)
                    return
            
            # Default handling if no protocol handler matches
            debug(f"Unhandled network message from {message_data.get('peer')}: {message_text}")
            
        except Exception as e:
            debug(f"Error handling network message: {str(e)}")
    
    def message_matches_protocol(self, message, protocol_name):
        """Check if message matches a specific protocol pattern"""
        # Simple protocol detection - can be extended
        protocol_patterns = {
            'json': lambda m: m.strip().startswith('{') and m.strip().endswith('}'),
            'xml': lambda m: m.strip().startswith('<') and m.strip().endswith('>'),
            'csv': lambda m: ',' in m,
            'custom_command': lambda m: m.startswith('CMD:')
        }
        
        if protocol_name in protocol_patterns:
            return protocol_patterns[protocol_name](message)
        
        return False
    
    def register_protocol_handler(self, protocol_name, handler_func):
        """Register protocol handler for specific message types"""
        self.protocol_handlers[protocol_name] = handler_func
        debug(f"Registered protocol handler: {protocol_name}")
    
    def send_tcp_message(self, connection_name, message, peer=None):
        """Send TCP message with error handling"""
        try:
            if connection_name not in self.tcp_connections:
                debug(f"TCP connection not found: {connection_name}")
                return False
            
            config = self.tcp_connections[connection_name]
            tcp_dat = config['tcp_dat']
            
            if not tcp_dat or not config['active']:
                debug(f"TCP connection {connection_name} not active")
                return False
            
            # Send message
            if peer:
                tcp_dat.send(message, peer)
            else:
                tcp_dat.send(message)
            
            config['message_count'] += 1
            debug(f"Sent TCP message via {connection_name}: {message}")
            return True
            
        except Exception as e:
            debug(f"Error sending TCP message via {connection_name}: {str(e)}")
            return False
    
    def send_udp_message(self, connection_name, message):
        """Send UDP message with error handling"""
        try:
            if connection_name not in self.udp_connections:
                debug(f"UDP connection not found: {connection_name}")
                return False
            
            config = self.udp_connections[connection_name]
            udp_dat = config['udp_dat']
            
            if not udp_dat or not config['active']:
                debug(f"UDP connection {connection_name} not active")
                return False
            
            # Send message
            udp_dat.send(message)
            
            config['message_count'] += 1
            debug(f"Sent UDP message via {connection_name}: {message}")
            return True
            
        except Exception as e:
            debug(f"Error sending UDP message via {connection_name}: {str(e)}")
            return False
    
    def schedule_reconnection(self, connection_name):
        """Schedule automatic reconnection for TCP client"""
        if connection_name not in self.tcp_connections:
            return
        
        config = self.tcp_connections[connection_name]
        if config['type'] != 'client':
            return
        
        config['reconnect_attempts'] += 1
        max_attempts = config['config'].get('max_reconnect_attempts', 10)
        
        if config['reconnect_attempts'] <= max_attempts:
            # Schedule reconnection with exponential backoff
            delay_seconds = min(30, 2 ** config['reconnect_attempts'])
            
            def attempt_reconnection():
                try:
                    tcp_dat = config['tcp_dat']
                    tcp_dat.par.active = False
                    run('tcp_dat.par.active = True', delayFrames=10)
                    debug(f"Attempting reconnection for {connection_name} (attempt {config['reconnect_attempts']})")
                except Exception as e:
                    debug(f"Error during reconnection attempt: {str(e)}")
            
            run('attempt_reconnection()', delayMilliSeconds=delay_seconds * 1000)
        else:
            debug(f"Max reconnection attempts reached for {connection_name}")
    
    def setup_connection_monitoring(self, connection_name, connection_type):
        """Set up connection monitoring"""
        self.connection_monitor[connection_name] = {
            'type': connection_type,
            'status': 'initializing',
            'last_activity': absTime.seconds,
            'message_count': 0,
            'errors': [],
            'last_event': None
        }
    
    def get_network_status(self):
        """Get comprehensive network status"""
        status = {
            'tcp_connections': {},
            'udp_connections': {},
            'protocol_handlers': list(self.protocol_handlers.keys())
        }
        
        for name, config in self.tcp_connections.items():
            status['tcp_connections'][name] = {
                'type': config['type'],
                'active': config['active'],
                'message_count': config['message_count'],
                'status': config.get('connection_status', 'unknown'),
                'connected_clients': len(config.get('connected_clients', {}))
            }
        
        for name, config in self.udp_connections.items():
            status['udp_connections'][name] = {
                'active': config['active'],
                'message_count': config['message_count']
            }
        
        return status

# Global network manager
network_manager = NetworkCommunicationManager()

# Make available to module system
if hasattr(mod, '__dict__'):
    mod.network_manager = network_manager
```

## WebSocket and Web Integration

### WebSocket Communication System

```python
class WebSocketManager:
    """Advanced WebSocket communication for web integration"""
    
    def __init__(self):
        self.websocket_connections = {}
        self.web_servers = {}
        self.client_sessions = {}
        self.setup_websocket_system()
    
    def setup_websocket_system(self):
        """Initialize WebSocket infrastructure"""
        parent_comp = op('/project1') or root
        self.websocket_container = parent_comp.create(baseCOMP, 'websocket_system')
        
        debug("WebSocket Manager initialized")
    
    def create_websocket_server(self, server_name, config):
        """Create WebSocket server for web client connections"""
        try:
            container = self.websocket_container
            
            # Create WebSocket DAT
            websocket_dat = container.create(websocketDAT, f"{server_name}_ws")
            websocket_dat.par.port = config.get('port', 9980)
            websocket_dat.par.active = True
            
            # Create web server for serving web interface
            webserver_dat = container.create(webserverDAT, f"{server_name}_server")
            webserver_dat.par.port = config.get('web_port', 8080)
            webserver_dat.par.active = True
            
            # Create execute DAT for WebSocket events
            execute_dat = container.create(executeDAT, f"{server_name}_execute")
            execute_dat.text = self.generate_websocket_callback_script(server_name)
            
            # Store configuration
            server_config = {
                'websocket_dat': websocket_dat,
                'webserver_dat': webserver_dat,
                'execute_dat': execute_dat,
                'config': config,
                'active': True,
                'connected_clients': {},
                'message_count': 0
            }
            
            self.websocket_connections[server_name] = server_config
            
            debug(f"Created WebSocket server: {server_name} on port {config.get('port', 9980)}")
            return server_config
            
        except Exception as e:
            debug(f"Error creating WebSocket server {server_name}: {str(e)}")
            return None
    
    def generate_websocket_callback_script(self, server_name):
        """Generate callback script for WebSocket events"""
        script = f'''
# WebSocket callback script for {server_name}
import json

def onOpen(webSocketDAT, client):
    """Handle WebSocket client connection"""
    try:
        debug(f"WebSocket client connected: {{client}}")
        if hasattr(mod, 'websocket_manager'):
            mod.websocket_manager.handle_websocket_event('{server_name}', 'open', client)
    except Exception as e:
        debug(f"Error in WebSocket open callback: {{str(e)}}")

def onClose(webSocketDAT, client):
    """Handle WebSocket client disconnection"""
    try:
        debug(f"WebSocket client disconnected: {{client}}")
        if hasattr(mod, 'websocket_manager'):
            mod.websocket_manager.handle_websocket_event('{server_name}', 'close', client)
    except Exception as e:
        debug(f"Error in WebSocket close callback: {{str(e)}}")

def onReceiveText(webSocketDAT, client, data):
    """Handle incoming WebSocket text message"""
    try:
        message_data = {{
            'timestamp': absTime.seconds,
            'client': client,
            'data': data,
            'server_name': '{server_name}',
            'type': 'text'
        }}
        
        if hasattr(mod, 'websocket_manager'):
            mod.websocket_manager.handle_websocket_message('{server_name}', message_data)
        else:
            debug(f"WebSocket text from {{client}}: {{data}}")
            
    except Exception as e:
        debug(f"Error in WebSocket text callback: {{str(e)}}")

def onReceiveBinary(webSocketDAT, client, data):
    """Handle incoming WebSocket binary message"""
    try:
        message_data = {{
            'timestamp': absTime.seconds,
            'client': client,
            'data': data,
            'server_name': '{server_name}',
            'type': 'binary'
        }}
        
        if hasattr(mod, 'websocket_manager'):
            mod.websocket_manager.handle_websocket_message('{server_name}', message_data)
        else:
            debug(f"WebSocket binary from {{client}}: {{len(data)}} bytes")
            
    except Exception as e:
        debug(f"Error in WebSocket binary callback: {{str(e)}}")
'''
        return script
    
    def handle_websocket_event(self, server_name, event_type, client):
        """Handle WebSocket connection events"""
        try:
            if server_name not in self.websocket_connections:
                return
            
            server_config = self.websocket_connections[server_name]
            
            if event_type == 'open':
                # Add client to connected clients
                client_id = str(client)
                server_config['connected_clients'][client_id] = {
                    'client': client,
                    'connect_time': absTime.seconds,
                    'message_count': 0,
                    'session_data': {}
                }
                
                # Send welcome message
                welcome_message = {
                    'type': 'welcome',
                    'server': server_name,
                    'timestamp': absTime.seconds
                }
                self.send_websocket_message(server_name, client, welcome_message)
                
            elif event_type == 'close':
                # Remove client from connected clients
                client_id = str(client)
                if client_id in server_config['connected_clients']:
                    del server_config['connected_clients'][client_id]
                    
        except Exception as e:
            debug(f"Error handling WebSocket event: {str(e)}")
    
    def handle_websocket_message(self, server_name, message_data):
        """Handle incoming WebSocket messages"""
        try:
            if server_name not in self.websocket_connections:
                return
            
            server_config = self.websocket_connections[server_name]
            client = message_data['client']
            client_id = str(client)
            
            # Update client statistics
            if client_id in server_config['connected_clients']:
                server_config['connected_clients'][client_id]['message_count'] += 1
            
            server_config['message_count'] += 1
            
            # Parse message data
            if message_data['type'] == 'text':
                try:
                    # Try to parse as JSON
                    import json
                    parsed_data = json.loads(message_data['data'])
                    self.process_websocket_json_message(server_name, client, parsed_data)
                except json.JSONDecodeError:
                    # Handle as plain text
                    self.process_websocket_text_message(server_name, client, message_data['data'])
            
            elif message_data['type'] == 'binary':
                self.process_websocket_binary_message(server_name, client, message_data['data'])
                
        except Exception as e:
            debug(f"Error handling WebSocket message: {str(e)}")
    
    def process_websocket_json_message(self, server_name, client, data):
        """Process JSON WebSocket messages"""
        try:
            message_type = data.get('type', 'unknown')
            
            if message_type == 'control':
                # Handle control messages
                self.handle_websocket_control_message(server_name, client, data)
            
            elif message_type == 'parameter':
                # Handle parameter updates
                self.handle_websocket_parameter_message(server_name, client, data)
            
            elif message_type == 'request_status':
                # Send status update
                self.send_status_update(server_name, client)
            
            else:
                debug(f"Unknown WebSocket message type: {message_type}")
                
        except Exception as e:
            debug(f"Error processing WebSocket JSON message: {str(e)}")
    
    def handle_websocket_control_message(self, server_name, client, data):
        """Handle control messages from web clients"""
        try:
            action = data.get('action')
            
            if action == 'scene_change':
                scene_name = data.get('scene_name')
                if scene_name and hasattr(mod, 'av_performance'):
                    success = mod.av_performance.switch_scene(scene_name)
                    self.send_websocket_message(server_name, client, {
                        'type': 'control_response',
                        'action': action,
                        'success': success,
                        'scene_name': scene_name
                    })
            
            elif action == 'emergency_stop':
                if hasattr(mod, 'av_performance'):
                    mod.av_performance.emergency_audio_stop()
                    # Broadcast to all clients
                    self.broadcast_message(server_name, {
                        'type': 'emergency_stop',
                        'timestamp': absTime.seconds
                    })
            
        except Exception as e:
            debug(f"Error handling control message: {str(e)}")
    
    def handle_websocket_parameter_message(self, server_name, client, data):
        """Handle parameter update messages"""
        try:
            operator_path = data.get('operator')
            parameter_name = data.get('parameter')
            value = data.get('value')
            
            if operator_path and parameter_name and value is not None:
                target_op = op(operator_path)
                if target_op and hasattr(target_op.par, parameter_name):
                    setattr(target_op.par, parameter_name, value)
                    
                    # Send confirmation
                    self.send_websocket_message(server_name, client, {
                        'type': 'parameter_response',
                        'operator': operator_path,
                        'parameter': parameter_name,
                        'value': value,
                        'success': True
                    })
                else:
                    # Send error
                    self.send_websocket_message(server_name, client, {
                        'type': 'parameter_response',
                        'operator': operator_path,
                        'parameter': parameter_name,
                        'success': False,
                        'error': 'Parameter not found'
                    })
                    
        except Exception as e:
            debug(f"Error handling parameter message: {str(e)}")
    
    def send_websocket_message(self, server_name, client, message_data):
        """Send message to WebSocket client"""
        try:
            if server_name not in self.websocket_connections:
                return False
            
            server_config = self.websocket_connections[server_name]
            websocket_dat = server_config['websocket_dat']
            
            if not websocket_dat or not server_config['active']:
                return False
            
            # Convert to JSON if it's a dict
            if isinstance(message_data, dict):
                import json
                message_text = json.dumps(message_data)
            else:
                message_text = str(message_data)
            
            # Send message
            websocket_dat.send(message_text, client)
            return True
            
        except Exception as e:
            debug(f"Error sending WebSocket message: {str(e)}")
            return False
    
    def broadcast_message(self, server_name, message_data):
        """Broadcast message to all connected WebSocket clients"""
        try:
            if server_name not in self.websocket_connections:
                return False
            
            server_config = self.websocket_connections[server_name]
            
            for client_id, client_info in server_config['connected_clients'].items():
                self.send_websocket_message(server_name, client_info['client'], message_data)
            
            return True
            
        except Exception as e:
            debug(f"Error broadcasting WebSocket message: {str(e)}")
            return False
    
    def send_status_update(self, server_name, client):
        """Send comprehensive status update to client"""
        try:
            status_data = {
                'type': 'status_update',
                'timestamp': absTime.seconds,
                'frame': absTime.frame,
                'touchdesigner': {
                    'fps': absTime.rate if hasattr(absTime, 'rate') else 60
                }
            }
            
            # Add performance system status if available
            if hasattr(mod, 'av_performance'):
                status_data['performance_system'] = mod.av_performance.get_system_status()
            
            # Add network status
            if hasattr(mod, 'network_manager'):
                status_data['network'] = mod.network_manager.get_network_status()
            
            # Add OSC status
            if hasattr(mod, 'osc_manager'):
                status_data['osc'] = mod.osc_manager.get_connection_status()
            
            self.send_websocket_message(server_name, client, status_data)
            
        except Exception as e:
            debug(f"Error sending status update: {str(e)}")
    
    def get_websocket_status(self):
        """Get WebSocket system status"""
        status = {
            'servers': {}
        }
        
        for name, config in self.websocket_connections.items():
            status['servers'][name] = {
                'active': config['active'],
                'connected_clients': len(config['connected_clients']),
                'message_count': config['message_count'],
                'port': config['config'].get('port')
            }
        
        return status

# Global WebSocket manager
websocket_manager = WebSocketManager()

# Make available to module system
if hasattr(mod, '__dict__'):
    mod.websocket_manager = websocket_manager
```

## Integration and Usage Examples

### Complete Multi-Protocol Communication Hub

```python
def setup_communication_hub():
    """Set up complete multi-protocol communication hub"""
    debug("Setting up communication hub...")
    
    # Set up OSC communication
    osc_input_config = {
        'port': 9000,
        'address': '0.0.0.0'
    }
    osc_manager.create_osc_input('main_input', osc_input_config)
    
    osc_output_config = {
        'address': '127.0.0.1',
        'port': 9001
    }
    osc_manager.create_osc_output('main_output', osc_output_config)
    
    # Set up TCP server
    tcp_server_config = {
        'port': 8080
    }
    network_manager.create_tcp_server('control_server', tcp_server_config)
    
    # Set up UDP communication
    udp_input_config = {
        'port': 8000,
        'mode': 'input'
    }
    network_manager.create_udp_connection('sensor_input', udp_input_config)
    
    # Set up WebSocket server
    websocket_config = {
        'port': 9980,
        'web_port': 8081
    }
    websocket_manager.create_websocket_server('web_control', websocket_config)
    
    # Register protocol handlers
    network_manager.register_protocol_handler('json', handle_json_protocol)
    network_manager.register_protocol_handler('custom_command', handle_custom_commands)
    
    # Set up OSC control mappings
    setup_osc_control_mappings()
    
    debug("Communication hub setup complete!")

def handle_json_protocol(message_data):
    """Handle JSON protocol messages"""
    try:
        import json
        data = json.loads(message_data['message'])
        
        if 'command' in data:
            command = data['command']
            
            if command == 'set_parameter':
                op_path = data.get('operator')
                param = data.get('parameter')
                value = data.get('value')
                
                target_op = op(op_path)
                if target_op and hasattr(target_op.par, param):
                    setattr(target_op.par, param, value)
                    debug(f"Set {op_path}.{param} = {value}")
            
            elif command == 'get_status':
                # Send status back via same connection
                status = get_system_status()
                response = json.dumps(status)
                
                connection_name = message_data['connection_name']
                if message_data['type'] == 'tcp':
                    network_manager.send_tcp_message(connection_name, response, message_data['peer'])
                elif message_data['type'] == 'udp':
                    network_manager.send_udp_message(connection_name, response)
                    
    except Exception as e:
        debug(f"Error handling JSON protocol: {str(e)}")

def handle_custom_commands(message_data):
    """Handle custom command protocol"""
    try:
        message = message_data['message']
        if message.startswith('CMD:'):
            command = message[4:].strip()
            
            if command == 'EMERGENCY_STOP':
                if hasattr(mod, 'av_performance'):
                    mod.av_performance.emergency_audio_stop()
            
            elif command.startswith('SCENE:'):
                scene_name = command[6:].strip()
                if hasattr(mod, 'av_performance'):
                    mod.av_performance.switch_scene(scene_name)
            
            elif command == 'STATUS':
                status = get_system_status()
                status_message = f"STATUS:{status}"
                
                connection_name = message_data['connection_name']
                if message_data['type'] == 'tcp':
                    network_manager.send_tcp_message(connection_name, status_message, message_data['peer'])
                    
    except Exception as e:
        debug(f"Error handling custom commands: {str(e)}")

def setup_osc_control_mappings():
    """Set up comprehensive OSC control mappings"""
    # Direct parameter mappings
    osc_manager.register_address_mapping('/volume', {
        'operator': '/project1/audio/master_volume',
        'parameter': 'gain',
        'scale': 2.0,
        'min_value': 0.0,
        'max_value': 1.0
    })
    
    osc_manager.register_address_mapping('/camera/position/x', {
        'operator': '/project1/cam1',
        'parameter': 'tx',
        'scale': 10.0,
        'offset': -5.0
    })
    
    # Pattern-based handlers
    def handle_fader_bank(message_data):
        """Handle bank of faders"""
        address = message_data['address']
        args = message_data['args']
        
        if len(args) > 0:
            # Extract fader number from address like /fader/1, /fader/2, etc.
            import re
            match = re.search(r'/fader/(\d+)', address)
            if match:
                fader_num = int(match.group(1))
                value = args[0]
                
                # Map to different parameters based on fader number
                if fader_num == 1:
                    target_op = op('/project1/geo1')
                    if target_op:
                        target_op.par.sx = value * 3.0
                elif fader_num == 2:
                    target_op = op('/project1/lights/main')
                    if target_op:
                        target_op.par.dimmer = value
    
    osc_manager.register_message_handler('/fader/*', handle_fader_bank)

def get_system_status():
    """Get comprehensive system status"""
    status = {
        'timestamp': absTime.seconds,
        'frame': absTime.frame,
        'touchdesigner_fps': absTime.rate if hasattr(absTime, 'rate') else 60
    }
    
    # Add communication system statuses
    if hasattr(mod, 'osc_manager'):
        status['osc'] = mod.osc_manager.get_connection_status()
    
    if hasattr(mod, 'network_manager'):
        status['network'] = mod.network_manager.get_network_status()
    
    if hasattr(mod, 'websocket_manager'):
        status['websocket'] = mod.websocket_manager.get_websocket_status()
    
    # Add performance system status
    if hasattr(mod, 'av_performance'):
        status['performance'] = mod.av_performance.get_system_status()
    
    return status

# Main update function
def update_communication_systems():
    """Main update function for all communication systems"""
    try:
        # Update connection monitoring
        current_time = absTime.seconds
        
        # Periodic status broadcasts via WebSocket
        if hasattr(mod, 'websocket_manager') and current_time % 5.0 < 0.1:  # Every 5 seconds
            for server_name in mod.websocket_manager.websocket_connections:
                status_update = {
                    'type': 'periodic_status',
                    'data': get_system_status()
                }
                mod.websocket_manager.broadcast_message(server_name, status_update)
        
    except Exception as e:
        debug(f"Error in communication systems update: {str(e)}")

# Convenience functions
def send_osc_broadcast(address, *args):
    """Send OSC message to all outputs"""
    for output_name in osc_manager.osc_outputs:
        osc_manager.send_osc_message(output_name, address, *args)

def broadcast_emergency_stop():
    """Broadcast emergency stop to all communication channels"""
    # OSC broadcast
    send_osc_broadcast('/emergency_stop', 1)
    
    # TCP broadcast
    for connection_name in network_manager.tcp_connections:
        network_manager.send_tcp_message(connection_name, 'CMD:EMERGENCY_STOP')
    
    # WebSocket broadcast
    for server_name in websocket_manager.websocket_connections:
        websocket_manager.broadcast_message(server_name, {
            'type': 'emergency_stop',
            'timestamp': absTime.seconds
        })

# Initialize communication hub
setup_communication_hub()
```

## Cross-References

**Related Documentation:**
- [EX_Advanced_Python_API_Patterns](./EX_Advanced_Python_API_Patterns.md) - Advanced Python integration
- [EX_Audio_Reactive_Systems](./EX_Audio_Reactive_Systems.md) - Audio system integration
- [PY_Debugging_Error_Handling](../PYTHON_/PY_Debugging_Error_Handling.md) - Python debugging systems
- [REF_Troubleshooting_Guide](../REFERENCE_/REF_Troubleshooting_Guide.md) - Network troubleshooting workflows
- [PERF_Optimize](../PERFORMANCE_/PERF_Optimize.md) - Network performance optimization

**TouchDesigner Operators:**
- [OSC In DAT](../TD_/TD_OPERATORS/DAT/oscinDAT.md)
- [OSC Out DAT](../TD_/TD_OPERATORS/DAT/oscoutDAT.md)
- [TCP/IP DAT](../TD_/TD_OPERATORS/DAT/tcpipDAT.md)
- [WebSocket DAT](../TD_/TD_OPERATORS/DAT/websocketDAT.md)

---

*This comprehensive network communication guide provides production-ready patterns for integrating TouchDesigner with external devices, web interfaces, and multi-machine setups using various communication protocols.*