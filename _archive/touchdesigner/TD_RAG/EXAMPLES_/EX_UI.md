---
title: "User Interface Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "20-30 minutes"
user_personas: ["ui_developer", "interactive_designer", "script_developer"]
operators: ["scriptDAT", "executeDAT", "buttonCOMP", "sliderCOMP", "panelCOMP"]
concepts: ["user_interface", "dialogs", "file_selection", "pane_management", "status_updates", "color_picker"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "UI_concepts"]
workflows: ["interface_development", "user_interaction", "dialog_systems"]
keywords: ["ui", "dialog", "messageBox", "chooseFile", "panes", "status", "interface"]
tags: ["python", "ui", "interface", "dialogs", "user_interaction", "examples"]
related_docs: ["CLASS_UI_Class", "EX_PANELS", "CLASS_panelCOMP_Class", "PY_TD_Python_Examples_Reference"]
example_count: 15
---

# TouchDesigner Python Examples: User Interface

## Quick Reference

TouchDesigner's `ui` module provides comprehensive interface control for dialogs, windows, panes, file operations, and user interaction. This category covers 15 essential patterns for creating professional user interfaces and dialog systems.

**Key UI Functions:**

- `ui.messageBox()` - Custom dialog boxes
- `ui.chooseFile()` - File selection dialogs
- `ui.openDialog()` - System dialog access
- `ui.status` - Status bar management
- `ui.colors` - Color picker integration
- `ui.panes` - Pane management
- `ui.options` - User preferences

**Core Capabilities:**

- System dialog integration
- Custom message boxes with buttons
- File and folder selection
- Color picker workflows
- Pane and window management
- Status updates and notifications

---

## Message Box System

### Basic Message Boxes

```python
# Simple notification
ui.messageBox('Warning', 'Operation completed successfully.')

# Information dialog
ui.messageBox('Info', 'TouchDesigner is ready for operation.')

# Error notification
ui.messageBox('Error', 'Failed to load component. Check file path.')
```

### Interactive Message Boxes

```python
# Custom button selection
result = ui.messageBox('Please select:', 'Choose an option:', 
                      buttons=['Option A', 'Option B', 'Cancel'])
print(f"User selected: {result}")

# Yes/No dialog
confirm = ui.messageBox('Confirm', 'Delete this component?', 
                       buttons=['Yes', 'No'])
if confirm == 0:  # Yes selected
    # Perform deletion
    pass
```

### Dynamic Content Message Boxes

```python
# List nodes for selection
nodes = me.parent().children
selected_node = ui.messageBox('Select Node:', 'Available nodes:', 
                              buttons=nodes)
if selected_node is not None:
    target_node = nodes[selected_node]
    print(f"Selected: {target_node.name}")

# Node name selection (cleaner display)
node_names = [x.name for x in me.parent().children]
selected_index = ui.messageBox('Select by Name:', 'Node names:', 
                               buttons=node_names)

# Table cell selection
table_cells = op('table1').cells('*', '*')
selected_cell = ui.messageBox('Select Cell:', 'Available cells:', 
                              buttons=table_cells)
```

---

## File and Folder Dialogs

### File Selection

```python
# Single file selection
selected_file = ui.chooseFile(load=True, 
                             start='C:/Projects', 
                             fileTypes=['mov', 'mp4', 'avi'])
if selected_file:
    print(f"Selected: {selected_file}")
    # Load the file
    op('moviefilein1').par.file = selected_file

# Multiple file selection
multiple_files = ui.chooseFile(load=True, 
                              multipleFiles=True,
                              fileTypes=['jpg', 'png', 'tiff'])
for file_path in multiple_files:
    print(f"File: {file_path}")
```

### Folder Selection

```python
# Choose folder for export
export_folder = ui.chooseFolder(start='C:/Exports', 
                               title='Select Export Directory')
if export_folder:
    print(f"Export to: {export_folder}")
    # Set export path
    op('exporter').par.folder = export_folder
```

### Save File Dialogs

