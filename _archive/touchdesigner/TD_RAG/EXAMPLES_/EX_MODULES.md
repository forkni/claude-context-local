---
title: "Module System Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "20-30 minutes"
user_personas: ["script_developer", "system_architect", "technical_artist"]
operators: ["textDAT", "scriptDAT", "tableDAT"]
concepts: ["module_system", "code_organization", "imports", "dependencies", "utilities", "reusability"]
prerequisites: ["Python_fundamentals", "TouchDesigner_Python_API", "object_oriented_programming"]
workflows: ["code_organization", "system_architecture", "library_development"]
keywords: ["modules", "import", "dependencies", "utilities", "organization", "reusable"]
tags: ["python", "modules", "import", "architecture", "utilities", "examples"]
related_docs: ["MODULE_td", "PY_Extensions", "EX_EXTENSIONS", "PY_TD_Python_Examples_Reference"]
example_count: 19
---

# TouchDesigner Python Examples: Module Tutorials

## Overview

Comprehensive examples for TouchDesigner's module system, demonstrating how to organize code, import libraries, create reusable functions, and manage dependencies. TouchDesigner's module system combines standard Python importing with unique features like DAT-based modules and the module-on-demand system.

**Source**: TouchDesigner Help > Python Examples > Modules  
**Example Count**: 19 files  
**Focus**: Code organization, imports, reusable utilities, dependency management

## Quick Reference

### Core Module Concepts

