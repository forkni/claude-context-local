---
title: "Panel Components Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "25-35 minutes"
user_personas: ["ui_developer", "interactive_designer", "technical_artist"]
operators: ["buttonCOMP", "sliderCOMP", "fieldCOMP", "tableCOMP", "containerCOMP", "panelCOMP"]
concepts: ["panel_components", "ui_controls", "focus_management", "keyboard_interaction", "color_systems", "event_handling"]
prerequisites: ["Python_fundamentals", "TouchDesigner_UI", "panel_basics"]
workflows: ["interface_development", "user_interaction", "control_systems"]
keywords: ["panel", "button", "slider", "field", "table", "ui", "focus", "color"]
tags: ["python", "ui", "panels", "interface", "controls", "interaction", "examples"]
related_docs: ["CLASS_panelCOMP_Class", "EX_UI", "EX_CALLBACKS", "CLASS_buttonCOMP_Class"]
example_count: 15
---

# TouchDesigner Python Examples: Panel Components

## Quick Reference

TouchDesigner panel components provide interactive UI elements with comprehensive Python control. This category covers 15 essential patterns for panel value access, focus management, keyboard interaction, color systems, and UI component styling.

**Key Panel Types:**

- **Button** - Interactive buttons with states
- **Field** - Text input with validation
- **Table** - Data tables with cell interaction
- **Slider** - Value controls with ranges
- **Container** - UI organization and grouping

**Core Panel Operations:**

- Panel value access and manipulation
- Focus and keyboard management
- Color and styling systems
- Event simulation and testing
- Table cell operations and attributes

---

## Panel Value Access

### Reading Panel Values

```python
# Basic value access
button = op('button3')
u_value = button.panel.u.val        # Returns float
radio_name = button.panel.radioname.val  # Returns string

# Direct access with autocasting
u_float = float(button.panel.u)     # Explicit cast
combined = button.panel.u + button.panel.v  # Auto arithmetic cast

# Value object attributes
u_obj = button.panel.u
print(f"Value: {u_obj.val}, Name: {u_obj.name}, Owner: {u_obj.owner}")
```

### Setting Panel Values

```python
# Direct value assignment
button.panel.u = 0.1               # Set numeric value
button.panel.v = 0.5
button.panel.radioname = "option1"  # Set string value

# Programmatic button states
button.panel.state = 1             # Press button
button.panel.state = 0             # Release button

# Range-based values
slider = op('slider1')
slider.panel.u = 0.75              # Set to 75% of range
```

### Advanced Value Operations

```python
def syncPanelValues(source_panel, target_panel, value_names):
    """Sync panel values between components"""
    for value_name in value_names:
        if hasattr(source_panel, value_name) and hasattr(target_panel, value_name):
            source_val = getattr(source_panel, value_name).val
            setattr(target_panel, value_name, source_val)

# Usage
syncPanelValues(op('button1').panel, op('button2').panel, ['u', 'v', 'state'])
```

---

## Focus Management

### Basic Focus Control

```python
# Set hierarchical focus
field = op('container2/field2')
field.setFocus()                   # Focus without mouse movement
field.setFocus(moveMouse=True)     # Move mouse to component

# Keyboard focus with text selection
field.setKeyboardFocus()           # Basic keyboard focus
field.setKeyboardFocus(selectAll=True)  # Select all field text
```

### Advanced Focus Management

```python
class FocusManager:
    """Professional focus management system"""
    
    def __init__(self):
        self.focus_history = []
        self.current_focus = None
    
    def setFocusWithHistory(self, target_op, select_text=False):
        """Set focus and maintain history"""
        if self.current_focus:
            self.focus_history.append(self.current_focus)
        
        self.current_focus = target_op
        
        if hasattr(target_op, 'setKeyboardFocus'):
            target_op.setKeyboardFocus(selectAll=select_text)
        else:
            target_op.setFocus(moveMouse=True)
    
    def returnToPreviousFocus(self):
        """Return to previous focus in history"""
        if self.focus_history:
            previous = self.focus_history.pop()
            self.current_focus = previous
            previous.setFocus()
    
    def clearFocusHistory(self):
        """Clear focus history"""
        self.focus_history.clear()
        self.current_focus = None

# Global focus manager instance
focus_manager = FocusManager()
```

### Focus Chain Management