```python
# Save with specific extension
save_path = ui.chooseFile(load=False, 
                         fileTypes=['tox'], 
                         title='Save Component As...')
if save_path:
    # Save component
    comp.save(save_path)
    ui.messageBox('Success', f'Component saved to: {save_path}')
```

---

## Color Picker Integration

### Basic Color Selection

```python
# Simple color picker
selected_color = ui.chooseColor()
if selected_color:
    r, g, b, a = selected_color
    print(f"Color: R={r:.3f}, G={g:.3f}, B={b:.3f}, A={a:.3f}")
    
    # Apply to material
    mat = op('mat1')
    mat.par.diffr = r
    mat.par.diffg = g
    mat.par.diffb = b
```

### Color with Default Value

```python
# Start with current color
current_color = (op('constant1').par.colorr.eval(),
                op('constant1').par.colorg.eval(),
                op('constant1').par.colorb.eval(),
                1.0)

new_color = ui.chooseColor(initial=current_color)
if new_color:
    # Update constant TOP
    op('constant1').par.colorr = new_color[0]
    op('constant1').par.colorg = new_color[1]
    op('constant1').par.colorb = new_color[2]
```

---

## System Dialog Access

### TouchDesigner Dialog Windows

```python
# Open common TouchDesigner windows
ui.openExplorer()           # Network explorer
ui.openTextport()           # Textport console
ui.openPerformanceMonitor() # Performance monitoring
ui.openPaletteBrowser()     # Palette browser
ui.openPreferences()        # TouchDesigner preferences

# Developer tools
ui.openConsole()           # Python console
ui.openErrors()            # Error dialog
ui.openHelp()              # Help browser
ui.openSearch()            # Search dialog
```

### Specialized Windows

```python
# Import/Export dialogs
ui.openImportFile()        # File import dialog
ui.openExportMovie()       # Movie export settings
ui.openCHOPExporter()      # CHOP export utility

# System utilities
ui.openMIDIDeviceMapper()  # MIDI device configuration
ui.openKeyManager()        # License key management
ui.openVersion()           # Version information
ui.openBeat()              # Beat analyzer
```

---

## Status Bar and Notifications

### Status Updates

```python
# Basic status message
ui.status = "Processing network analysis..."

# Progress indication
for i in range(100):
    ui.status = f"Progress: {i}% complete"
    # Perform work here
    time.sleep(0.1)

ui.status = "Analysis complete"
```

### Temporary Status Messages

```python
def temporaryStatus(message, duration=2.0):
    """Display temporary status message"""
    original_status = ui.status
    ui.status = message
    
    # Use run to restore after delay
    run(f"ui.status = '{original_status}'", delayFrames=int(duration * project.cookRate))
```

---

## Pane and Window Management

### Pane Information

```python
# Get information about current panes
pane_count = len(ui.panes)
print(f"Active panes: {pane_count}")

# Pane details
for i, pane in enumerate(ui.panes):
    print(f"Pane {i}:")
    print(f"  Type: {pane.type}")
    print(f"  Name: {pane.name}")
    print(f"  Owner: {pane.owner}")
```

### Pane Operations

```python
# Focus specific pane
if ui.panes:
    target_pane = ui.panes[0]
    target_pane.setFocus()
    
    # Change pane content
    if hasattr(target_pane, 'owner'):
        target_pane.owner = op('/project1')
```

---

## Advanced Patterns

### Confirmation Dialog System

```python
class ConfirmationSystem:
    """Professional confirmation dialog system"""
    
    @staticmethod
    def confirmAction(action_name, details="", destructive=False):
        """Show confirmation with appropriate styling"""
        title = f"Confirm {action_name}"
        
        if destructive:
            title = f"⚠️ {title}"
            buttons = ['Delete', 'Cancel']
        else:
            buttons = ['Continue', 'Cancel']
        
        message = f"{details}\n\nThis action cannot be undone." if destructive else details
        
        result = ui.messageBox(title, message, buttons=buttons)
        return result == 0  # True if confirmed
    
    @staticmethod
    def confirmDelete(item_name):
        """Specialized delete confirmation"""
        return ConfirmationSystem.confirmAction(
            "Delete", 
            f"Delete '{item_name}'?",
            destructive=True
        )
```

