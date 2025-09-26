---
title: "Undo System Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "tool_developer", "technical_artist"]
operators: ["scriptDAT", "executeDAT", "buttonCOMP"]
concepts: ["undo_system", "history_management", "undo_blocks", "operation_control", "state_management"]
prerequisites: ["Python_fundamentals", "TouchDesigner_UI", "state_management_concepts"]
workflows: ["tool_development", "user_interface", "operation_management"]
keywords: ["undo", "redo", "history", "block", "state", "operation", "management"]
tags: ["python", "undo", "history", "state", "management", "ui", "examples"]
related_docs: ["CLASS_UI_Class", "CLASS_Undo_Class", "EX_UI", "PY_TD_Python_Examples_Reference"]
example_count: 15
---

# TouchDesigner Python Examples: Undo System

## Quick Reference

TouchDesigner's undo system provides comprehensive history management for Python operations. This category covers 15 essential patterns for undo/redo operations, undo blocking, callback integration, and data management within the undo framework.

**Key Undo Functions:**

- `ui.undo.undo()` - Perform undo operation  
- `ui.undo.redo()` - Perform redo operation
- `ui.undo.startBlock()` - Begin undo block
- `ui.undo.endBlock()` - End undo block
- Callback integration for undo events

**Core Operations:**

- Manual undo/redo control
- Undo block creation for multiple operations
- Undo prevention for specific operations
- Callback-driven undo handling
- Data preservation in undo states

---

## Basic Undo Operations

### Manual Undo and Redo

```python
# Basic undo operation
ui.undo.undo()  # Equivalent to Ctrl-Z or Edit > Undo

# Basic redo operation  
ui.undo.redo()  # Equivalent to Ctrl-Y or Edit > Redo

# Check undo availability
if ui.undo.canUndo():
    print("Undo is available")
    ui.undo.undo()
else:
    print("Nothing to undo")

# Check redo availability
if ui.undo.canRedo():
    print("Redo is available")  
    ui.undo.redo()
else:
    print("Nothing to redo")
```

### Undo State Information

```python
def getUndoState():
    """Get current undo system state"""
    return {
        'can_undo': ui.undo.canUndo(),
        'can_redo': ui.undo.canRedo(),
        'undo_description': ui.undo.undoDescription(),
        'redo_description': ui.undo.redoDescription(),
        'undo_count': len(ui.undo.undoStack) if hasattr(ui.undo, 'undoStack') else 0
    }

# Usage
undo_state = getUndoState()
print(f"Undo available: {undo_state['can_undo']}")
print(f"Next undo: {undo_state['undo_description']}")
print(f"Next redo: {undo_state['redo_description']}")
```

---

## Undo Blocks

### Basic Undo Block Usage

```python
# Create undo block for multiple operations
# All operations within the block become a single undo step
ui.undo.startBlock('Move and Scale Operation')

# Multiple operations that will be grouped
op('constant1').nodeY -= 50           # Move node
op('constant1').par.value0 += 10      # Change parameter
op('constant1').color = (1, 0, 0)     # Change color

# End the undo block
ui.undo.endBlock()

# Now pressing undo will reverse all three operations at once
```

### Advanced Undo Block Management

```python
class UndoBlockManager:
    """Professional undo block management with error handling"""
    
    def __init__(self):
        self.active_blocks = []
    
    def startBlock(self, name):
        """Start undo block with error handling"""
        try:
            ui.undo.startBlock(name)
            self.active_blocks.append(name)
            print(f"Started undo block: {name}")
            return True
        except Exception as e:
            print(f"Failed to start undo block '{name}': {e}")
            return False
    
    def endBlock(self):
        """End undo block with validation"""
        if not self.active_blocks:
            print("Warning: No active undo block to end")
            return False
        
        try:
            ui.undo.endBlock()
            block_name = self.active_blocks.pop()
            print(f"Ended undo block: {block_name}")
            return True
        except Exception as e:
            print(f"Failed to end undo block: {e}")
            return False
    
    def executeWithUndo(self, operations, block_name):
        """Execute operations within undo block"""
        if self.startBlock(block_name):
            try:
                # Execute all operations
                for operation in operations:
                    operation()
                
                return self.endBlock()
            except Exception as e:
                print(f"Error during undo block execution: {e}")
                # Attempt to end block even on error
                self.endBlock()
                return False
        return False

# Usage example
undo_manager = UndoBlockManager()

def move_operations():
    """Example operations to group in undo block"""
    op('noise1').nodeX += 100
    op('noise1').nodeY += 50
    op('noise1').par.freq = 2.5

operations = [move_operations]
undo_manager.executeWithUndo(operations, 'Adjust Noise Settings')
```

