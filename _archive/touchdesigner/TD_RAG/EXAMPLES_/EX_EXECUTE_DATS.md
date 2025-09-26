---
title: "Execute DAT Patterns Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "25-35 minutes"
user_personas: ["script_developer", "interactive_designer", "performance_artist"]
operators: ["executeDAT", "parameterExecuteDAT", "panelExecuteDAT", "opExecuteDAT", "datExecuteDAT", "chopExecuteDAT"]
concepts: ["execute_dats", "frame_execution", "event_monitoring", "performance_monitoring", "automation"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "callback_concepts"]
workflows: ["event_driven_programming", "performance_monitoring", "automation_systems"]
keywords: ["execute", "frame", "monitoring", "events", "automation", "performance"]
tags: ["python", "execute", "monitoring", "events", "frame", "examples"]
related_docs: ["EX_CALLBACKS", "CLASS_executeDAT_Class", "TD_Timeline", "PERF_Performance_Monitor_Dialog"]
example_count: 26
---

# TouchDesigner Python Examples: Execute DAT Patterns

## Overview

Comprehensive examples for Execute DAT operators in TouchDesigner, demonstrating frame-based execution, event monitoring, and callback patterns. Execute DATs provide the foundation for reactive programming and event-driven behavior in TouchDesigner networks.

**Source**: TouchDesigner Help > Python Examples > Execute_DATs  
**Example Count**: 26 files  
**Focus**: Event handling, frame-based execution, monitoring patterns

## Quick Reference

### Core Execute Types

