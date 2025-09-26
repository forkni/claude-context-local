---
title: "Parameters Examples"
category: EXAMPLES
document_type: examples
difficulty: beginner
time_estimate: "20-30 minutes"
user_personas: ["script_developer", "beginner_programmer", "technical_artist"]
operators: ["all_operators", "constantCHOP", "transformTOP", "geometryCOMP"]
concepts: ["parameter_access", "expressions", "parameter_types", "value_assignment", "menus", "pulses"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "parameter_concepts"]
workflows: ["operator_control", "dynamic_parameters", "automation"]
keywords: ["parameters", "par", "expr", "menu", "pulse", "toggle", "value", "assignment"]
tags: ["python", "parameters", "par", "expressions", "control", "fundamentals", "examples"]
related_docs: ["CLASS_Par_Class", "CLASS_OP_Class", "EX_OPS", "PY_TD_Python_Examples_Reference"]
example_count: 13
---

# TouchDesigner Python Examples: Parameters

## Quick Reference

TouchDesigner parameters are the primary interface for controlling operator behavior through Python. This category covers 13 essential patterns for parameter access, manipulation, expression handling, and type-specific operations including menus, pulses, and toggles.

**Key Parameter Types:**

- **Number** - Numeric values (int, float)
- **String** - Text values and file paths  
- **OP** - Operator references
- **Menu** - Dropdown selections
- **Toggle** - Boolean on/off states
- **Pulse** - Momentary trigger actions

**Core Operations:**

- Parameter value access and assignment
- Expression management
- Type-specific parameter handling
- Menu manipulation
- Pulse triggering

---

## Basic Parameter Access

### Parameter Object Access

```python
# Get operator and parameter objects
target_op = op('geo1')

# Get parameter object (not value)
rotation_param = target_op.par.ry  # Parameter object
print(f"Parameter: {rotation_param}")
print(f"Owner: {rotation_param.owner}")
print(f"Name: {rotation_param.name}")
print(f"Label: {rotation_param.label}")
print(f"Index: {rotation_param.index}")
print(f"Vector Index: {rotation_param.vecIndex}")
print(f"Expression: {rotation_param.expr}")

# Evaluate parameter to get current value
current_value = rotation_param.eval()
print(f"Current value: {current_value}")
```

### Parameter Value Assignment

```python
# Direct value assignment
target_op.par.tx.val = 1.2          # Set translation X
# target_op.par.tx = 1.2            # Equivalent shorthand

# Expression assignment
target_op.par.rx.expr = 'me.time.frame'  # Set expression

# Operator reference assignment
target_op.par.lookat.val = op('null2')   # Set OP parameter
# target_op.par.lookat = op('null2')      # Equivalent shorthand
```

### Parameter Type Detection

```python
def analyzeParameters(target_op):
    """Analyze all parameters by type"""
    param_analysis = {
        'ops': [],
        'toggles': [],
        'strings': [],
        'pulses': [],
        'menus': [],
        'numbers': []
    }
    
    for param in target_op.pars():
        param_info = {
            'name': param.name,
            'value': param.eval(),
            'type': type(param.eval()).__name__
        }
        
        if param.isOP:
            param_analysis['ops'].append(param_info)
        elif param.isToggle:
            param_analysis['toggles'].append(param_info)
        elif param.isString:
            param_analysis['strings'].append(param_info)
        elif param.isPulse:
            param_analysis['pulses'].append(param_info)
        elif param.isMenu:
            param_analysis['menus'].append(param_info)
        elif param.isNumber:
            param_analysis['numbers'].append(param_info)
    
    return param_analysis

# Usage and reporting
def reportParameters(target_op):
    """Generate parameter type report"""
    analysis = analyzeParameters(target_op)
    
    print(f"Parameter Analysis for {target_op.name}:")
    
    for param_type, params in analysis.items():
        if params:
            print(f"  {param_type.title()} ({len(params)}):")
            for param in params[:3]:  # Show first 3 of each type
                print(f"    {param['name']}: {param['value']} ({param['type']})")
            if len(params) > 3:
                print(f"    ... and {len(params) - 3} more")

# Generate report
reportParameters(op('geo1'))
```

---

## Menu Parameters

### Menu Value Manipulation