```python
def createFocusChain(components):
    """Create tab-order focus chain"""
    for i, comp in enumerate(components):
        # Store next component reference
        comp.store('focus_next', components[(i + 1) % len(components)])
        comp.store('focus_prev', components[i - 1])

def focusNext(current_comp):
    """Move to next component in focus chain"""
    next_comp = current_comp.fetch('focus_next', None)
    if next_comp:
        next_comp.setKeyboardFocus()

def focusPrevious(current_comp):
    """Move to previous component in focus chain"""
    prev_comp = current_comp.fetch('focus_prev', None)
    if prev_comp:
        prev_comp.setKeyboardFocus()
```

---

## Keyboard and Mouse Simulation

### Click Simulation

```python
# Simulate mouse clicks on components
button = op('button1')

# Basic click simulation
button.click()                     # Single click
button.click(x=0.5, y=0.5)        # Click at center
button.click(x=0.1, y=0.9, force=True)  # Force click

# Multi-click patterns
def doubleClick(component, delay_frames=5):
    """Simulate double-click"""
    component.click()
    run(f"op('{component.path}').click()", delayFrames=delay_frames)

# Drag simulation
def simulateDrag(component, start_pos, end_pos):
    """Simulate drag operation"""
    sx, sy = start_pos
    ex, ey = end_pos
    
    # Start drag
    component.clickDrag(sx, sy, ex, ey)
```

### Keyboard Input Simulation

```python
def simulateKeyInput(field_op, text, clear_first=True):
    """Simulate keyboard input to field"""
    if clear_first:
        field_op.setKeyboardFocus(selectAll=True)
    
    # Simulate typing
    for char in text:
        field_op.type(char)
    
    # Simulate Enter key
    field_op.type('\n')

def simulateKeyboardShortcut(target_op, key_combination):
    """Simulate keyboard shortcuts"""
    # Focus target first
    target_op.setKeyboardFocus()
    
    # Send key combination
    if '+' in key_combination:
        # Handle modifier keys (Ctrl+C, Alt+F4, etc.)
        keys = key_combination.split('+')
        modifiers = keys[:-1]
        main_key = keys[-1]
        
        # Implementation depends on TD's keyboard API
        target_op.sendKeys(main_key, modifiers=modifiers)
    else:
        target_op.sendKeys(key_combination)
```

---

## Panel Color Systems

### Color Table Integration

```python
# Panel color system using color tables
def setupPanelColors(panel_op, color_table):
    """Setup panel colors from color table"""
    panel_op.par.colortable = color_table
    
    # Color states
    panel_op.par.bgcolorr = color_table[0, 0]  # Background red
    panel_op.par.bgcolorg = color_table[0, 1]  # Background green
    panel_op.par.bgcolorb = color_table[0, 2]  # Background blue

def createColorTheme(base_color, variations=5):
    """Create color theme variations"""
    r, g, b = base_color
    theme_table = []
    
    for i in range(variations):
        factor = 0.5 + (i * 0.5 / variations)  # 0.5 to 1.0
        theme_color = (r * factor, g * factor, b * factor)
        theme_table.append(theme_color)
    
    return theme_table

# Apply theme to button states
def applyButtonTheme(button_op, theme_colors):
    """Apply color theme to button states"""
    if len(theme_colors) >= 3:
        # Normal, rollover, select states
        button_op.par.bgcolorr = theme_colors[0][0]
        button_op.par.rollovercolorr = theme_colors[1][0]
        button_op.par.selectcolorr = theme_colors[2][0]
        # ... apply g, b components similarly
```

---

## Table Panel Patterns

### Table Cell Operations

```python
# Table cell access and manipulation
table = op('table3')

# Cell attribute access
def getCellAttributes(table_op, row, col):
    """Get comprehensive cell attributes"""
    cell = table_op[row, col]
    return {
        'value': cell.val,
        'string': str(cell),
        'row': cell.row,
        'col': cell.col,
        'owner': cell.owner
    }

# Cell styling and attributes
def setCellStyle(table_op, row, col, color=None, text_color=None):
    """Set cell visual attributes"""
    cell_attr_table = table_op.par.cellattributes.eval()
    if cell_attr_table:
        # Set cell background color
        if color:
            cell_attr_table[row, f'bgcolorr_{col}'] = color[0]
            cell_attr_table[row, f'bgcolorg_{col}'] = color[1] 
            cell_attr_table[row, f'bgcolorb_{col}'] = color[2]
```

### Table Selection and Interaction