### Nested Undo Block Handling

```python
def complexOperation():
    """Complex operation with nested undo blocks"""
    ui.undo.startBlock('Complex Network Changes')
    
    try:
        # Phase 1: Create operators
        ui.undo.startBlock('Create Operators')
        new_noise = me.parent().create(noiseTOP, 'procedural_noise')
        new_math = me.parent().create(mathTOP, 'math_processor')
        ui.undo.endBlock()
        
        # Phase 2: Configure parameters
        ui.undo.startBlock('Configure Parameters')
        new_noise.par.freq = 4.0
        new_noise.par.amp = 0.8
        new_math.par.combine = 'multiply'
        ui.undo.endBlock()
        
        # Phase 3: Connect network
        ui.undo.startBlock('Connect Network')
        new_math.inputConnectors[0].connect(new_noise)
        ui.undo.endBlock()
        
    except Exception as e:
        print(f"Error in complex operation: {e}")
        raise
    finally:
        ui.undo.endBlock()  # End main block

# Execute complex operation
complexOperation()
```

---

## Undo Prevention

### Operations Without Undo

```python
# Some Python operations cannot be undone automatically
# These operations will not appear in undo history

def nonUndoableOperations():
    """Operations that cannot be undone without undo blocks"""
    # Node position changes via Python
    op('constant1').nodeX -= 50
    
    # Parameter changes via Python
    op('constant1').par.value0 += 1
    
    # These changes are permanent unless wrapped in undo blocks
    print("Operations completed - cannot undo without undo blocks")

# Execute non-undoable operations
nonUndoableOperations()
print("Try pressing Ctrl-Z - these changes won't be undone")
```

### Selective Undo Prevention  

```python
def preventUndoForOperation(operation_func):
    """Execute operation without adding to undo history"""
    # Save current undo state
    undo_enabled = ui.undo.enabled
    
    try:
        # Disable undo for this operation
        ui.undo.enabled = False
        operation_func()
        
    finally:
        # Restore undo state
        ui.undo.enabled = undo_enabled

def temporaryChange():
    """Temporary change that shouldn't be undoable"""
    op('constant1').par.value0 = 999  # Temporary debug value

# Execute without undo
preventUndoForOperation(temporaryChange)
print("Temporary change made - not undoable")
```

---

## Undo Callbacks

### Undo Event Callbacks

```python
# Undo callback integration
def onUndoEvent(event_type):
    """Handle undo system events"""
    if event_type == 'undo':
        print("Undo operation performed")
        # Update UI or state as needed
        updateUIAfterUndo()
        
    elif event_type == 'redo':
        print("Redo operation performed")
        # Update UI or state as needed  
        updateUIAfterRedo()
        
    elif event_type == 'block_start':
        print("Undo block started")
        
    elif event_type == 'block_end':
        print("Undo block ended")

def updateUIAfterUndo():
    """Update UI elements after undo"""
    # Refresh displays, update status, etc.
    ui.status = "Undo performed"

def updateUIAfterRedo():
    """Update UI elements after redo"""  
    # Refresh displays, update status, etc.
    ui.status = "Redo performed"
```

### Callback-Driven Undo System