```python
# Menu parameter control
target_op = op('creep1')

# Set menu by name (string value)
target_op.par.resetmethod = 'fillpath'
print(f"Menu set to: {target_op.par.resetmethod.eval()}")

# Set menu by index (numeric position)  
target_op.par.resetmethod.menuIndex = 1
print(f"Menu index set to: {target_op.par.resetmethod.menuIndex}")

# Get menu options
menu_param = target_op.par.resetmethod
if hasattr(menu_param, 'menuNames'):
    menu_options = menu_param.menuNames
    print(f"Menu options: {menu_options}")

if hasattr(menu_param, 'menuLabels'):
    menu_labels = menu_param.menuLabels
    print(f"Menu labels: {menu_labels}")
```

### Dynamic Menu Management

```python
class MenuManager:
    """Professional menu parameter management"""
    
    def __init__(self, target_op):
        self.target_op = target_op
    
    def setMenuByName(self, param_name, menu_value):
        """Set menu parameter by name"""
        try:
            param = getattr(self.target_op.par, param_name)
            if param.isMenu:
                param.val = menu_value
                return True
            else:
                print(f"Parameter {param_name} is not a menu")
                return False
        except AttributeError:
            print(f"Parameter {param_name} not found")
            return False
    
    def setMenuByIndex(self, param_name, menu_index):
        """Set menu parameter by index"""
        try:
            param = getattr(self.target_op.par, param_name)
            if param.isMenu:
                param.menuIndex = menu_index
                return True
            else:
                print(f"Parameter {param_name} is not a menu")
                return False
        except AttributeError:
            print(f"Parameter {param_name} not found")
            return False
    
    def getMenuOptions(self, param_name):
        """Get available menu options"""
        try:
            param = getattr(self.target_op.par, param_name)
            if param.isMenu:
                return {
                    'names': param.menuNames if hasattr(param, 'menuNames') else [],
                    'labels': param.menuLabels if hasattr(param, 'menuLabels') else [],
                    'current_index': param.menuIndex if hasattr(param, 'menuIndex') else -1,
                    'current_value': param.eval()
                }
        except AttributeError:
            pass
        return None
    
    def cycleMenu(self, param_name):
        """Cycle to next menu option"""
        options = self.getMenuOptions(param_name)
        if options and options['names']:
            current_index = options['current_index']
            next_index = (current_index + 1) % len(options['names'])
            return self.setMenuByIndex(param_name, next_index)
        return False

# Usage
menu_manager = MenuManager(op('math1'))
menu_manager.setMenuByName('combine', 'multiply')
options = menu_manager.getMenuOptions('combine')
print(f"Menu options: {options}")
menu_manager.cycleMenu('combine')
```

---

## Pulse Parameters

### Basic Pulse Operations

```python
# Pulse parameter triggering
target_op = op('creep1')
reset_param = target_op.par.reset

# Trigger pulse
reset_param.pulse()
print("Reset pulse triggered")

# Pulse with conditional logic
def conditionalReset(condition):
    """Pulse reset only if condition is met"""
    if condition:
        target_op.par.reset.pulse()
        print("Conditional reset triggered")
    else:
        print("Reset condition not met")

# Usage
conditionalReset(absTime.frame % 60 == 0)  # Reset every 60 frames
```

### Advanced Pulse Management

```python
class PulseManager:
    """Manage pulse parameters with timing control"""
    
    def __init__(self):
        self.pulse_history = {}
    
    def pulseWithDelay(self, target_op, param_name, delay_frames=0):
        """Trigger pulse with frame delay"""
        if delay_frames <= 0:
            # Immediate pulse
            param = getattr(target_op.par, param_name)
            if param.isPulse:
                param.pulse()
                self.recordPulse(target_op, param_name)
                return True
        else:
            # Delayed pulse using run()
            command = f"op('{target_op.path}').par.{param_name}.pulse()"
            run(command, delayFrames=delay_frames)
            return True
        
        return False
    
    def recordPulse(self, target_op, param_name):
        """Record pulse in history"""
        key = f"{target_op.path}.{param_name}"
        self.pulse_history[key] = {
            'frame': absTime.frame,
            'time': absTime.seconds
        }
    
    def getLastPulseTime(self, target_op, param_name):
        """Get last pulse time for parameter"""
        key = f"{target_op.path}.{param_name}"
        return self.pulse_history.get(key, None)
    
    def pulseSequence(self, pulse_list, interval_frames=10):
        """Trigger sequence of pulses with intervals"""
        for i, (target_op, param_name) in enumerate(pulse_list):
            delay = i * interval_frames
            self.pulseWithDelay(target_op, param_name, delay)
        
        print(f"Scheduled {len(pulse_list)} pulses with {interval_frames} frame intervals")

# Usage
pulse_manager = PulseManager()

# Single delayed pulse
pulse_manager.pulseWithDelay(op('constant1'), 'reset', delay_frames=30)

# Pulse sequence
pulse_sequence = [
    (op('noise1'), 'resetseed'),
    (op('noise2'), 'resetseed'),
    (op('constant1'), 'reset')
]
pulse_manager.pulseSequence(pulse_sequence, interval_frames=15)
```