```python
class TableManager:
    """Professional table management system"""
    
    def __init__(self, table_op):
        self.table = table_op
        self.selection = set()
    
    def selectCell(self, row, col):
        """Select individual cell"""
        self.selection.add((row, col))
        self.updateSelection()
    
    def selectRange(self, start_row, start_col, end_row, end_col):
        """Select range of cells"""
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                self.selection.add((r, c))
        self.updateSelection()
    
    def clearSelection(self):
        """Clear all selection"""
        self.selection.clear()
        self.updateSelection()
    
    def updateSelection(self):
        """Update visual selection state"""
        # Update select table or cell attributes
        select_table = self.table.par.selecttable.eval()
        if select_table:
            # Clear previous selection
            select_table.clear()
            # Apply current selection
            for row, col in self.selection:
                select_table[row, col] = 1
```

---

## Advanced Panel Patterns

### Panel State Management

```python
class PanelStateManager:
    """Manage panel states with persistence"""
    
    def __init__(self, owner_comp):
        self.owner = owner_comp
        self.states = {}
    
    def saveState(self, panel_op, state_name):
        """Save current panel state"""
        state = {}
        
        # Save common panel values
        for attr in ['u', 'v', 'w', 'h', 'state', 'radioname']:
            if hasattr(panel_op.panel, attr):
                state[attr] = getattr(panel_op.panel, attr).val
        
        self.states[state_name] = state
        
        # Persist to component storage
        self.owner.store(f'panel_state_{state_name}', state)
    
    def restoreState(self, panel_op, state_name):
        """Restore panel state"""
        state = self.states.get(state_name)
        if not state:
            state = self.owner.fetch(f'panel_state_{state_name}', {})
        
        for attr, value in state.items():
            if hasattr(panel_op.panel, attr):
                setattr(panel_op.panel, attr, value)
    
    def listStates(self):
        """List available states"""
        return list(self.states.keys())

# Usage
state_manager = PanelStateManager(me)
state_manager.saveState(op('button1'), 'initial')
state_manager.restoreState(op('button1'), 'initial')
```

### Panel Validation System

```python
def createPanelValidator():
    """Create comprehensive panel validation system"""
    
    validators = {}
    
    def addValidator(panel_name, validation_func, error_message):
        """Add validator for specific panel"""
        validators[panel_name] = {
            'func': validation_func,
            'message': error_message
        }
    
    def validatePanel(panel_op):
        """Validate single panel"""
        panel_name = panel_op.name
        if panel_name in validators:
            validator = validators[panel_name]
            if not validator['func'](panel_op):
                return False, validator['message']
        return True, "Valid"
    
    def validateAllPanels(parent_op):
        """Validate all panels in component"""
        results = {}
        for child in parent_op.children:
            if hasattr(child, 'panel'):
                valid, message = validatePanel(child)
                results[child.name] = {'valid': valid, 'message': message}
        return results
    
    return {
        'addValidator': addValidator,
        'validatePanel': validatePanel,
        'validateAllPanels': validateAllPanels
    }

# Usage
validator = createPanelValidator()
validator['addValidator']('field1', 
                         lambda p: len(str(p.panel.string.val)) > 0,
                         "Field cannot be empty")
```

---

## Cross-References

**Related Documentation:**

- [EX_UI](./EX_UI.md) - User interface patterns
- [EX_EXECUTE_DATS](./EX_EXECUTE_DATS.md) - Panel execute callbacks
- [EX_CALLBACKS](./EX_CALLBACKS.md) - Panel event handling
- [CLASSES_/CLASS_Panel](../CLASSES_/CLASS_Panel.md) - Panel class reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Performance Notes:**

- Panel value access is optimized for frequent queries
- Focus operations should be used sparingly in performance-critical code
- Color table updates can be batched for better performance
- Table operations scale with table size - consider pagination for large datasets

---

## File References

**Source Files (15 total):**

- `Panels__Text__test_panel_values__td.txt` - Panel value access patterns
- `Panels__Text__test_keyboard_focus__td.txt` - Focus management
- `Panels__Text__test_keyboard_focus2__td.txt` - Advanced focus patterns
- `Panels__Text__test_simulate_clicks__td.txt` - Click simulation
- `Panels__Text__text1_callbacks__td.py` - Panel callback integration
- `Panels__Text__text4_callbacks__td.py` - Text field callbacks
- `button*__Table__color__td.tsv` - Button color tables (3 files)
- `field*__*__*.dat/tsv` - Field component data (9 files)
- `table3__*__*.dat/tsv` - Table component system (12 files)
- `annotation__*__td.*` - Annotation integration (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)

**Panel Types Covered:**

- **Buttons**: Interactive button states and color systems
- **Fields**: Text input with focus and validation
- **Tables**: Data tables with cell operations and styling
- **Containers**: UI organization and hierarchy
- **General**: Focus management and event simulation

---

*This documentation covers TouchDesigner's comprehensive panel system for building interactive user interfaces with proper state management, focus control, and visual styling.*