```python
class UndoCallbackManager:
    """Manage undo callbacks and state synchronization"""
    
    def __init__(self):
        self.callbacks = {
            'pre_undo': [],
            'post_undo': [],
            'pre_redo': [],
            'post_redo': []
        }
    
    def registerCallback(self, event_type, callback_func):
        """Register callback for undo events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback_func)
    
    def executeUndo(self):
        """Execute undo with callbacks"""
        # Pre-undo callbacks
        for callback in self.callbacks['pre_undo']:
            try:
                callback()
            except Exception as e:
                print(f"Pre-undo callback error: {e}")
        
        # Perform undo
        if ui.undo.canUndo():
            ui.undo.undo()
            
            # Post-undo callbacks
            for callback in self.callbacks['post_undo']:
                try:
                    callback()
                except Exception as e:
                    print(f"Post-undo callback error: {e}")
    
    def executeRedo(self):
        """Execute redo with callbacks"""
        # Pre-redo callbacks
        for callback in self.callbacks['pre_redo']:
            try:
                callback()
            except Exception as e:
                print(f"Pre-redo callback error: {e}")
        
        # Perform redo
        if ui.undo.canRedo():
            ui.undo.redo()
            
            # Post-redo callbacks
            for callback in self.callbacks['post_redo']:
                try:
                    callback()
                except Exception as e:
                    print(f"Post-redo callback error: {e}")

# Usage
undo_callback_manager = UndoCallbackManager()

def refreshViewer():
    """Refresh viewer after undo/redo"""
    print("Refreshing viewer after undo/redo")

def logUndoAction():
    """Log undo actions"""
    print(f"Undo action at frame {absTime.frame}")

# Register callbacks
undo_callback_manager.registerCallback('post_undo', refreshViewer)
undo_callback_manager.registerCallback('post_undo', logUndoAction)
undo_callback_manager.registerCallback('post_redo', refreshViewer)
```

---

## Data Management with Undo

### Python Data Preservation

```python
# Custom data management that integrates with undo system
class UndoableDataManager:
    """Manage Python data with undo support"""
    
    def __init__(self, owner_comp):
        self.owner = owner_comp
        self.data_key = 'undoable_data'
        self.history_key = 'data_history'
    
    def saveState(self, data, description="Data Update"):
        """Save data state with undo support"""
        # Get current history
        history = self.owner.fetch(self.history_key, [])
        
        # Add current state to history
        current_state = {
            'data': data,
            'description': description,
            'frame': absTime.frame,
            'timestamp': absTime.seconds
        }
        
        history.append(current_state)
        
        # Limit history size
        max_history = 50
        if len(history) > max_history:
            history = history[-max_history:]
        
        # Store updated history
        self.owner.store(self.history_key, history)
        self.owner.store(self.data_key, data)
    
    def undoData(self):
        """Undo to previous data state"""
        history = self.owner.fetch(self.history_key, [])
        
        if len(history) > 1:
            # Remove current state
            history.pop()
            
            # Get previous state
            previous_state = history[-1]
            
            # Restore data
            self.owner.store(self.data_key, previous_state['data'])
            self.owner.store(self.history_key, history)
            
            print(f"Undid: {previous_state['description']}")
            return previous_state['data']
        else:
            print("No previous state to undo to")
            return None
    
    def getCurrentData(self):
        """Get current data"""
        return self.owner.fetch(self.data_key, None)
    
    def getDataHistory(self):
        """Get data history for debugging"""
        return self.owner.fetch(self.history_key, [])

# Usage
data_manager = UndoableDataManager(me)

# Save data states
data_manager.saveState({'values': [1, 2, 3]}, "Initial values")
data_manager.saveState({'values': [4, 5, 6]}, "Updated values")
data_manager.saveState({'values': [7, 8, 9]}, "Final values")

# Undo data changes
previous_data = data_manager.undoData()
print(f"Restored data: {previous_data}")
```

---

## Advanced Patterns

### Undo Integration with UI