---

## Expression Management

### Expression Assignment and Evaluation

```python
# Expression handling
target_op = op('transform1')

# Set expressions
target_op.par.tx.expr = 'sin(me.time.seconds * 2)'
target_op.par.ty.expr = 'cos(me.time.seconds * 2)'
target_op.par.rz.expr = 'me.time.frame * 0.5'

# Clear expressions (set to evaluated value)
def clearExpression(param):
    """Clear expression and set to current evaluated value"""
    current_value = param.eval()
    param.expr = ''  # Clear expression
    param.val = current_value  # Set to evaluated value
    print(f"Cleared expression for {param.name}, set to {current_value}")

# Usage
clearExpression(target_op.par.tx)

# Expression validation
def validateExpression(param, test_expr):
    """Test if expression is valid before setting"""
    original_expr = param.expr
    original_val = param.val
    
    try:
        # Test the expression
        param.expr = test_expr
        test_value = param.eval()
        print(f"Expression '{test_expr}' is valid, evaluates to: {test_value}")
        return True
        
    except Exception as e:
        print(f"Expression '{test_expr}' is invalid: {e}")
        # Restore original values
        param.expr = original_expr
        param.val = original_val
        return False

# Test expressions
validateExpression(target_op.par.sx, 'absTime.frame / 100')
validateExpression(target_op.par.sy, 'invalid_function()')
```

---

## Parameter Animation and Keyframes

### Keyframe Management

```python
def animateParameter(param, keyframes):
    """Set up parameter animation with keyframes"""
    # Clear existing animation
    param.expr = ''
    
    # Set keyframes (simplified approach using expressions)
    if len(keyframes) == 2:
        # Linear interpolation between two points
        start_frame, start_val = keyframes[0]
        end_frame, end_val = keyframes[1]
        
        # Create linear interpolation expression
        expr = f"fit(absTime.frame, {start_frame}, {end_frame}, {start_val}, {end_val})"
        param.expr = expr
        print(f"Set linear animation: {expr}")
    
    elif len(keyframes) > 2:
        # More complex keyframe animation would typically use CHOP or Animation COMP
        print(f"Complex keyframe animation with {len(keyframes)} points")
        # This would require more sophisticated implementation

def createAnimationCurve(target_op, param_name, keyframes):
    """Create animation curve using Animation COMP"""
    # Create animation component (simplified)
    anim_comp = me.parent().create(animationCOMP, f'{target_op.name}_{param_name}_anim')
    
    # Configure animation (would require specific Animation COMP setup)
    # This is a placeholder for more complex animation setup
    print(f"Created animation component for {target_op.name}.{param_name}")
    
    return anim_comp

# Usage examples
rotation_keyframes = [
    (0, 0),      # Frame 0, value 0
    (60, 360),   # Frame 60, value 360
]

animateParameter(op('transform1').par.rz, rotation_keyframes)
```

---

## Advanced Parameter Patterns

### Parameter State Management

```python
class ParameterStateManager:
    """Save and restore parameter states"""
    
    def __init__(self):
        self.saved_states = {}
    
    def saveParameterState(self, target_op, state_name=None):
        """Save current state of all parameters"""
        if state_name is None:
            state_name = f"state_{absTime.frame}"
        
        param_state = {}
        for param in target_op.pars():
            param_state[param.name] = {
                'value': param.eval(),
                'expression': param.expr,
                'type': param.style
            }
        
        key = f"{target_op.path}_{state_name}"
        self.saved_states[key] = param_state
        print(f"Saved parameter state '{state_name}' for {target_op.name}")
        
        return state_name
    
    def restoreParameterState(self, target_op, state_name):
        """Restore saved parameter state"""
        key = f"{target_op.path}_{state_name}"
        
        if key not in self.saved_states:
            print(f"State '{state_name}' not found for {target_op.name}")
            return False
        
        param_state = self.saved_states[key]
        
        for param_name, param_data in param_state.items():
            try:
                param = getattr(target_op.par, param_name)
                
                # Restore expression if it exists
                if param_data['expression']:
                    param.expr = param_data['expression']
                else:
                    param.expr = ''
                    param.val = param_data['value']
                    
            except AttributeError:
                print(f"Parameter {param_name} no longer exists")
        
        print(f"Restored parameter state '{state_name}' for {target_op.name}")
        return True
    
    def listSavedStates(self, target_op):
        """List all saved states for operator"""
        prefix = f"{target_op.path}_"
        states = [key[len(prefix):] for key in self.saved_states.keys() if key.startswith(prefix)]
        return states

# Usage
param_manager = ParameterStateManager()

# Save current state
state_name = param_manager.saveParameterState(op('transform1'), 'initial_setup')

# Modify parameters
op('transform1').par.tx = 2.0
op('transform1').par.ry.expr = 'absTime.frame'

# Restore previous state
param_manager.restoreParameterState(op('transform1'), 'initial_setup')

# List saved states
states = param_manager.listSavedStates(op('transform1'))
print(f"Saved states: {states}")
```