### Progressive File Operations

```python
def batchFileProcessor():
    """Batch file processing with UI feedback"""
    # Select multiple files
    files = ui.chooseFile(load=True, 
                         multipleFiles=True,
                         title="Select files to process")
    
    if not files:
        ui.messageBox('Cancelled', 'No files selected.')
        return
    
    # Confirm operation
    confirm = ui.messageBox('Confirm Batch Process', 
                           f'Process {len(files)} files?',
                           buttons=['Process', 'Cancel'])
    
    if confirm != 0:
        return
    
    # Process with progress
    for i, file_path in enumerate(files):
        progress = int((i / len(files)) * 100)
        ui.status = f"Processing: {progress}% ({i+1}/{len(files)})"
        
        # Process file here
        process_file(file_path)
    
    ui.status = f"Completed processing {len(files)} files"
    ui.messageBox('Complete', f'Successfully processed {len(files)} files.')
```

### Dynamic UI Builder

```python
class DynamicUIBuilder:
    """Build dynamic UI elements based on data"""
    
    def __init__(self):
        self.current_options = []
    
    def buildSelectionDialog(self, title, items, display_func=None):
        """Build selection dialog from data"""
        if not display_func:
            display_func = lambda x: str(x)
        
        display_items = [display_func(item) for item in items]
        
        result = ui.messageBox(title, 
                              'Select an option:', 
                              buttons=display_items)
        
        if result is not None and 0 <= result < len(items):
            return items[result]
        return None
    
    def buildOperatorSelector(self, op_types=None):
        """Build operator selection from network"""
        candidates = []
        
        for child in me.parent().children:
            if op_types is None or child.type in op_types:
                candidates.append(child)
        
        if not candidates:
            ui.messageBox('No Options', 'No matching operators found.')
            return None
        
        return self.buildSelectionDialog(
            'Select Operator',
            candidates,
            display_func=lambda op: f"{op.name} ({op.type})"
        )
```

---

## Cross-References

**Related Documentation:**

- [EX_PANELS](./EX_PANELS.md) - Panel component patterns
- [EX_EXECUTE_DATS](./EX_EXECUTE_DATS.md) - Panel execute callbacks
- [EX_CALLBACKS](./EX_CALLBACKS.md) - UI event handling
- [CLASSES_/CLASS_ui](../CLASSES_/CLASS_ui.md) - ui module reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Best Practices:**

- Always provide meaningful dialog titles and messages
- Use appropriate button labels (not just OK/Cancel)
- Handle dialog cancellation gracefully
- Provide progress feedback for long operations
- Use temporary status messages for quick feedback

---

## File References

**Source Files (15 total):**

- `UI__Text__test_dialogs__td.txt` - System dialog access patterns
- `UI__Text__test_messageBox__td.txt` - Message box implementation
- `UI__Text__test_choosefiles__td.txt` - File selection dialogs
- `UI__Text__test_colors__td.txt` - Color picker integration
- `UI__Text__test_options__td.txt` - Option handling patterns
- `UI__Text__test_panes__td.txt` - Pane management
- `UI__Text__test_status__td.txt` - Status bar operations
- `UI__Text__text4_callbacks__td.py` - UI callback integration
- `UI__Table__table1__td.tsv` - UI data tables
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation integration (3 files)
- `open_wiki__*__td.*` - Wiki integration (2 files)

**Dialog Categories:**

- **System Dialogs**: TouchDesigner built-in windows and tools
- **File Operations**: File/folder selection and save dialogs
- **User Interaction**: Message boxes and confirmation dialogs
- **Color Selection**: Color picker workflows
- **Status Management**: Progress and notification systems

---

*This documentation covers TouchDesigner's comprehensive UI system for creating professional user interfaces with proper dialog handling, file operations, and user feedback systems.*