- **[Python Standard Libraries](#python-standard-libraries)** - Using Python built-in and 3rd party modules
- **[TouchDesigner Built-ins](#touchdesigner-built-ins)** - Built-in TD objects and helpers
- **[DAT Modules](#dat-modules)** - Using DATs as importable modules
- **[Module-on-Demand](#module-on-demand)** - Dynamic module access with mod object

### Organization Patterns  

- **[Local Module System](#local-module-system)** - /local/modules for network-wide access
- **[Utility Libraries](#utility-libraries)** - Creating reusable function libraries
- **[Module Best Practices](#module-best-practices)** - Patterns for maintainable code
- **[Dependency Management](#dependency-management)** - Managing module dependencies

---

## Python Standard Libraries

### Standard and 3rd Party Imports

**Source File**: `test_imports.py`

**Key Concepts**: Standard Python libraries, 3rd party packages, TouchDesigner libraries

```python
# Standard Python library imports
import time
print('time', time.asctime((0,0,0,0,0,0,0,0,0)))

# Get current time
current_time = time.time()
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print(f'Current time: {formatted_time}')

# Time utilities
def wait_seconds(seconds):
    """Wait for specified number of seconds"""
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass  # Busy wait (not recommended for long waits)

# 3rd party library (NumPy)
import numpy
print('1/15', numpy.reciprocal(15.0))

# NumPy operations
def process_array_data(data_list):
    """Process list data using NumPy"""
    arr = numpy.array(data_list)
    
    # Statistical operations
    stats = {
        'mean': numpy.mean(arr),
        'std': numpy.std(arr),
        'min': numpy.min(arr),
        'max': numpy.max(arr)
    }
    
    # Normalize data to 0-1 range
    normalized = (arr - numpy.min(arr)) / (numpy.max(arr) - numpy.min(arr))
    
    return stats, normalized.tolist()

# TouchDesigner specific library
import TDFunctions
print('shortcut', TDFunctions.getShortcutPath(me, op('/project1')))

# TDFunctions utilities
def create_tdf_property_wrapper(component, name, default_value):
    """Wrapper for creating TDF properties with validation"""
    try:
        TDFunctions.createProperty(component, name=name, value=default_value)
        return True
    except Exception as e:
        debug(f'Failed to create property {name}: {e}')
        return False

# Other commonly used imports
import os
import sys
import json
import math
import random

def demonstrate_standard_libraries():
    """Demonstrate common standard library usage"""
    
    # OS operations
    current_dir = os.getcwd()
    print(f'Current directory: {current_dir}')
    
    # System information
    print(f'Python version: {sys.version}')
    print(f'Platform: {sys.platform}')
    
    # JSON operations
    data = {'name': 'TouchDesigner', 'version': '2023', 'active': True}
    json_string = json.dumps(data, indent=2)
    print(f'JSON data: {json_string}')
    
    # Math operations
    angle_degrees = 45
    angle_radians = math.radians(angle_degrees)
    sin_value = math.sin(angle_radians)
    print(f'sin({angle_degrees}°) = {sin_value:.4f}')
    
    # Random operations
    random_float = random.uniform(0.0, 1.0)
    random_int = random.randint(1, 100)
    print(f'Random values: {random_float:.4f}, {random_int}')

# Call demonstration
demonstrate_standard_libraries()
```

### Advanced Import Patterns

```python
# Conditional imports
try:
    import scipy
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    debug('SciPy not available - some features disabled')

def advanced_processing(data):
    """Use SciPy if available, fallback otherwise"""
    if SCIPY_AVAILABLE:
        return scipy_advanced_processing(data)
    else:
        return basic_processing(data)

# Import specific functions
from math import sin, cos, tan, pi
from random import choice, shuffle
from json import loads, dumps

def optimized_imports_example():
    """Using specific imports for cleaner code"""
    angle = pi / 4  # No need for math.pi
    result = sin(angle)  # No need for math.sin
    
    options = ['A', 'B', 'C', 'D']
    selected = choice(options)  # No need for random.choice
    
    return result, selected

# Aliased imports for convenience
import numpy as np
import TDFunctions as tdf

def aliased_imports_example():
    """Using import aliases"""
    data = np.array([1, 2, 3, 4, 5])
    mean_value = np.mean(data)
    
    tdf.createProperty(me.parent(), name='MeanValue', value=mean_value)
    
    return mean_value
```

---

## TouchDesigner Built-ins

### Built-in TD Objects and Helpers

**Source File**: `test_builtins.py`

**Key Concepts**: TD module objects, automatically available helpers, operator families

```python
# TouchDesigner objects are built-in through the td module
# (automatically imported in all TouchDesigner Python contexts)

# Operator families and classes
print(DAT)       # DAT operator family
print(textDAT)   # Specific operator class
print(CHOP)      # CHOP operator family
print(mathCHOP)  # Specific CHOP class
print(TOP)       # TOP operator family
print(moviefileinTOP)  # Specific TOP class

# Built-in helpers and globals
print('frame', absTime.frame)    # Global time helper
print('seconds', absTime.seconds)  # Time in seconds

# Always available standard modules
print('pow', math.pow(2, 5))    # math module always available
print(sys.version)              # sys module always available

# Other built-in TouchDesigner objects
print('project name:', project.name)
print('project folder:', project.folder)
print('cook rate:', project.cookRate)

def demonstrate_builtin_objects():
    """Demonstrate built-in TouchDesigner objects"""
    
    # Time and frame information
    current_frame = absTime.frame
    current_seconds = absTime.seconds
    frame_rate = project.cookRate
    
    print(f'Frame: {current_frame}, Time: {current_seconds:.3f}s, Rate: {frame_rate}fps')
    
    # UI information
    print(f'UI width: {ui.width}, height: {ui.height}')
    print(f'Mouse position: ({ui.mouseX}, {ui.mouseY})')
    
    # Monitor information
    for i, monitor in enumerate(monitors):
        print(f'Monitor {i}: {monitor.width}x{monitor.height} at ({monitor.left}, {monitor.top})')
    
    # License information
    print(f'TouchDesigner license: {licenses.pro}')
    
    return {
        'frame': current_frame,
        'seconds': current_seconds,
        'frame_rate': frame_rate
    }

def create_operators_using_builtins():
    """Create operators using built-in classes"""
    container = me.parent()
    
    # Create operators using built-in classes
    text_dat = container.create(textDAT, 'created_text')
    text_dat.text = 'Created from built-in class'
    
    math_chop = container.create(mathCHOP, 'created_math')
    math_chop.par.func = 'sin'
    math_chop.par.range1 = 0
    math_chop.par.range2 = 360
    
    noise_top = container.create(noiseTOP, 'created_noise')
    noise_top.par.seed = int(absTime.seconds * 100) % 1000
    
    return [text_dat, math_chop, noise_top]

# Additional built-in objects and functions
def explore_more_builtins():
    """Explore additional built-in TouchDesigner objects"""
    
    # Root project access
    print(f'Root path: {root.path}')
    
    # Variable system
    var('myVar', 42)  # Set variable
    my_value = var('myVar')  # Get variable
    print(f'Variable value: {my_value}')
    
    # TDU (TouchDesigner Utilities)
    path_result = tdu.collapsePath('/project1/geo1/../base1')
    print(f'Collapsed path: {path_result}')
    
    # Debug function
    debug('This is a debug message with built-in debug()')
    
    return my_value
```

### Working with Built-in Operator Types

```python
def operator_type_utilities():
    """Utilities for working with operator types"""
    
    # Check operator types
    def get_operator_info(op_ref):
        """Get detailed information about an operator"""
        if not op_ref:
            return None
        
        info = {
            'name': op_ref.name,
            'path': op_ref.path,
            'family': str(op_ref.family),
            'type': str(op_ref.type),
            'valid': op_ref.valid
        }
        
        # Family-specific information
        if op_ref.family == DAT:
            info['numRows'] = op_ref.numRows if hasattr(op_ref, 'numRows') else 0
            info['numCols'] = op_ref.numCols if hasattr(op_ref, 'numCols') else 0
        
        elif op_ref.family == CHOP:
            info['numChans'] = op_ref.numChans if hasattr(op_ref, 'numChans') else 0
            info['numSamples'] = op_ref.numSamples if hasattr(op_ref, 'numSamples') else 0
        
        elif op_ref.family == TOP:
            info['width'] = op_ref.width if hasattr(op_ref, 'width') else 0
            info['height'] = op_ref.height if hasattr(op_ref, 'height') else 0
        
        return info
    
    # Create operators by type
    def create_operator_by_family(container, family, name):
        """Create appropriate operator based on family"""
        if family == DAT:
            return container.create(textDAT, name)
        elif family == CHOP:
            return container.create(mathCHOP, name)
        elif family == TOP:
            return container.create(noiseTOP, name)
        elif family == SOP:
            return container.create(boxSOP, name)
        elif family == COMP:
            return container.create(containerCOMP, name)
        elif family == MAT:
            return container.create(phongMAT, name)
        
        return None
    
    return get_operator_info, create_operator_by_family
```

---

## DAT Modules

### Using DATs as Importable Modules

**Source File**: `test_dat_modules.py`

**Key Concepts**: DAT imports, module functions, help documentation

```python
# You can import any DAT in the same network as a module
import utils_a as a

# Access module help and functions
help(a)
print('----------------------------------')
help(a.myadd)
print(a.myadd(1, 3))

import utils_b as b
print(b.myadd(2, 4))
print('----------------------------------')

# Example utility DAT (utils_a):
"""
def myadd(x, y):
    \"\"\"help for myadd\"\"\"
    return 10000*x + y

def mysub(x, y):
    \"\"\"help for mysub\"\"\"
    return -(10000*x + y)

some_constant = 125
"""

def demonstrate_dat_module_usage():
    """Demonstrate various ways to use DAT modules"""
    
    # Direct import usage
    result1 = a.myadd(1, 3)
    result2 = a.mysub(5, 2)
    constant = a.some_constant
    
    print(f'Addition result: {result1}')
    print(f'Subtraction result: {result2}')
    print(f'Constant value: {constant}')
    
    # Access module attributes
    module_name = a.__name__
    module_file = a.__file__ if hasattr(a, '__file__') else 'DAT module'
    
    print(f'Module name: {module_name}')
    print(f'Module file: {module_file}')
    
    return result1, result2, constant

# Create your own utility DAT module
def create_utility_dat_module():
    """Example of creating a comprehensive utility DAT module"""
    
    utility_code = '''
"""TouchDesigner Utility Module"""

import math

# Mathematical utilities
def normalize(value, min_val, max_val):
    """Normalize value to 0-1 range"""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)

def denormalize(normalized, min_val, max_val):
    """Convert normalized value back to original range"""
    return normalized * (max_val - min_val) + min_val

def lerp(a, b, t):
    """Linear interpolation between a and b"""
    return a + t * (b - a)

def clamp(value, min_val, max_val):
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))

# TouchDesigner specific utilities
def safe_op_reference(path):
    """Safely get operator reference"""
    try:
        operator = op(path)
        return operator if operator and operator.valid else None
    except:
        return None

def get_parameter_safely(operator, param_name, default=0):
    """Safely get parameter value"""
    try:
        if operator and hasattr(operator.par, param_name):
            return getattr(operator.par, param_name).eval()
        return default
    except:
        return default

# Color utilities
def rgb_to_hsv(r, g, b):
    """Convert RGB to HSV color space"""
    r, g, b = r/255.0, g/255.0, b/255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    
    # Value
    v = max_val
    
    # Saturation
    s = 0 if max_val == 0 else diff / max_val
    
    # Hue
    if diff == 0:
        h = 0
    elif max_val == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif max_val == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    else:
        h = (60 * ((r - g) / diff) + 240) % 360
    
    return h, s, v

# Constants
PI = math.pi
TWO_PI = 2 * math.pi
HALF_PI = math.pi / 2

# Version info
VERSION = "1.0"
AUTHOR = "TouchDesigner User"
'''
    
    return utility_code

# Best practices for DAT modules
def dat_module_best_practices():
    """Best practices for creating DAT modules"""
    
    practices = [
        "1. Include docstrings for all functions",
        "2. Use descriptive function and variable names", 
        "3. Include module-level documentation",
        "4. Organize functions logically",
        "5. Include version and author information",
        "6. Handle errors gracefully",
        "7. Use constants for magic numbers",
        "8. Test functions before using in production"
    ]
    
    return practices
```

---

## Module-on-Demand

### Dynamic Module Access with mod Object

**Source File**: `test_dat_modules.py`

**Key Concepts**: mod object, dynamic access, module attributes

```python
# You can also use the module on demand (mod) object
# This allows dynamic access to modules without explicit import

print(mod.utils_a.myadd(1, 3))
print(mod.utils_a.__name__)        # Module attributes
print(mod.utils_a.some_constant)   # Module data

def demonstrate_mod_object():
    """Demonstrate module-on-demand usage patterns"""
    
    # Dynamic module access
    result = mod.utils_a.myadd(1, 3)
    
    # Access module metadata
    module_name = mod.utils_a.__name__
    
    # Check if module exists before using
    if hasattr(mod, 'utils_a'):
        constant_value = mod.utils_a.some_constant
        print(f'Constant from mod: {constant_value}')
    
    # Dynamic function calls
    function_name = 'myadd'
    if hasattr(mod.utils_a, function_name):
        func = getattr(mod.utils_a, function_name)
        dynamic_result = func(10, 20)
        print(f'Dynamic call result: {dynamic_result}')
    
    return result

def mod_object_patterns():
    """Advanced patterns using mod object"""
    
    # Pattern 1: Configuration-driven module usage
    def use_module_from_config(config):
        """Use module based on configuration"""
        module_name = config.get('module', 'utils_a')
        function_name = config.get('function', 'myadd')
        args = config.get('args', [1, 2])
        
        if hasattr(mod, module_name):
            module = getattr(mod, module_name)
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                return func(*args)
        
        return None
    
    # Pattern 2: Module registry system
    def create_module_registry():
        """Create a registry of available modules"""
        registry = {}
        
        # Check for common utility modules
        utility_modules = ['utils_a', 'utils_b', 'math_utils', 'color_utils']
        
        for module_name in utility_modules:
            if hasattr(mod, module_name):
                module = getattr(mod, module_name)
                
                # Get module information
                functions = [name for name in dir(module) 
                           if callable(getattr(module, name)) and not name.startswith('_')]
                
                registry[module_name] = {
                    'module': module,
                    'functions': functions,
                    'available': True
                }
            else:
                registry[module_name] = {'available': False}
        
        return registry
    
    # Pattern 3: Hot-reloading modules
    def reload_module(module_name):
        """Reload a module (useful for development)"""
        if hasattr(mod, module_name):
            # In TouchDesigner, modules are reloaded automatically when DAT changes
            # But you can force reload by re-accessing
            module = getattr(mod, module_name)
            debug(f'Reloaded module: {module_name}')
            return module
        return None
    
    # Pattern 4: Safe module execution
    def safe_mod_execute(module_name, function_name, *args, **kwargs):
        """Safely execute module function with error handling"""
        try:
            if hasattr(mod, module_name):
                module = getattr(mod, module_name)
                if hasattr(module, function_name):
                    func = getattr(module, function_name)
                    return func(*args, **kwargs)
                else:
                    debug(f'Function {function_name} not found in {module_name}')
            else:
                debug(f'Module {module_name} not found')
        except Exception as e:
            debug(f'Error executing {module_name}.{function_name}: {e}')
        
        return None
    
    return use_module_from_config, create_module_registry, reload_module, safe_mod_execute

# Example usage patterns
def mod_usage_examples():
    """Examples of mod object usage"""
    
    # Example 1: Plugin system using mod
    def load_plugins():
        """Load all available plugin modules"""
        plugins = []
        plugin_names = ['plugin_audio', 'plugin_video', 'plugin_effects']
        
        for plugin_name in plugin_names:
            if hasattr(mod, plugin_name):
                plugin = getattr(mod, plugin_name)
                if hasattr(plugin, 'initialize'):
                    plugin.initialize()
                plugins.append(plugin)
        
        return plugins
    
    # Example 2: Dynamic utility selection
    def get_utility_function(category, operation):
        """Get utility function based on category and operation"""
        module_map = {
            'math': 'math_utils',
            'color': 'color_utils', 
            'geometry': 'geo_utils',
            'animation': 'anim_utils'
        }
        
        module_name = module_map.get(category)
        if module_name and hasattr(mod, module_name):
            module = getattr(mod, module_name)
            if hasattr(module, operation):
                return getattr(module, operation)
        
        return None
    
    # Example 3: Module validation
    def validate_module_interface(module_name, required_functions):
        """Validate that a module has required interface"""
        if not hasattr(mod, module_name):
            return False, f'Module {module_name} not found'
        
        module = getattr(mod, module_name)
        missing_functions = []
        
        for func_name in required_functions:
            if not hasattr(module, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            return False, f'Missing functions: {missing_functions}'
        
        return True, 'Module interface valid'
    
    return load_plugins, get_utility_function, validate_module_interface
```

---

## Local Module System

### Global Module Access via /local/modules

**Source File**: `test_modules2.py`

**Key Concepts**: Global modules, network-wide access, module hierarchy

```python
# To make a module available globally, put it in /local/modules
# Modules found there are available to this network and any child networks

import mymod1  # Found in /local/modules
a = mymod1.myadd(6, 8)
print(a)

# You can also use the module on demand object
a = mod.mymod1.myadd(6, 8)
print(a)

def demonstrate_local_modules():
    """Demonstrate local module system usage"""
    
    # Import from local modules
    import mymod1
    
    # Use imported functions
    result1 = mymod1.myadd(6, 8)  # Direct import usage
    result2 = mod.mymod1.myadd(6, 8)  # Mod object usage
    
    print(f'Import result: {result1}')
    print(f'Mod result: {result2}')
    
    return result1, result2

def create_local_module_structure():
    """Best practices for organizing local modules"""
    
    structure = {
        '/local/modules/': {
            'description': 'Global module container',
            'contents': {
                'core_utils.py': 'Core utility functions',
                'math_lib.py': 'Mathematical operations',
                'ui_helpers.py': 'UI utility functions',
                'network_tools.py': 'Network communication tools',
                'data_processors.py': 'Data processing utilities',
                'config_manager.py': 'Configuration management'
            }
        }
    }
    
    return structure

# Example local module: core_utils.py
def create_core_utils_module():
    """Example comprehensive core utilities module"""
    
    core_utils_code = '''
"""
Core Utilities Module for TouchDesigner
Location: /local/modules/core_utils

Provides essential utility functions used across multiple projects
"""

import math
import time

# Version and metadata
__version__ = "2.0"
__author__ = "TouchDesigner Team"
__description__ = "Core utility functions for TouchDesigner projects"

# Logging utilities
def log_message(message, level="INFO"):
    """Log message with timestamp and level"""
    timestamp = time.strftime("%H:%M:%S")
    debug(f"[{timestamp}] {level}: {message}")

def log_error(error_msg, context=""):
    """Log error with context"""
    log_message(f"ERROR in {context}: {error_msg}", "ERROR")

# Math utilities
def safe_divide(a, b, default=0):
    """Safe division with default fallback"""
    try:
        return a / b if b != 0 else default
    except:
        return default

def smooth_step(edge0, edge1, x):
    """Smooth step function for smooth transitions"""
    t = max(0, min(1, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)

def map_range(value, in_min, in_max, out_min, out_max):
    """Map value from input range to output range"""
    if in_max == in_min:
        return out_min
    return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))

# TouchDesigner utilities
def find_operators_by_type(container, op_type):
    """Find all operators of specific type in container"""
    if not container:
        return []
    
    found_ops = []
    for child in container.children:
        if child.type == op_type:
            found_ops.append(child)
    
    return found_ops

def safe_parameter_set(operator, param_name, value):
    """Safely set parameter value with error handling"""
    try:
        if operator and hasattr(operator.par, param_name):
            param = getattr(operator.par, param_name)
            param.val = value
            return True
    except Exception as e:
        log_error(f"Failed to set {param_name} = {value}", f"{operator}")
    
    return False

def create_operator_safely(container, op_class, name):
    """Create operator with error handling and naming"""
    try:
        # Ensure unique name
        base_name = name
        counter = 1
        while container.op(name):
            name = f"{base_name}_{counter}"
            counter += 1
        
        new_op = container.create(op_class, name)
        log_message(f"Created operator: {new_op.path}")
        return new_op
    
    except Exception as e:
        log_error(f"Failed to create {op_class} '{name}'", str(container))
        return None

# Data validation utilities
def validate_numeric_range(value, min_val, max_val, param_name="value"):
    """Validate numeric value is within specified range"""
    try:
        num_val = float(value)
        if min_val <= num_val <= max_val:
            return True, num_val
        else:
            return False, f"{param_name} must be between {min_val} and {max_val}"
    except ValueError:
        return False, f"{param_name} must be a number"

def validate_operator_reference(op_ref, expected_family=None):
    """Validate operator reference and optionally check family"""
    if not op_ref:
        return False, "Operator reference is None"
    
    if not op_ref.valid:
        return False, f"Operator {op_ref.path} is not valid"
    
    if expected_family and op_ref.family != expected_family:
        return False, f"Expected {expected_family}, got {op_ref.family}"
    
    return True, "Valid operator reference"

# Performance utilities
class PerformanceMonitor:
    """Simple performance monitoring utility"""
    
    def __init__(self):
        self.start_time = None
        self.measurements = {}
    
    def start(self, label="default"):
        """Start timing measurement"""
        self.measurements[label] = time.time()
    
    def end(self, label="default"):
        """End timing measurement and return duration"""
        if label in self.measurements:
            duration = time.time() - self.measurements[label]
            del self.measurements[label]
            return duration
        return 0
    
    def measure(self, func, label=None):
        """Measure function execution time"""
        if label is None:
            label = func.__name__
        
        self.start(label)
        result = func()
        duration = self.end(label)
        
        log_message(f"Function {label} took {duration:.4f}s")
        return result, duration

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

# Module initialization
def initialize():
    """Initialize core utilities module"""
    log_message(f"Core utilities v{__version__} initialized")

# Auto-initialize when imported
initialize()
'''
    
    return core_utils_code

def local_module_management():
    """Patterns for managing local modules"""
    
    # Pattern 1: Module discovery
    def discover_local_modules():
        """Discover all available local modules"""
        modules_container = op('/local/modules')
        if not modules_container:
            return []
        
        available_modules = []
        for child in modules_container.children:
            if child.family == DAT and child.name != 'readme':
                module_info = {
                    'name': child.name,
                    'path': child.path,
                    'valid': child.valid,
                    'modified': child.modified
                }
                available_modules.append(module_info)
        
        return available_modules
    
    # Pattern 2: Module dependency checking
    def check_module_dependencies(module_name, dependencies):
        """Check if module dependencies are available"""
        missing_deps = []
        
        for dep in dependencies:
            if not hasattr(mod, dep):
                missing_deps.append(dep)
        
        if missing_deps:
            log_message(f"Module {module_name} missing dependencies: {missing_deps}")
            return False
        
        return True
    
    # Pattern 3: Module version management
    def get_module_version(module_name):
        """Get version information from module"""
        if hasattr(mod, module_name):
            module = getattr(mod, module_name)
            return getattr(module, '__version__', 'unknown')
        return None
    
    return discover_local_modules, check_module_dependencies, get_module_version
```

---

## Utility Libraries

### Creating Reusable Function Libraries

**Source File**: `utils_a.py`

**Key Concepts**: Function libraries, documentation, constants, reusability

```python
# Example utility library structure
"""Sample utility functions for common operations"""

def myadd(x, y):
    """Add two numbers with special scaling
    
    Args:
        x: First number (scaled by 10000)
        y: Second number 
    
    Returns:
        Scaled sum: 10000*x + y
    """
    return 10000 * x + y

def mysub(x, y):
    """Subtract with special scaling
    
    Args:
        x: First number (scaled by 10000) 
        y: Second number
    
    Returns:
        Scaled difference: -(10000*x + y)
    """
    return -(10000 * x + y)

# Module constants
some_constant = 125

def create_comprehensive_utility_library():
    """Template for comprehensive utility library"""
    
    library_template = '''
"""
Comprehensive Utility Library Template
=====================================

A well-structured utility library for TouchDesigner projects.
Include clear documentation, type hints, and error handling.
"""

from typing import Optional, List, Tuple, Any, Union
import math

# Module metadata
__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"
__description__ = "Comprehensive utility library for TouchDesigner"

# Constants
DEFAULT_PRECISION = 6
MAX_ITERATIONS = 1000
EPSILON = 1e-10

# Type aliases for clarity
NumberType = Union[int, float]
Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]
ColorRGB = Tuple[float, float, float]
ColorRGBA = Tuple[float, float, float, float]

# Mathematical utilities
def clamp(value: NumberType, min_val: NumberType, max_val: NumberType) -> NumberType:
    """Clamp value between min and max bounds"""
    return max(min_val, min(max_val, value))

def lerp(a: NumberType, b: NumberType, t: NumberType) -> float:
    """Linear interpolation between a and b"""
    return a + t * (b - a)

def smoothstep(edge0: NumberType, edge1: NumberType, x: NumberType) -> float:
    """Smooth step interpolation"""
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def distance_2d(p1: Point2D, p2: Point2D) -> float:
    """Calculate distance between two 2D points"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)

def distance_3d(p1: Point3D, p2: Point3D) -> float:
    """Calculate distance between two 3D points"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)

def normalize_vector_3d(vector: Point3D) -> Point3D:
    """Normalize 3D vector to unit length"""
    magnitude = math.sqrt(vector[0]**2 + vector[1]**2 + vector[2]**2)
    if magnitude < EPSILON:
        return (0.0, 0.0, 0.0)
    
    return (vector[0]/magnitude, vector[1]/magnitude, vector[2]/magnitude)

# Color utilities
def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex string"""
    return f"#{r:02x}{g:02x}{b:02x}"

def hex_to_rgb(hex_color: str) -> ColorRGB:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Invalid hex color format")
    
    return (
        int(hex_color[0:2], 16) / 255.0,
        int(hex_color[2:4], 16) / 255.0,
        int(hex_color[4:6], 16) / 255.0
    )

def color_lerp(color1: ColorRGB, color2: ColorRGB, t: float) -> ColorRGB:
    """Linear interpolation between two colors"""
    return (
        lerp(color1[0], color2[0], t),
        lerp(color1[1], color2[1], t),
        lerp(color1[2], color2[2], t)
    )

# TouchDesigner specific utilities
def safe_op(path: str) -> Optional[Any]:
    """Safely get operator reference with None fallback"""
    try:
        operator = op(path)
        return operator if operator and operator.valid else None
    except:
        return None

def get_param_value(operator: Any, param_name: str, default: Any = 0) -> Any:
    """Safely get parameter value with default fallback"""
    try:
        if operator and hasattr(operator.par, param_name):
            return getattr(operator.par, param_name).eval()
        return default
    except:
        return default

def set_param_value(operator: Any, param_name: str, value: Any) -> bool:
    """Safely set parameter value"""
    try:
        if operator and hasattr(operator.par, param_name):
            getattr(operator.par, param_name).val = value
            return True
        return False
    except:
        return False

# Data validation and conversion
def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int with default"""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def validate_range(value: NumberType, min_val: NumberType, max_val: NumberType) -> bool:
    """Validate value is within range"""
    try:
        return min_val <= value <= max_val
    except:
        return False

# String utilities
def sanitize_name(name: str) -> str:
    """Sanitize string for use as TouchDesigner operator name"""
    import re
    # Remove invalid characters and replace with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure doesn't start with number
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized or 'unnamed'

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to max length with optional suffix"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

# Error handling utilities
class UtilityError(Exception):
    """Custom exception for utility functions"""
    pass

def with_error_handling(func):
    """Decorator for automatic error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            debug(f"Error in {func.__name__}: {e}")
            return None
    return wrapper

# Performance utilities
import time

def timing_decorator(func):
    """Decorator to measure function execution time"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        debug(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Testing utilities
def run_tests():
    """Run basic tests for utility functions"""
    tests_passed = 0
    tests_total = 0
    
    # Test mathematical functions
    tests_total += 1
    if abs(lerp(0, 10, 0.5) - 5.0) < EPSILON:
        tests_passed += 1
    else:
        debug("lerp test failed")
    
    tests_total += 1
    if clamp(15, 0, 10) == 10:
        tests_passed += 1
    else:
        debug("clamp test failed")
    
    tests_total += 1
    distance = distance_2d((0, 0), (3, 4))
    if abs(distance - 5.0) < EPSILON:
        tests_passed += 1
    else:
        debug("distance_2d test failed")
    
    debug(f"Tests passed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total

# Module initialization
if __name__ == "__main__":
    debug(f"Utility library {__version__} loaded successfully")
    run_tests()
'''
    
    return library_template

def utility_library_patterns():
    """Patterns for organizing utility libraries"""
    
    organization_patterns = {
        'by_domain': {
            'math_utils': ['lerp', 'clamp', 'smoothstep', 'distance'],
            'color_utils': ['rgb_to_hsv', 'color_blend', 'palette_generation'],
            'geometry_utils': ['point_in_polygon', 'line_intersection', 'mesh_operations'],
            'animation_utils': ['ease_functions', 'keyframe_interpolation', 'timeline_utils'],
            'ui_utils': ['layout_helpers', 'widget_creation', 'event_handling'],
            'network_utils': ['osc_helpers', 'tcp_utilities', 'data_serialization']
        },
        'by_complexity': {
            'core_utils': ['basic operations', 'common patterns', 'essential helpers'],
            'advanced_utils': ['complex algorithms', 'optimization functions', 'specialized tools'],
            'experimental_utils': ['beta features', 'research functions', 'prototype code']
        },
        'by_dependency': {
            'standalone_utils': ['no dependencies', 'pure python'],
            'td_utils': ['TouchDesigner specific', 'requires TD context'],
            'external_utils': ['requires 3rd party libraries', 'optional dependencies']
        }
    }
    
    return organization_patterns
```

---

## Module Best Practices

### Patterns for Maintainable Code

```python
def module_documentation_standards():
    """Standards for documenting TouchDesigner modules"""
    
    documentation_template = '''
"""
Module Name: {module_name}
Version: {version}
Author: {author}
Created: {creation_date}
Modified: {modification_date}

Description:
    Brief description of what this module does and why it exists.
    Include primary use cases and target audience.

Dependencies:
    - List any required modules or libraries
    - Note TouchDesigner version requirements
    - Include any external dependencies

Usage Examples:
    ```python
    import {module_name}
    
    # Basic usage
    result = {module_name}.main_function(parameters)
    
    # Advanced usage
    {module_name}.configure(settings)
    advanced_result = {module_name}.advanced_function()
    ```

Public Functions:
    - function_name(args) -> return_type: Description
    - another_function(args) -> return_type: Description

Private Functions:
    - _helper_function(): Internal helper
    - _validation_function(): Input validation

Constants:
    - CONSTANT_NAME: Description and typical value

Notes:
    - Any special considerations
    - Performance implications
    - Thread safety notes
    - Known limitations

Changelog:
    v1.0.0: Initial release
    v1.1.0: Added advanced features
    v1.2.0: Bug fixes and performance improvements
"""
'''
    
    return documentation_template

def module_testing_patterns():
    """Patterns for testing TouchDesigner modules"""
    
    testing_code = '''
"""
Testing utilities for TouchDesigner modules

Provides simple testing framework since traditional Python test frameworks
may not work well in TouchDesigner environment.
"""

class SimpleTestRunner:
    """Simple test runner for TouchDesigner modules"""
    
    def __init__(self, module_name="Unknown"):
        self.module_name = module_name
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def assert_equal(self, actual, expected, message=""):
        """Assert two values are equal"""
        self.tests_run += 1
        
        if actual == expected:
            self.tests_passed += 1
            result = "PASS"
        else:
            self.tests_failed += 1
            result = "FAIL"
            message = message or f"Expected {expected}, got {actual}"
        
        self.test_results.append({
            'result': result,
            'message': message,
            'actual': actual,
            'expected': expected
        })
        
        return result == "PASS"
    
    def assert_true(self, condition, message=""):
        """Assert condition is true"""
        return self.assert_equal(condition, True, message)
    
    def assert_false(self, condition, message=""):
        """Assert condition is false"""
        return self.assert_equal(condition, False, message)
    
    def assert_almost_equal(self, actual, expected, tolerance=1e-10, message=""):
        """Assert two floating point values are nearly equal"""
        self.tests_run += 1
        
        if abs(actual - expected) < tolerance:
            self.tests_passed += 1
            result = "PASS"
        else:
            self.tests_failed += 1
            result = "FAIL"
            message = message or f"Expected {expected}, got {actual} (tolerance: {tolerance})"
        
        self.test_results.append({
            'result': result,
            'message': message,
            'actual': actual,
            'expected': expected
        })
        
        return result == "PASS"
    
    def run_test(self, test_func, test_name=""):
        """Run a test function with error handling"""
        test_name = test_name or test_func.__name__
        
        try:
            test_func(self)
            debug(f"Test {test_name}: completed")
        except Exception as e:
            self.tests_run += 1
            self.tests_failed += 1
            self.test_results.append({
                'result': 'ERROR',
                'message': f"Test {test_name} raised exception: {e}",
                'actual': None,
                'expected': None
            })
            debug(f"Test {test_name}: ERROR - {e}")
    
    def print_summary(self):
        """Print test summary"""
        debug(f"\\n=== Test Summary for {self.module_name} ===")
        debug(f"Tests Run: {self.tests_run}")
        debug(f"Tests Passed: {self.tests_passed}")
        debug(f"Tests Failed: {self.tests_failed}")
        debug(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%" if self.tests_run > 0 else "No tests run")
        
        if self.tests_failed > 0:
            debug("\\nFailed Tests:")
            for result in self.test_results:
                if result['result'] in ['FAIL', 'ERROR']:
                    debug(f"  - {result['message']}")

# Example test suite
def test_math_utilities():
    """Example test suite for math utilities"""
    
    def test_lerp(test_runner):
        """Test linear interpolation function"""
        # Test basic interpolation
        result = lerp(0, 10, 0.5)
        test_runner.assert_almost_equal(result, 5.0, message="lerp(0, 10, 0.5) should equal 5.0")
        
        # Test edge cases
        result = lerp(0, 10, 0.0)
        test_runner.assert_almost_equal(result, 0.0, message="lerp at t=0 should return start value")
        
        result = lerp(0, 10, 1.0)
        test_runner.assert_almost_equal(result, 10.0, message="lerp at t=1 should return end value")
    
    def test_clamp(test_runner):
        """Test clamp function"""
        result = clamp(15, 0, 10)
        test_runner.assert_equal(result, 10, message="clamp should limit to max value")
        
        result = clamp(-5, 0, 10)
        test_runner.assert_equal(result, 0, message="clamp should limit to min value")
        
        result = clamp(5, 0, 10)
        test_runner.assert_equal(result, 5, message="clamp should pass through valid values")
    
    # Run tests
    runner = SimpleTestRunner("Math Utilities")
    runner.run_test(test_lerp)
    runner.run_test(test_clamp)
    runner.print_summary()
    
    return runner.tests_passed == runner.tests_run

# Integration testing
def integration_test_pattern():
    """Pattern for integration testing with TouchDesigner operators"""
    
    def test_operator_integration():
        """Test module integration with TouchDesigner operators"""
        
        # Create test environment
        test_container = me.parent().create(containerCOMP, 'test_container')
        
        try:
            # Test operator creation
            test_op = create_operator_safely(test_container, mathCHOP, 'test_math')
            if not test_op:
                debug("Failed to create test operator")
                return False
            
            # Test parameter manipulation
            success = set_param_value(test_op, 'func', 'sin')
            if not success:
                debug("Failed to set parameter")
                return False
            
            # Test parameter retrieval
            func_value = get_param_value(test_op, 'func', 'unknown')
            if func_value != 'sin':
                debug(f"Parameter not set correctly: {func_value}")
                return False
            
            debug("Integration test passed")
            return True
        
        finally:
            # Clean up test environment
            if test_container and test_container.valid:
                test_container.destroy()

# Performance testing
def performance_test_pattern():
    """Pattern for performance testing modules"""
    
    import time
    
    def benchmark_function(func, iterations=1000):
        """Benchmark a function's performance"""
        start_time = time.time()
        
        for _ in range(iterations):
            func()
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        debug(f"Function {func.__name__}:")
        debug(f"  Total time: {total_time:.4f}s")
        debug(f"  Average time: {avg_time:.6f}s")
        debug(f"  Iterations: {iterations}")
        
        return avg_time
'''
    
    return testing_code

def module_versioning_and_lifecycle():
    """Patterns for module versioning and lifecycle management"""
    
    versioning_patterns = {
        'semantic_versioning': {
            'format': 'MAJOR.MINOR.PATCH',
            'rules': {
                'MAJOR': 'Breaking changes, incompatible API changes',
                'MINOR': 'New features, backwards compatible',
                'PATCH': 'Bug fixes, backwards compatible'
            },
            'example': '2.1.3'
        },
        'date_versioning': {
            'format': 'YYYY.MM.DD[.build]',
            'example': '2023.12.15.1'
        },
        'simple_versioning': {
            'format': 'v1, v2, v3, etc.',
            'example': 'v5'
        }
    }
    
    lifecycle_stages = {
        'development': 'Active development, unstable API',
        'alpha': 'Feature complete, internal testing',
        'beta': 'Public testing, API stable',
        'release_candidate': 'Production ready, final testing',
        'stable': 'Production release',
        'maintenance': 'Bug fixes only',
        'deprecated': 'No longer maintained',
        'obsolete': 'Should not be used'
    }
    
    return versioning_patterns, lifecycle_stages
```

---

## Dependency Management

### Managing Module Dependencies

```python
def dependency_management_patterns():
    """Patterns for managing module dependencies in TouchDesigner"""
    
    # Pattern 1: Dependency declaration
    dependency_template = '''
"""
Module Dependency Declaration Template
"""

# Required dependencies
REQUIRED_MODULES = [
    'core_utils',  # Core utility functions
    'math_utils',  # Mathematical operations
]

# Optional dependencies
OPTIONAL_MODULES = {
    'advanced_math': 'Enables advanced mathematical functions',
    'visualization': 'Provides visualization utilities',
    'network_tools': 'Network communication features'
}

# TouchDesigner version requirements
MIN_TD_VERSION = '2023.11000'  # Minimum TouchDesigner version
RECOMMENDED_TD_VERSION = '2023.12000'  # Recommended version

# Python version requirements
MIN_PYTHON_VERSION = (3, 7)

def check_dependencies():
    """Check if all dependencies are available"""
    missing_required = []
    missing_optional = {}
    
    # Check required modules
    for module_name in REQUIRED_MODULES:
        if not hasattr(mod, module_name):
            missing_required.append(module_name)
    
    # Check optional modules
    for module_name, description in OPTIONAL_MODULES.items():
        if not hasattr(mod, module_name):
            missing_optional[module_name] = description
    
    # Report results
    if missing_required:
        debug(f"Missing required modules: {missing_required}")
        return False
    
    if missing_optional:
        debug(f"Missing optional modules: {list(missing_optional.keys())}")
        debug("Some features may be unavailable")
    
    return True

def get_dependency_info():
    """Get information about module dependencies"""
    return {
        'required': REQUIRED_MODULES,
        'optional': OPTIONAL_MODULES,
        'td_version': MIN_TD_VERSION,
        'python_version': MIN_PYTHON_VERSION
    }

# Auto-check dependencies on import
if not check_dependencies():
    debug("Warning: Module may not function correctly due to missing dependencies")
'''
    
    # Pattern 2: Lazy loading
    lazy_loading_pattern = '''
def lazy_import(module_name):
    """Lazy import pattern for optional dependencies"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not hasattr(wrapper, '_module'):
                if hasattr(mod, module_name):
                    wrapper._module = getattr(mod, module_name)
                else:
                    raise ImportError(f"Module {module_name} not available")
            
            return func(wrapper._module, *args, **kwargs)
        return wrapper
    return decorator

@lazy_import('advanced_math')
def use_advanced_math(math_module, x, y):
    """Function that uses advanced math module when available"""
    return math_module.complex_calculation(x, y)
'''
    
    # Pattern 3: Feature flags
    feature_flags_pattern = '''
# Feature availability based on dependencies
FEATURES = {}

def initialize_features():
    """Initialize available features based on dependencies"""
    FEATURES['advanced_math'] = hasattr(mod, 'advanced_math')
    FEATURES['visualization'] = hasattr(mod, 'visualization')
    FEATURES['network'] = hasattr(mod, 'network_tools')
    
    debug(f"Available features: {list(k for k, v in FEATURES.items() if v)}")

def require_feature(feature_name):
    """Decorator to require specific feature"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not FEATURES.get(feature_name, False):
                raise RuntimeError(f"Feature {feature_name} is not available")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_feature('visualization')
def create_visualization(data):
    """Function that requires visualization feature"""
    viz_module = getattr(mod, 'visualization')
    return viz_module.create_chart(data)

# Initialize on module load
initialize_features()
'''
    
    return dependency_template, lazy_loading_pattern, feature_flags_pattern

def create_dependency_manager():
    """Create a dependency management system"""
    
    manager_code = '''
class DependencyManager:
    """Manage module dependencies in TouchDesigner"""
    
    def __init__(self):
        self.required_modules = set()
        self.optional_modules = {}
        self.loaded_modules = {}
        self.failed_modules = set()
    
    def require(self, module_name, description=""):
        """Mark module as required dependency"""
        self.required_modules.add(module_name)
        if description:
            self.optional_modules[module_name] = description
    
    def optional(self, module_name, description=""):
        """Mark module as optional dependency"""
        self.optional_modules[module_name] = description
    
    def load_module(self, module_name):
        """Load a module with caching"""
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        if module_name in self.failed_modules:
            return None
        
        try:
            if hasattr(mod, module_name):
                module = getattr(mod, module_name)
                self.loaded_modules[module_name] = module
                return module
            else:
                self.failed_modules.add(module_name)
                return None
        except Exception as e:
            debug(f"Failed to load module {module_name}: {e}")
            self.failed_modules.add(module_name)
            return None
    
    def check_dependencies(self):
        """Check all dependencies"""
        missing_required = []
        
        for module_name in self.required_modules:
            if not self.load_module(module_name):
                missing_required.append(module_name)
        
        if missing_required:
            debug(f"Missing required modules: {missing_required}")
            return False
        
        return True
    
    def get_status(self):
        """Get dependency status report"""
        status = {
            'required_available': [],
            'required_missing': [],
            'optional_available': [],
            'optional_missing': []
        }
        
        for module_name in self.required_modules:
            if self.load_module(module_name):
                status['required_available'].append(module_name)
            else:
                status['required_missing'].append(module_name)
        
        for module_name in self.optional_modules:
            if module_name not in self.required_modules:
                if self.load_module(module_name):
                    status['optional_available'].append(module_name)
                else:
                    status['optional_missing'].append(module_name)
        
        return status

# Global dependency manager
deps = DependencyManager()

# Usage example:
deps.require('core_utils', 'Core utility functions')
deps.optional('advanced_math', 'Advanced mathematical operations')

if deps.check_dependencies():
    # All required dependencies available
    core_utils = deps.load_module('core_utils')
    advanced_math = deps.load_module('advanced_math')  # May be None
'''
    
    return manager_code
```

---

## Cross-References

### Related Documentation

- **[PY_Extensions.md](../PYTHON_/PY_Extensions.md)** - Extension development with modules
- **[MODULE_TDFunctions.md](../MODULE_/MODULE_TDFunctions.md)** - TDFunctions module reference
- **[PY_TD_Python_Examples_Reference.md](../PYTHON_/PY_TD_Python_Examples_Reference.md)** - Complete Python patterns

### Related Examples

- **[EX_EXTENSIONS.md](./EX_EXTENSIONS.md)** - Using modules in extensions
- **[EX_BUILTINS.md](./EX_BUILTINS.md)** - Built-in module usage
- **[EX_MODULE_TUTORIALS.md](./EX_MODULE_TUTORIALS.md)** - Step-by-step module development

### Module System Components

- **DAT Operators** - Any DAT can be used as a module
- **/local/modules/** - Global module container
- **mod object** - Module-on-demand access
- **import statement** - Standard Python import
- **TDFunctions** - TouchDesigner utility functions

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/Modules/`

**Key Files**:

- `test_imports.py` - Standard and 3rd party imports
- `test_builtins.py` - Built-in TouchDesigner objects
- `utils_a.py` - Example utility module
- `test_dat_modules.py` - DAT module usage patterns
- `test_modules2.py` - Local module system
- `mymod1.py` - Global module example

**Total Examples**: 19 files covering all aspects of module system usage, from basic imports to advanced dependency management and code organization.

---

*These examples provide the foundation for creating well-organized, maintainable TouchDesigner projects through effective use of the module system and code reuse patterns.*