### Parameter Validation System

```python
def createParameterValidator():
    """Create parameter validation system"""
    
    validators = {}
    
    def addValidator(op_path, param_name, validation_func, fix_func=None):
        """Add parameter validator"""
        key = f"{op_path}.{param_name}"
        validators[key] = {
            'validate': validation_func,
            'fix': fix_func
        }
    
    def validateParameter(target_op, param_name):
        """Validate single parameter"""
        key = f"{target_op.path}.{param_name}"
        
        if key not in validators:
            return True, "No validator found"
        
        validator = validators[key]
        param = getattr(target_op.par, param_name, None)
        
        if not param:
            return False, "Parameter not found"
        
        is_valid, message = validator['validate'](param)
        
        if not is_valid and validator['fix']:
            # Attempt to fix
            try:
                validator['fix'](param)
                return True, "Fixed automatically"
            except Exception as e:
                return False, f"Fix failed: {e}"
        
        return is_valid, message
    
    def validateAllParameters(target_op):
        """Validate all parameters for operator"""
        results = {}
        
        for param in target_op.pars():
            is_valid, message = validateParameter(target_op, param.name)
            if not is_valid:
                results[param.name] = message
        
        return results
    
    return {
        'addValidator': addValidator,
        'validateParameter': validateParameter,
        'validateAll': validateAllParameters
    }

# Usage
validator = createParameterValidator()

# Add validators
validator['addValidator'](
    '/project1/transform1', 'sx',
    lambda p: (p.eval() > 0, "Scale must be positive"),
    lambda p: setattr(p, 'val', abs(p.eval()))
)

# Validate parameters
is_valid, message = validator['validateParameter'](op('transform1'), 'sx')
print(f"Validation result: {is_valid}, {message}")
```

---

## Cross-References

**Related Documentation:**

- [EX_OPS](./EX_OPS.md) - General operator operations
- [EX_EXECUTE_DATS](./EX_EXECUTE_DATS.md) - Parameter execute callbacks
- [EX_UI](./EX_UI.md) - UI parameter integration
- [CLASSES_/CLASS_Par](../CLASSES_/CLASS_Par.md) - Parameter class reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Best Practices:**

- Use parameter objects (.par.name) for inspection, .val or direct assignment for values
- Validate expressions before setting to avoid runtime errors  
- Use appropriate parameter types (isMenu, isPulse, etc.) for type-specific operations
- Consider parameter state management for complex configurations
- Handle missing parameters gracefully with try/catch blocks

---

## File References

**Source Files (13 total):**

- `Parameters__Text__test_Par__td.txt` - Basic parameter access and type detection
- `Parameters__Text__test_menu__td.txt` - Menu parameter manipulation
- `Parameters__Text__test_pulse__td.txt` - Pulse parameter triggering
- `Parameters__Text__text2_callbacks__td.py` - Parameter callback integration
- `Parameters__Text__text3_callbacks__td.py` - Advanced callback patterns
- `Parameters__Text__text4_callbacks__td.py` - General callback integration
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)
- `open_wiki__*Execute__*__td.py` - Wiki integration (2 files)

**Parameter Categories:**

- **Basic Access**: Parameter object access, value assignment, type detection
- **Menu Parameters**: Dropdown menu manipulation by name and index
- **Pulse Parameters**: Trigger actions and pulse management
- **Expressions**: Expression assignment, validation, and animation
- **State Management**: Parameter saving, restoration, and validation

---

*This documentation covers TouchDesigner's comprehensive parameter system for controlling operator behavior through Python, providing essential patterns for value manipulation, expressions, and type-specific operations.*