- **[Execute DAT](#execute-dat)** - Frame-based and system lifecycle callbacks
- **[Parameter Execute](#parameter-execute)** - Parameter change monitoring and callbacks
- **[Panel Execute](#panel-execute)** - UI interaction and panel value callbacks
- **[OP Execute](#op-execute)** - Operator lifecycle and network change monitoring

### Specialized Execute Types  

- **[DAT Execute](#dat-execute)** - Table and data change monitoring
- **[CHOP Execute](#chop-execute)** - Channel data change detection
- **[Event Patterns](#event-patterns)** - Common event handling strategies
- **[Performance Tips](#performance-tips)** - Efficient execution patterns

---

## Execute DAT

### Basic System Callbacks

**Source File**: `execute1.py`

**Key Concepts**: Frame-based execution, system lifecycle, timeline events

```python
# Global variables available in Execute DAT:
# me - this DAT
# frame - the current frame
# state - True if the timeline is paused

# Make sure the corresponding toggle is enabled in the Execute DAT.

def onStart():
    """Called when TouchDesigner starts or timeline begins"""
    debug('onStart')

def onCreate():
    """Called when this DAT is created (to see: delete DAT, then undo)"""
    debug('onCreate')

def onExit():
    """Called when TouchDesigner exits (tricky to see - runs on exit)"""
    debug('onExit')

def onFrameStart(frame):
    """Called at the beginning of each frame"""
    debug('onFrameStart', frame)
    
    # Access global time info
    current_seconds = absTime.seconds
    frame_rate = project.cookRate
    
    # Perform per-frame setup
    prepare_frame_data(frame)

def onFrameEnd(frame):
    """Called at the end of each frame"""
    debug('onFrameEnd', frame)
    
    # Cleanup, logging, post-frame processing
    log_frame_performance(frame)

def onPlayStateChange(state):
    """Called when timeline is paused or played"""
    debug('onPlayStateChange', state)
    
    if state:
        print("Timeline paused")
        # Handle pause behavior
    else:
        print("Timeline playing") 
        # Handle play behavior

def onDeviceChange():
    """Called when system devices change"""
    debug('onDeviceChange')
    # Useful for monitoring device connections

def onProjectPreSave():
    """Called before project is saved"""
    debug('onProjectPreSave')
    # Opportunity to prepare data for save

def onProjectPostSave():
    """Called after project is saved"""  
    debug('onProjectPostSave')
    # Confirm save operations, update status
```

**Use Cases**:

- Frame-accurate processing and timing
- System event monitoring and logging
- Project lifecycle management
- Performance monitoring and debugging

### Frame-Based Processing Patterns

```python
def onFrameStart(frame):
    """Advanced frame processing patterns"""
    
    # Frame-rate dependent processing
    frame_rate = project.cookRate
    time_delta = 1.0 / frame_rate if frame_rate > 0 else 0
    
    # Skip processing for performance
    if frame % 5 == 0:  # Process every 5th frame
        update_heavy_calculations()
    
    # Time-based triggers
    if frame % int(frame_rate) == 0:  # Every second
        update_per_second_data()
    
    # Store frame data for analysis
    if not hasattr(me.parent(), 'frame_history'):
        me.parent().store('frame_history', [])
    
    history = me.parent().fetch('frame_history')
    history.append({
        'frame': frame,
        'time': absTime.seconds,
        'cook_count': me.parent().cook.count
    })
    
    # Keep only last 60 frames of history
    if len(history) > 60:
        history.pop(0)
    
    me.parent().store('frame_history', history)

def onFrameEnd(frame):
    """Frame cleanup and analysis"""
    
    # Calculate frame processing time
    start_time = me.parent().fetch('frame_start_time', 0)
    if start_time:
        processing_time = absTime.seconds - start_time
        if processing_time > 0.016:  # Longer than 60fps
            debug(f'Slow frame {frame}: {processing_time:.4f}s')
```

---

## Parameter Execute

### Parameter Change Monitoring

**Source File**: `parexec1.py`

**Key Concepts**: Parameter monitoring, value change detection, pulse handling

```python
# Global variables available in Parameter Execute DAT:
# me - this DAT
# par - the Par object that has changed
# val - the current value (in some callbacks)
# prev - the previous value

# Make sure the corresponding toggle is enabled in the Parameter Execute DAT.

def onValueChange(par, prev):
    """Called when any monitored parameter changes"""
    # Use par.eval() to get current value
    current = par.eval()
    print('onValueChange', par.name, current, prev)
    
    # Parameter-specific handling
    if par.name == 'tx':
        handle_position_change(current, prev)
    elif par.name == 'opacity':
        handle_opacity_change(current, prev)
    
    # Store parameter history
    store_parameter_change(par, current, prev)
    
    return

def onValuesChanged(changes):
    """Called at end of frame with complete list of parameter changes"""
    # The changes are a list of named tuples: (Par, previous value)
    print("onValuesChanged - Batch Update")
    print("All Changes:")
    
    for c in changes:
        par = c.par
        prev = c.prev
        current = par.eval()
        print(f'  {par.name}: {current} (was: {prev})')
    
    # Handle batch parameter updates efficiently
    process_batch_changes(changes)
    print('----------------------------------------')

def onPulse(par):
    """Called when pulse parameter is triggered"""
    print('pulse', par.name)
    
    # Handle specific pulse actions
    if par.name == 'reset':
        reset_component_state()
    elif par.name == 'trigger':
        execute_trigger_action()

def onExpressionChange(par, val, prev):
    """Called when parameter expression changes"""
    print('onExpressionChange', par.name, val, prev)
    
    # Monitor expression complexity
    if len(str(val)) > 100:
        debug(f'Complex expression in {par.name}: {val}')

def onExportChange(par, val, prev):
    """Called when CHOP export binding changes"""
    print('onExportChange', par.name, val, prev)
    
    # Track export connections
    track_chop_binding(par, val, prev)

def onEnableChange(par, val, prev):
    """Called when parameter enable state changes"""
    print('onEnableChange', par.name, val, prev)

def onModeChange(par, val, prev):
    """Called when parameter mode changes (Constant, Expression, etc.)"""
    print('onModeChange', par.name, val, prev)
```

### Advanced Parameter Monitoring

```python
def store_parameter_change(par, current, prev):
    """Store parameter changes for analysis"""
    # Get or create parameter history
    history_key = f'param_history_{par.owner.path}_{par.name}'
    history = me.parent().fetch(history_key, [])
    
    # Store change record
    change_record = {
        'frame': absTime.frame,
        'time': absTime.seconds,
        'value': current,
        'previous': prev,
        'operator': par.owner.path,
        'parameter': par.name
    }
    
    history.append(change_record)
    
    # Keep only last 100 changes
    if len(history) > 100:
        history.pop(0)
    
    me.parent().store(history_key, history)

def process_batch_changes(changes):
    """Handle multiple parameter changes efficiently"""
    # Group changes by operator
    by_operator = {}
    for change in changes:
        op_path = change.par.owner.path
        if op_path not in by_operator:
            by_operator[op_path] = []
        by_operator[op_path].append(change)
    
    # Process changes per operator
    for op_path, op_changes in by_operator.items():
        operator = op(op_path)
        if operator:
            update_operator_from_changes(operator, op_changes)

def handle_position_change(current, prev):
    """Specific handling for position parameters"""
    delta = abs(current - prev)
    if delta > 1.0:  # Large position change
        debug(f'Large position change: {delta}')
        # Trigger position-dependent updates
        update_position_dependent_systems(current)
```

### Button Integration Example

**Source File**: `button1/parexec1.py`

```python
def onValueChange(par, prev):
    """Button parameter callback example"""
    # Sync parameter to panel state when not selected
    if not parent().panel.select:
        parent().panel.state = par.eval()
    return
```

---

## Panel Execute

### UI Interaction Callbacks

**Source File**: `panelexec1.py`

**Key Concepts**: Panel value monitoring, UI state tracking, interaction patterns

```python
# Global variables available in Panel Execute DAT:
# me - this DAT
# panelValue - the PanelValue object that changed
# prev - the previous value of the PanelValue object

# Make sure the corresponding toggle is enabled in the Panel Execute DAT.

def onOffToOn(panelvalue):
    """Called when panel value transitions from off to on"""
    print('offToOn', panelvalue.name, panelvalue)
    
    # Handle UI activation
    if panelvalue.name == 'button1':
        activate_button_function()
    elif panelvalue.name.startswith('toggle'):
        handle_toggle_activation(panelvalue)
    
    return

def whileOn(panelvalue):
    """Called continuously while panel value is on"""
    print('whileOn', panelvalue.name, panelvalue)
    
    # Handle sustained interactions (like held buttons)
    if panelvalue.name == 'hold_button':
        process_continuous_action(panelvalue.val)
    
    return

def onOnToOff(panelvalue):
    """Called when panel value transitions from on to off"""
    print('onToOff', panelvalue.name, panelvalue)
    
    # Handle UI deactivation
    cleanup_button_action(panelvalue.name)
    return

def whileOff(panelvalue):
    """Called continuously while panel value is off"""
    print('whileOff', panelvalue.name, panelvalue)
    
    # Usually less commonly used
    return

def onValueChange(panelvalue):
    """Called when panel value changes (most versatile callback)"""
    print('valueChange', panelvalue.name, panelvalue)
    
    # Handle different panel types
    if panelvalue.panel.panel.type == PanelType.SLIDER:
        handle_slider_change(panelvalue)
    elif panelvalue.panel.panel.type == PanelType.BUTTON:
        handle_button_change(panelvalue)
    elif panelvalue.panel.panel.type == PanelType.FIELD:
        handle_field_change(panelvalue)
    
    return
```

### Advanced Panel Interaction Patterns

```python
def handle_slider_change(panelvalue):
    """Specialized slider handling"""
    value = panelvalue.val
    normalized = value  # Already normalized 0-1
    
    # Map to different ranges
    if panelvalue.name == 'volume_slider':
        # Map to decibel range
        db_value = -60 + (normalized * 60)  # -60dB to 0dB
        set_audio_volume(db_value)
    
    elif panelvalue.name.endswith('_color'):
        # Handle color component sliders
        update_color_component(panelvalue.name, value)

def handle_button_change(panelvalue):
    """Specialized button handling"""
    if panelvalue.val == 1:  # Button pressed
        button_name = panelvalue.name
        
        if button_name.startswith('preset_'):
            # Load preset by name
            preset_id = button_name.replace('preset_', '')
            load_preset(preset_id)
        
        elif button_name == 'randomize':
            randomize_parameters()
        
        elif button_name == 'reset':
            reset_to_defaults()

def track_ui_interaction_patterns():
    """Track user interaction patterns for analysis"""
    interaction_data = me.parent().fetch('ui_interactions', [])
    
    # Store interaction
    interaction_record = {
        'time': absTime.seconds,
        'frame': absTime.frame,
        'panel': panelvalue.name,
        'value': panelvalue.val,
        'panel_type': str(panelvalue.panel.panel.type)
    }
    
    interaction_data.append(interaction_record)
    
    # Keep only last 1000 interactions
    if len(interaction_data) > 1000:
        interaction_data.pop(0)
    
    me.parent().store('ui_interactions', interaction_data)
```

---

## OP Execute

### Operator Lifecycle Monitoring

**Source File**: `opexec2.py`

**Key Concepts**: Operator monitoring, network change detection, lifecycle events

```python
# Global variables available in OP Execute DAT:
# me - this DAT
# changeOp - the operator that has changed

# Make sure the corresponding toggle is enabled in the OP Execute DAT.

def onPreCook(changeOp):
    """Called before operator cooks"""
    print('onPreCook', changeOp)
    
    # Pre-cooking setup or validation
    if hasattr(changeOp, 'par') and hasattr(changeOp.par, 'enable'):
        if not changeOp.par.enable.eval():
            debug(f'{changeOp} is disabled but still cooking')

def onPostCook(changeOp):
    """Called after operator finishes cooking"""
    print('onPostCook', changeOp)
    
    # Performance monitoring
    cook_time = changeOp.cook.prevCookTime
    if cook_time > 0.001:  # Longer than 1ms
        debug(f'{changeOp} cook time: {cook_time:.4f}s')
    
    # Validate outputs
    validate_operator_output(changeOp)

def onDestroy():
    """Called when monitored operator is destroyed"""
    print('onDestroy')
    
    # Cleanup references, notify dependent systems
    cleanup_operator_references()

def onFlagChange(changeOp, flag):
    """Called when operator flag changes (bottom circle buttons)"""
    print('onFlagChange', changeOp, flag)
    
    # Monitor important flag changes
    if flag == 'display' and changeOp.flag.display:
        debug(f'{changeOp} display flag enabled')
    elif flag == 'bypass' and changeOp.flag.bypass:
        debug(f'{changeOp} bypassed')

def onWireChange(changeOp):
    """Called when input wiring changes"""
    print('onWireChange', changeOp)
    
    # Track network topology changes
    log_connection_change(changeOp)
    
    # Validate new connections
    validate_connections(changeOp)

def onNameChange(changeOp):
    """Called when operator name changes"""
    print('onNameChange', changeOp)
    
    # Update name-based references
    update_name_references(changeOp)

def onPathChange(changeOp):
    """Called when operator path changes (name or parent change)"""
    print('onPathChange', changeOp)
    
    # Update path-based references
    update_path_references(changeOp)

def onUIChange(changeOp):
    """Called when operator UI position/size changes"""
    print('onUIChange', changeOp)
    
    # Update layout-dependent systems
    if hasattr(changeOp, 'nodeX'):
        position = (changeOp.nodeX, changeOp.nodeY)
        update_operator_position(changeOp, position)
```

### Network Monitoring Patterns

```python
def validate_operator_output(changeOp):
    """Validate operator outputs after cooking"""
    try:
        if hasattr(changeOp, 'numChans'):  # CHOP
            if changeOp.numChans == 0:
                debug(f'Warning: {changeOp} has no channels')
        
        elif hasattr(changeOp, 'width'):  # TOP
            if changeOp.width == 0 or changeOp.height == 0:
                debug(f'Warning: {changeOp} has zero dimensions')
        
        elif hasattr(changeOp, 'numRows'):  # DAT
            if changeOp.numRows == 0:
                debug(f'Warning: {changeOp} has no data')
    
    except Exception as e:
        debug(f'Error validating {changeOp}: {e}')

def log_connection_change(changeOp):
    """Log network connection changes"""
    connections = []
    
    try:
        for i in range(len(changeOp.inputs)):
            input_op = changeOp.inputs[i]
            if input_op:
                connections.append(f'Input {i}: {input_op.path}')
            else:
                connections.append(f'Input {i}: None')
    
    except Exception as e:
        debug(f'Error logging connections for {changeOp}: {e}')
    
    # Store connection state
    connection_log = me.parent().fetch('connection_log', [])
    connection_log.append({
        'time': absTime.seconds,
        'operator': changeOp.path,
        'connections': connections
    })
    
    me.parent().store('connection_log', connection_log[-100:])  # Keep last 100

def monitor_network_performance():
    """Monitor overall network performance"""
    # Track cook counts and times
    network_stats = {
        'total_cooks': 0,
        'slow_operators': [],
        'error_operators': []
    }
    
    # Analyze recent performance data
    # Implementation depends on specific monitoring needs
    
    return network_stats
```

---

## DAT Execute

### Table Change Monitoring

**Source File**: `datexec1.py`

**Key Concepts**: Table change detection, data monitoring, content validation

```python
# Global variables available in DAT Execute:
# me - this DAT
# dat - the changed DAT
# rows - list of row indices (for specific callbacks)
# cols - list of column indices (for specific callbacks) 
# cells - list of cells that changed content
# prev - list of previous string contents of changed cells

def tableChange(dat):
    """Called when entire table structure changes"""
    print('tableChange', dat)
    
    # Handle major table restructuring
    validate_table_structure(dat)
    notify_table_dependent_systems(dat)
    
    return

def rowChange(dat, rows):
    """Called when specific rows change"""
    print('rowChange', dat, rows)
    
    # Process specific row changes
    for row_index in rows:
        if row_index < dat.numRows:
            process_row_change(dat, row_index)
    
    return

def colChange(dat, cols):
    """Called when specific columns change"""
    print('colChange', dat, cols)
    
    # Process specific column changes
    for col_index in cols:
        if col_index < dat.numCols:
            process_column_change(dat, col_index)
    
    return

def cellChange(dat, cells, prev):
    """Called when specific cells change"""
    print('cellChange', dat, cells, prev)
    
    # Process individual cell changes
    for i, cell in enumerate(cells):
        previous_value = prev[i] if i < len(prev) else ''
        current_value = str(cell)
        
        # Handle cell-specific logic
        if cell.row == 0:  # Header row
            handle_header_change(cell, previous_value)
        else:
            handle_data_cell_change(cell, current_value, previous_value)
    
    return

def sizeChange(dat):
    """Called when table dimensions change (rows/columns added/removed)"""
    print('sizeChange', dat)
    
    # Handle table size changes
    new_size = (dat.numRows, dat.numCols)
    handle_table_resize(dat, new_size)
    
    return
```

### Data Validation and Processing

```python
def validate_table_structure(dat):
    """Validate table structure after changes"""
    if dat.numRows == 0:
        debug(f'Warning: {dat} has no rows')
        return False
    
    if dat.numCols == 0:
        debug(f'Warning: {dat} has no columns') 
        return False
    
    # Check for expected headers
    if dat.numRows > 0:
        header_row = [dat[0, col] for col in range(dat.numCols)]
        expected_headers = get_expected_headers(dat)
        
        if expected_headers and header_row != expected_headers:
            debug(f'Table {dat} headers changed: {header_row}')
    
    return True

def handle_data_cell_change(cell, current_value, previous_value):
    """Handle individual data cell changes"""
    # Type validation
    if cell.col == 0:  # First column might be names
        if not current_value.strip():
            debug(f'Empty name in row {cell.row}')
    
    elif cell.col == 1:  # Second column might be numeric
        try:
            float(current_value)
        except ValueError:
            debug(f'Non-numeric value in numeric column: {current_value}')
    
    # Track changes for undo/audit
    track_cell_change(cell, current_value, previous_value)

def track_cell_change(cell, current, previous):
    """Track cell changes for audit trail"""
    change_log = me.parent().fetch('dat_changes', [])
    
    change_record = {
        'time': absTime.seconds,
        'dat': cell.owner.path,
        'row': cell.row,
        'col': cell.col,
        'current': current,
        'previous': previous
    }
    
    change_log.append(change_record)
    
    # Keep last 500 changes
    if len(change_log) > 500:
        change_log.pop(0)
    
    me.parent().store('dat_changes', change_log)

def process_row_change(dat, row_index):
    """Process changes to specific row"""
    if row_index >= dat.numRows:
        return
    
    # Get entire row data
    row_data = [str(dat[row_index, col]) for col in range(dat.numCols)]
    
    # Process based on table type
    table_type = dat.tags.get('table_type', 'unknown')
    
    if table_type == 'config':
        process_config_row(row_data, row_index)
    elif table_type == 'data':
        process_data_row(row_data, row_index)
```

---

## CHOP Execute

### Channel Data Monitoring

**Source Files**: Various CHOP execute examples

**Key Concepts**: Channel change detection, sample monitoring, channel analysis

```python
# CHOP Execute DAT callbacks for monitoring channel data changes
# Global variables:
# me - this DAT
# channel - the changed channel
# sampleIndex - index of changed sample
# val - new value
# prev - previous value

def onValueChange(channel, sampleIndex, val, prev):
    """Called when channel values change"""
    print(f'Channel {channel.name}[{sampleIndex}] changed: {val} (was: {prev})')
    
    # Handle specific channel types
    if channel.name.startswith('audio'):
        handle_audio_level_change(channel, val)
    elif channel.name.endswith('_pos'):
        handle_position_change(channel, val)
    
def onOffToOn(channel, sampleIndex, val):
    """Called when channel value goes from 0 to non-zero"""
    print(f'Channel {channel.name}[{sampleIndex}] activated: {val}')
    
    # Trigger-like behavior
    if channel.name == 'trigger':
        execute_trigger_action()

def onOnToOff(channel, sampleIndex, prev):
    """Called when channel value goes to 0"""
    print(f'Channel {channel.name}[{sampleIndex}] deactivated (was: {prev})')

def whileOn(channel, sampleIndex, val):
    """Called while channel value is non-zero"""
    # Continuous processing while active
    if channel.name == 'motor_speed':
        update_motor_speed(val)

def whileOff(channel, sampleIndex):
    """Called while channel value is zero"""
    # Usually less commonly needed
    pass
```

---

## Event Patterns

### Event Aggregation and Batching

```python
class EventAggregator:
    """Aggregate and batch events for efficient processing"""
    
    def __init__(self):
        self.pending_events = []
        self.last_process_frame = -1
    
    def add_event(self, event_type, data):
        """Add event to pending queue"""
        event = {
            'type': event_type,
            'data': data,
            'frame': absTime.frame,
            'time': absTime.seconds
        }
        self.pending_events.append(event)
    
    def process_events_if_needed(self):
        """Process events if frame has changed"""
        current_frame = absTime.frame
        if current_frame != self.last_process_frame and self.pending_events:
            self.process_pending_events()
            self.last_process_frame = current_frame
    
    def process_pending_events(self):
        """Process all pending events efficiently"""
        # Group events by type
        by_type = {}
        for event in self.pending_events:
            event_type = event['type']
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(event)
        
        # Process each type in batch
        for event_type, events in by_type.items():
            self.process_event_batch(event_type, events)
        
        # Clear processed events
        self.pending_events.clear()

# Global event aggregator instance
if not hasattr(parent(), '_event_aggregator'):
    parent().store('_event_aggregator', EventAggregator())

aggregator = parent().fetch('_event_aggregator')

# Use in Execute DAT callbacks:
def onValueChange(par, prev):
    aggregator.add_event('parameter_change', {
        'parameter': par.name,
        'value': par.eval(),
        'previous': prev,
        'operator': par.owner.path
    })
    aggregator.process_events_if_needed()
```

### State Machine Patterns

```python
class ComponentStateMachine:
    """State machine for component behavior"""
    
    def __init__(self):
        self.state = 'idle'
        self.state_handlers = {
            'idle': self.handle_idle_state,
            'processing': self.handle_processing_state,
            'error': self.handle_error_state
        }
    
    def transition_to(self, new_state, context=None):
        """Transition to new state"""
        if new_state in self.state_handlers:
            debug(f'State transition: {self.state} -> {new_state}')
            
            # Exit current state
            exit_method = getattr(self, f'exit_{self.state}', None)
            if exit_method:
                exit_method()
            
            # Enter new state  
            self.state = new_state
            enter_method = getattr(self, f'enter_{new_state}', None)
            if enter_method:
                enter_method(context)
    
    def handle_event(self, event_type, data):
        """Handle events based on current state"""
        handler = self.state_handlers.get(self.state)
        if handler:
            handler(event_type, data)
    
    def handle_idle_state(self, event_type, data):
        """Handle events in idle state"""
        if event_type == 'start_processing':
            self.transition_to('processing', data)
    
    def handle_processing_state(self, event_type, data):
        """Handle events in processing state"""
        if event_type == 'processing_complete':
            self.transition_to('idle')
        elif event_type == 'error':
            self.transition_to('error', data)
    
    def handle_error_state(self, event_type, data):
        """Handle events in error state"""
        if event_type == 'reset':
            self.transition_to('idle')
```

---

## Performance Tips

### Efficient Execute DAT Patterns

```python
# Avoid expensive operations in frequent callbacks
def onFrameStart(frame):
    """Efficient frame processing"""
    
    # Use frame-based throttling
    if frame % 30 != 0:  # Only every 30 frames
        return
    
    # Cache expensive lookups
    if not hasattr(me.parent(), '_cached_operators'):
        me.parent().store('_cached_operators', find_all_relevant_operators())
    
    operators = me.parent().fetch('_cached_operators')
    process_operators_efficiently(operators)

def onValueChange(par, prev):
    """Efficient parameter change handling"""
    
    # Early return for uninteresting changes
    if abs(par.eval() - prev) < 0.001:  # Negligible change
        return
    
    # Batch similar parameter changes
    if not hasattr(me.parent(), '_parameter_batch'):
        me.parent().store('parameter_batch', [])
    
    batch = me.parent().fetch('parameter_batch')
    batch.append((par, par.eval(), prev))
    
    # Process batch at frame end
    run("process_parameter_batch()", delayFrames=1)

# Memory management for long-running Execute DATs
def cleanup_old_data():
    """Regular cleanup of accumulated data"""
    current_time = absTime.seconds
    
    # Clean parameter history older than 5 minutes
    for key in list(me.parent().storage.keys()):
        if key.startswith('param_history_'):
            history = me.parent().fetch(key, [])
            # Filter out old entries
            recent = [entry for entry in history 
                     if current_time - entry.get('time', 0) < 300]
            if len(recent) != len(history):
                me.parent().store(key, recent)

# Call cleanup periodically
def onFrameStart(frame):
    if frame % 1800 == 0:  # Every 30 seconds at 60fps
        cleanup_old_data()
```

### Debugging Execute DATs

```python
# Debug utilities for Execute DATs
def debug_execute_state():
    """Debug information about Execute DAT state"""
    debug(f'Execute DAT: {me.path}')
    debug(f'Parent: {me.parent().path}')
    debug(f'Current frame: {absTime.frame}')
    debug(f'Storage keys: {list(me.parent().storage.keys())}')

def log_callback_frequency():
    """Monitor callback frequency for performance analysis"""
    callback_counts = me.parent().fetch('callback_counts', {})
    callback_name = 'unknown'  # Set this in each callback
    
    callback_counts[callback_name] = callback_counts.get(callback_name, 0) + 1
    me.parent().store('callback_counts', callback_counts)
    
    # Log summary every 1000 calls
    total_calls = sum(callback_counts.values())
    if total_calls % 1000 == 0:
        debug(f'Callback frequency: {callback_counts}')
```

---

## Cross-References

### Related Documentation

- **[CLASS_Execute_Classes.md](../CLASSES_/CLASS_Execute_Classes.md)** - Execute DAT class references
- **[PY_CallbacksExtExtension.md](../PYTHON_/PY_CallbacksExtExtension.md)** - Callback system overview
- **[PY_Working_with_Execute_DATs.md](../PYTHON_/PY_Working_with_Execute_DATs.md)** - Execute DAT concepts

### Related Examples  

- **[EX_CALLBACKS.md](./EX_CALLBACKS.md)** - General callback patterns
- **[EX_EXTENSIONS.md](./EX_EXTENSIONS.md)** - Extension callback integration
- **[EX_PARAMETERS.md](./EX_PARAMETERS.md)** - Parameter manipulation patterns

### Execute DAT Operators

- **Execute DAT** - General frame-based execution
- **Parameter Execute DAT** - Parameter change monitoring
- **Panel Execute DAT** - UI interaction callbacks
- **OP Execute DAT** - Operator lifecycle monitoring
- **DAT Execute DAT** - Table change monitoring
- **CHOP Execute DAT** - Channel data monitoring

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/Execute_DATs/`

**Key Files**:

- `execute1.py` - Basic Execute DAT callbacks
- `parexec1.py` - Parameter Execute patterns  
- `panelexec1.py` - Panel Execute callbacks
- `opexec2.py` - OP Execute monitoring
- `datexec1.py` - DAT Execute table monitoring
- `chopexec1.dat` - CHOP Execute channel monitoring

**Total Examples**: 26 files covering all aspects of event-driven programming and monitoring in TouchDesigner.

---

*These examples provide the foundation for reactive, event-driven TouchDesigner networks. Use them to create responsive systems that react efficiently to user input, data changes, and system events.*