```python
def createUndoUI():
    """Create UI integration for undo system"""
    
    def updateUndoButtons():
        """Update undo/redo button states"""
        # Enable/disable undo button
        undo_button = op('undo_button')
        if undo_button:
            undo_button.par.enable = ui.undo.canUndo()
            undo_button.text = ui.undo.undoDescription() if ui.undo.canUndo() else "Undo"
        
        # Enable/disable redo button
        redo_button = op('redo_button')  
        if redo_button:
            redo_button.par.enable = ui.undo.canRedo()
            redo_button.text = ui.undo.redoDescription() if ui.undo.canRedo() else "Redo"
    
    def onUndoButton():
        """Handle undo button press"""
        if ui.undo.canUndo():
            ui.undo.undo()
            updateUndoButtons()
            ui.status = f"Undid: {ui.undo.redoDescription()}"
    
    def onRedoButton():
        """Handle redo button press"""
        if ui.undo.canRedo():
            ui.undo.redo()
            updateUndoButtons()
            ui.status = f"Redid: {ui.undo.undoDescription()}"
    
    # Update buttons initially
    updateUndoButtons()
    
    return {
        'updateButtons': updateUndoButtons,
        'onUndo': onUndoButton,
        'onRedo': onRedoButton
    }

# Create UI integration
undo_ui = createUndoUI()
```

### Batch Operations with Smart Undo

```python
def performBatchWithUndo(operations, batch_name="Batch Operation"):
    """Perform batch operations with intelligent undo grouping"""
    
    if not operations:
        return
    
    # Start undo block for batch
    ui.undo.startBlock(batch_name)
    
    try:
        success_count = 0
        error_count = 0
        
        for i, operation in enumerate(operations):
            try:
                # Execute operation
                if callable(operation):
                    operation()
                else:
                    # Assume operation is a tuple (function, args)
                    func, args = operation
                    func(*args)
                
                success_count += 1
                
            except Exception as e:
                print(f"Error in operation {i}: {e}")
                error_count += 1
        
        print(f"Batch completed: {success_count} succeeded, {error_count} failed")
        
    finally:
        ui.undo.endBlock()

# Usage example
def create_noise_chain():
    """Create a chain of noise operators"""
    parent_comp = me.parent()
    
    operations = [
        lambda: parent_comp.create(noiseTOP, 'noise_1'),
        lambda: parent_comp.create(noiseTOP, 'noise_2'), 
        lambda: parent_comp.create(mathTOP, 'noise_math'),
        lambda: op('noise_1').par.freq.set(2.0),
        lambda: op('noise_2').par.freq.set(4.0),
        lambda: op('noise_math').inputConnectors[0].connect(op('noise_1')),
        lambda: op('noise_math').inputConnectors[1].connect(op('noise_2'))
    ]
    
    performBatchWithUndo(operations, "Create Noise Chain")

# Execute batch operation
create_noise_chain()
```

---

## Cross-References

**Related Documentation:**

- [EX_OPS](./EX_OPS.md) - General operator operations
- [EX_UI](./EX_UI.md) - User interface integration
- [EX_CALLBACKS](./EX_CALLBACKS.md) - Callback patterns
- [CLASSES_/CLASS_ui_undo](../CLASSES_/CLASS_ui_undo.md) - Undo system reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Best Practices:**

- Always use undo blocks for multi-step Python operations
- Provide descriptive names for undo blocks
- Handle errors gracefully within undo blocks
- Use callbacks to maintain UI consistency after undo/redo
- Consider performance impact of large undo histories

---

## File References

**Source Files (15 total):**

- `Undo__Text__test_undo__td.py` - Basic undo operation
- `Undo__Text__test_redo__td.py` - Basic redo operation
- `Undo__Text__test_undo_block__td.py` - Undo block creation and management
- `Undo__Text__test_no_undo__td.py` - Non-undoable operations
- `Undo__Text__test_no_undo_callback__td.py` - Undo prevention with callbacks
- `Undo__Text__test_undo_callback__td.py` - Undo callback integration
- `Undo__Text__python_data__td.py` - Python data management with undo
- `Undo__Text__text4_callbacks__td.py` - General callback integration
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)
- `open_wiki__*Execute__*__td.py` - Wiki integration (2 files)

**Undo Categories:**

- **Basic Operations**: Manual undo/redo control
- **Undo Blocks**: Multi-operation grouping
- **Prevention**: Selective undo prevention
- **Callbacks**: Event-driven undo handling
- **Data Management**: Python data preservation in undo system

---

*This documentation covers TouchDesigner's undo system for managing operation history, providing essential patterns for undo blocks, callbacks, and data management within the undo framework.*
