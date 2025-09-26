---
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: 45-60 minutes
operators:
- Execute_DAT
- Script_DAT
- Text_DAT
- Base_COMP
- Geometry_COMP
- Camera_COMP
- Light_COMP
- Render_TOP
- Transform_SOP
- Constant_CHOP
- Math_CHOP
- Timer_CHOP
- Null_CHOP
- Parameter_Execute_DAT
- CHOP_Execute_DAT
concepts:
- advanced_python_api
- operator_chaining
- parameter_automation
- real_time_control
- callback_integration
- error_handling_patterns
- performance_optimization
- matrix_transformations
- component_hierarchies
prerequisites:
- MODULE_td_Module
- PY_Working_with_OPs_in_Python
- CLASS_OP_Class
workflows:
- procedural_automation
- real_time_performance_systems
- advanced_scripting_patterns
- complex_parameter_control
- dynamic_network_creation
keywords:
- advanced python api
- operator chaining
- parameter automation
- callback patterns
- error handling
- performance scripting
- matrix math
- component hierarchies
- real-time control
tags:
- python
- advanced
- api
- examples
- patterns
- performance
- automation
- real-time
relationships:
  MODULE_td_Module: strong
  PY_Working_with_OPs_in_Python: strong
  CLASS_OP_Class: strong
  EX_OPS: medium
related_docs:
- MODULE_td_Module
- PY_Working_with_OPs_in_Python
- CLASS_OP_Class
- EX_OPS
hierarchy:
  secondary: advanced_examples
  tertiary: python_api_patterns
question_patterns:
- Advanced Python API usage in TouchDesigner?
- Complex operator manipulation patterns?
- Real-time Python scripting examples?
- Performance-oriented Python patterns?
common_use_cases:
- procedural_automation
- real_time_performance_systems
- advanced_scripting_patterns
- complex_parameter_control
---

# Advanced TouchDesigner Python API Patterns

## 🎯 Quick Reference

**Purpose**: Advanced Python API usage patterns for complex TouchDesigner automation
**Difficulty**: Advanced
**Time to read**: 45-60 minutes
**Use for**: procedural_automation, real_time_performance_systems, advanced_scripting_patterns

## 🔗 Learning Path

**Prerequisites**: [MODULE td Module] → [PY Working with OPs in Python] → [CLASS OP Class]
**This document**: EXAMPLES advanced patterns
**Next steps**: Real-world implementation and optimization

## Advanced Operator Access Patterns

### Safe Operator Access with Error Handling

```python
class SafeOperatorAccess:
    """Robust operator access with comprehensive error handling"""
    
    @staticmethod
    def safe_op(path, create_if_missing=False, op_type=None):
        """Safely access operator with optional creation"""
        try:
            # Try using opex for clear error messages
            target_op = op(path)
            if target_op is None:
                if create_if_missing and op_type:
                    parent_path = '/'.join(path.split('/')[:-1])
                    op_name = path.split('/')[-1]
                    parent_op = op(parent_path) if parent_path else root
                    if parent_op:
                        target_op = parent_op.create(op_type, op_name)
                        debug(f"Created missing operator: {path}")
                        return target_op
                raise ValueError(f"Operator not found: {path}")
            return target_op
        except Exception as e:
            debug(f"Error accessing operator {path}: {str(e)}")
            return None
    
    @staticmethod
    def safe_param(op_path, param_name, default_value=None):
        """Safely access parameter with fallback"""
        try:
            target_op = SafeOperatorAccess.safe_op(op_path)
            if target_op and hasattr(target_op.par, param_name):
                param = getattr(target_op.par, param_name)
                return param.eval() if hasattr(param, 'eval') else param
            return default_value
        except Exception as e:
            debug(f"Error accessing parameter {op_path}.{param_name}: {str(e)}")
            return default_value

# Usage examples
safe_access = SafeOperatorAccess()

# Safe operator access with creation fallback
geometry_comp = safe_access.safe_op('/project1/geo1', 
                                   create_if_missing=True, 
                                   op_type=geometryCOMP)

# Safe parameter access with defaults
rotation_x = safe_access.safe_param('/project1/geo1', 'rx', 0.0)
```

### Advanced Operator Query Patterns

```python
class AdvancedOperatorQuery:
    """Advanced operator selection and filtering"""
    
    @staticmethod
    def find_operators_by_criteria(search_root='/', **criteria):
        """Find operators using complex criteria"""
        results = []
        search_op = op(search_root) if isinstance(search_root, str) else search_root
        
        # Get all children recursively if deep search requested
        candidates = []
        if criteria.get('deep_search', False):
            candidates = search_op.findChildren(depth=criteria.get('max_depth', 10))
        else:
            candidates = list(search_op.children)
        
        for candidate in candidates:
            if AdvancedOperatorQuery._matches_criteria(candidate, criteria):
                results.append(candidate)
        
        return results
    
    @staticmethod
    def _matches_criteria(op_candidate, criteria):
        """Check if operator matches all criteria"""
        # Family filter
        if 'family' in criteria:
            families = criteria['family'] if isinstance(criteria['family'], list) else [criteria['family']]
            if op_candidate.family not in families:
                return False
        
        # Type filter
        if 'type' in criteria:
            types = criteria['type'] if isinstance(criteria['type'], list) else [criteria['type']]
            if op_candidate.type not in types:
                return False
        
        # Name pattern filter
        if 'name_pattern' in criteria:
            import re
            if not re.search(criteria['name_pattern'], op_candidate.name):
                return False
        
        # Parameter value filter
        if 'parameter_filter' in criteria:
            for param_name, expected_value in criteria['parameter_filter'].items():
                if hasattr(op_candidate.par, param_name):
                    param = getattr(op_candidate.par, param_name)
                    actual_value = param.eval() if hasattr(param, 'eval') else param
                    if actual_value != expected_value:
                        return False
                else:
                    return False
        
        # Custom filter function
        if 'custom_filter' in criteria:
            if not criteria['custom_filter'](op_candidate):
                return False
        
        return True

# Usage examples
query = AdvancedOperatorQuery()

# Find all CHOP operators with specific names
chop_operators = query.find_operators_by_criteria(
    search_root='/project1',
    family='CHOP',
    name_pattern=r'(lfo|osc|wave)',
    deep_search=True
)

# Find geometry components with specific transform values
geo_comps = query.find_operators_by_criteria(
    search_root='/project1',
    family='COMP',
    type='geo',
    parameter_filter={'tx': 0, 'ty': 0},
    custom_filter=lambda op: len(op.children) > 5
)

debug(f"Found {len(chop_operators)} CHOP operators")
debug(f"Found {len(geo_comps)} geometry components")
```

## Real-Time Parameter Automation

### Dynamic Parameter Control System

```python
class ParameterAnimationSystem:
    """Advanced parameter animation and control"""
    
    def __init__(self):
        self.animations = {}
        self.running = False
    
    def animate_parameter(self, op_path, param_name, animation_config):
        """Set up parameter animation"""
        animation_id = f"{op_path}.{param_name}"
        
        config = {
            'type': 'sine',  # sine, linear, exponential, custom
            'duration': 2.0,
            'start_value': 0.0,
            'end_value': 1.0,
            'loop': True,
            'ease_function': None,
            'custom_function': None,
            **animation_config
        }
        
        config['start_time'] = absTime.seconds
        self.animations[animation_id] = config
        
        return animation_id
    
    def update_animations(self):
        """Update all active animations - call from timer or execute DAT"""
        current_time = absTime.seconds
        
        for animation_id, config in list(self.animations.items()):
            try:
                # Calculate progress
                elapsed = current_time - config['start_time']
                progress = elapsed / config['duration']
                
                # Handle looping
                if config['loop'] and progress >= 1.0:
                    config['start_time'] = current_time
                    progress = 0.0
                elif progress >= 1.0:
                    progress = 1.0
                    # Animation complete, remove if not looping
                    if not config['loop']:
                        del self.animations[animation_id]
                        continue
                
                # Calculate value based on animation type
                if config['type'] == 'sine':
                    import math
                    value = config['start_value'] + (config['end_value'] - config['start_value']) * \
                           (math.sin(progress * math.pi * 2) * 0.5 + 0.5)
                elif config['type'] == 'linear':
                    value = config['start_value'] + (config['end_value'] - config['start_value']) * progress
                elif config['type'] == 'exponential':
                    import math
                    value = config['start_value'] + (config['end_value'] - config['start_value']) * \
                           (1 - math.exp(-5 * progress))
                elif config['type'] == 'custom' and config['custom_function']:
                    value = config['custom_function'](progress, config)
                else:
                    value = config['start_value']
                
                # Apply easing if specified
                if config['ease_function']:
                    value = config['ease_function'](value, config)
                
                # Set parameter value
                op_path, param_name = animation_id.rsplit('.', 1)
                target_op = op(op_path)
                if target_op and hasattr(target_op.par, param_name):
                    setattr(target_op.par, param_name, value)
                
            except Exception as e:
                debug(f"Error updating animation {animation_id}: {str(e)}")
                # Remove problematic animation
                if animation_id in self.animations:
                    del self.animations[animation_id]

# Global animation system instance
param_animator = ParameterAnimationSystem()

# Usage examples
def setup_camera_orbit():
    """Set up automatic camera orbit animation"""
    # Animate camera rotation around Y axis
    param_animator.animate_parameter('/project1/cam1', 'ry', {
        'type': 'linear',
        'duration': 10.0,
        'start_value': 0,
        'end_value': 360,
        'loop': True
    })
    
    # Animate camera height with sine wave
    param_animator.animate_parameter('/project1/cam1', 'ty', {
        'type': 'sine',
        'duration': 6.0,
        'start_value': 2.0,
        'end_value': 8.0,
        'loop': True
    })

# Call this from a Timer CHOP callback or Execute DAT
def onFrameEnd():
    param_animator.update_animations()
```

### Advanced Callback Integration

```python
class CallbackManager:
    """Centralized callback management system"""
    
    def __init__(self):
        self.callbacks = {}
        self.global_state = {}
    
    def register_parameter_callback(self, op_path, param_name, callback_func, **options):
        """Register parameter change callback"""
        callback_id = f"{op_path}.{param_name}"
        
        self.callbacks[callback_id] = {
            'type': 'parameter',
            'function': callback_func,
            'op_path': op_path,
            'param_name': param_name,
            'options': options,
            'last_value': None
        }
        
        return callback_id
    
    def register_chop_callback(self, chop_path, callback_func, **options):
        """Register CHOP value change callback"""
        callback_id = f"{chop_path}.chop"
        
        self.callbacks[callback_id] = {
            'type': 'chop',
            'function': callback_func,
            'chop_path': chop_path,
            'options': options,
            'last_values': {}
        }
        
        return callback_id
    
    def process_callbacks(self):
        """Process all registered callbacks - call from Execute DAT"""
        for callback_id, callback_info in self.callbacks.items():
            try:
                if callback_info['type'] == 'parameter':
                    self._process_parameter_callback(callback_id, callback_info)
                elif callback_info['type'] == 'chop':
                    self._process_chop_callback(callback_id, callback_info)
            except Exception as e:
                debug(f"Error processing callback {callback_id}: {str(e)}")
    
    def _process_parameter_callback(self, callback_id, info):
        """Process parameter change callback"""
        target_op = op(info['op_path'])
        if target_op and hasattr(target_op.par, info['param_name']):
            param = getattr(target_op.par, info['param_name'])
            current_value = param.eval() if hasattr(param, 'eval') else param
            
            if info['last_value'] != current_value:
                # Value changed, call callback
                info['function'](target_op, info['param_name'], current_value, info['last_value'])
                info['last_value'] = current_value
    
    def _process_chop_callback(self, callback_id, info):
        """Process CHOP value change callback"""
        chop_op = op(info['chop_path'])
        if chop_op and hasattr(chop_op, 'chans'):
            current_values = {}
            for chan in chop_op.chans():
                current_values[chan.name] = chan.vals[0] if len(chan.vals) > 0 else 0
            
            # Check for changes
            if info['last_values'] != current_values:
                changes = {}
                for chan_name, value in current_values.items():
                    old_value = info['last_values'].get(chan_name, None)
                    if old_value != value:
                        changes[chan_name] = {'new': value, 'old': old_value}
                
                if changes:
                    info['function'](chop_op, changes, current_values)
                info['last_values'] = current_values.copy()

# Global callback manager
callback_manager = CallbackManager()

# Usage examples
def on_camera_position_change(op, param_name, new_value, old_value):
    """Called when camera position changes"""
    debug(f"Camera {op.name}.{param_name} changed from {old_value} to {new_value}")
    
    # Update dependent objects
    if param_name in ['tx', 'ty', 'tz']:
        # Recalculate lighting or shadows
        lighting_system = op('/project1/lighting_system')
        if lighting_system:
            lighting_system.par.recalc.pulse()

def on_audio_levels_change(chop_op, changes, all_values):
    """Called when audio levels change"""
    for chan_name, change_info in changes.items():
        if change_info['new'] > 0.8:  # High audio level
            # Trigger visual effects
            vfx_trigger = op('/project1/vfx_trigger')
            if vfx_trigger:
                vfx_trigger.par.intensity = change_info['new']
                vfx_trigger.par.trigger.pulse()

# Register callbacks
callback_manager.register_parameter_callback('/project1/cam1', 'tx', on_camera_position_change)
callback_manager.register_parameter_callback('/project1/cam1', 'ty', on_camera_position_change)
callback_manager.register_parameter_callback('/project1/cam1', 'tz', on_camera_position_change)
callback_manager.register_chop_callback('/project1/audioin1', on_audio_levels_change)

# Call from Execute DAT onFrameEnd or similar
def onFrameEnd():
    callback_manager.process_callbacks()
```

## Matrix Mathematics and Transform Hierarchies

### Advanced Transform Operations

```python
class TransformHierarchyManager:
    """Advanced transform hierarchy management"""
    
    def __init__(self):
        self.transform_cache = {}
        self.hierarchy_cache = {}
    
    def get_world_transform_matrix(self, op_path):
        """Get world transform matrix for any operator"""
        target_op = op(op_path)
        if not target_op:
            return tdu.Matrix()
        
        # Check cache first
        cache_key = f"{op_path}_{target_op.cook}"
        if cache_key in self.transform_cache:
            return self.transform_cache[cache_key]
        
        # Calculate world transform by walking up hierarchy
        world_matrix = tdu.Matrix()
        current_op = target_op
        
        while current_op and current_op != root:
            # Get local transform matrix
            local_matrix = self._get_local_transform_matrix(current_op)
            
            # Multiply with accumulated world transform
            world_matrix = local_matrix * world_matrix
            
            # Move up hierarchy
            current_op = current_op.parent()
        
        # Cache result
        self.transform_cache[cache_key] = world_matrix
        return world_matrix
    
    def _get_local_transform_matrix(self, target_op):
        """Get local transform matrix from operator parameters"""
        if not hasattr(target_op.par, 'tx'):
            return tdu.Matrix()  # Identity matrix
        
        # Translation
        tx = target_op.par.tx.eval() if hasattr(target_op.par, 'tx') else 0
        ty = target_op.par.ty.eval() if hasattr(target_op.par, 'ty') else 0
        tz = target_op.par.tz.eval() if hasattr(target_op.par, 'tz') else 0
        
        # Rotation (in degrees)
        rx = target_op.par.rx.eval() if hasattr(target_op.par, 'rx') else 0
        ry = target_op.par.ry.eval() if hasattr(target_op.par, 'ry') else 0
        rz = target_op.par.rz.eval() if hasattr(target_op.par, 'rz') else 0
        
        # Scale
        sx = target_op.par.sx.eval() if hasattr(target_op.par, 'sx') else 1
        sy = target_op.par.sy.eval() if hasattr(target_op.par, 'sy') else 1
        sz = target_op.par.sz.eval() if hasattr(target_op.par, 'sz') else 1
        
        # Build transform matrix
        import math
        
        # Convert degrees to radians
        rx_rad = math.radians(rx)
        ry_rad = math.radians(ry)
        rz_rad = math.radians(rz)
        
        # Create individual transformation matrices
        translate_matrix = tdu.Matrix()
        translate_matrix.translate(tx, ty, tz)
        
        rotate_x_matrix = tdu.Matrix()
        rotate_x_matrix.rotateX(rx_rad)
        
        rotate_y_matrix = tdu.Matrix()
        rotate_y_matrix.rotateY(ry_rad)
        
        rotate_z_matrix = tdu.Matrix()
        rotate_z_matrix.rotateZ(rz_rad)
        
        scale_matrix = tdu.Matrix()
        scale_matrix.scale(sx, sy, sz)
        
        # Combine transformations: T * R * S
        result_matrix = translate_matrix * rotate_z_matrix * rotate_y_matrix * rotate_x_matrix * scale_matrix
        
        return result_matrix
    
    def set_world_position(self, op_path, world_x, world_y, world_z):
        """Set operator position in world space"""
        target_op = op(op_path)
        if not target_op:
            return False
        
        parent_op = target_op.parent()
        if parent_op and parent_op != root:
            # Get parent's world transform
            parent_world_matrix = self.get_world_transform_matrix(parent_op.path)
            
            # Calculate parent's inverse transform
            try:
                parent_inverse = parent_world_matrix.inverse()
                
                # Transform world position to parent's local space
                world_pos = tdu.Position(world_x, world_y, world_z)
                local_pos = parent_inverse * world_pos
                
                # Set local position
                target_op.par.tx = local_pos.x
                target_op.par.ty = local_pos.y
                target_op.par.tz = local_pos.z
                
            except:
                # Fallback to direct world coordinates if inverse fails
                target_op.par.tx = world_x
                target_op.par.ty = world_y
                target_op.par.tz = world_z
        else:
            # No parent or root parent, use world coordinates directly
            target_op.par.tx = world_x
            target_op.par.ty = world_y
            target_op.par.tz = world_z
        
        return True
    
    def align_to_target(self, source_op_path, target_op_path, alignment_type='position'):
        """Align one operator to another"""
        source_op = op(source_op_path)
        target_op = op(target_op_path)
        
        if not source_op or not target_op:
            return False
        
        if alignment_type == 'position':
            # Get target world position
            target_matrix = self.get_world_transform_matrix(target_op_path)
            target_position = target_matrix.decompose()['translate']
            
            # Set source to same world position
            self.set_world_position(source_op_path, 
                                  target_position.x, 
                                  target_position.y, 
                                  target_position.z)
        
        elif alignment_type == 'look_at':
            # Calculate look-at rotation
            source_matrix = self.get_world_transform_matrix(source_op_path)
            target_matrix = self.get_world_transform_matrix(target_op_path)
            
            source_pos = source_matrix.decompose()['translate']
            target_pos = target_matrix.decompose()['translate']
            
            # Calculate direction vector
            direction = target_pos - source_pos
            direction.normalize()
            
            # Calculate rotation angles
            import math
            ry = math.atan2(direction.x, direction.z) * 180 / math.pi
            rx = math.asin(-direction.y) * 180 / math.pi
            
            source_op.par.rx = rx
            source_op.par.ry = ry
        
        return True

# Global transform manager
transform_manager = TransformHierarchyManager()

# Usage examples
def setup_camera_tracking():
    """Set up camera to track a moving object"""
    # Get object's world position
    target_matrix = transform_manager.get_world_transform_matrix('/project1/geo1/target_object')
    target_pos = target_matrix.decompose()['translate']
    
    # Position camera relative to target
    camera_world_x = target_pos.x + 5
    camera_world_y = target_pos.y + 3
    camera_world_z = target_pos.z + 5
    
    transform_manager.set_world_position('/project1/cam1', 
                                       camera_world_x, 
                                       camera_world_y, 
                                       camera_world_z)
    
    # Make camera look at target
    transform_manager.align_to_target('/project1/cam1', 
                                    '/project1/geo1/target_object', 
                                    'look_at')

def create_orbital_formation(center_op_path, orbit_ops, radius=5):
    """Arrange operators in orbital formation around center"""
    center_matrix = transform_manager.get_world_transform_matrix(center_op_path)
    center_pos = center_matrix.decompose()['translate']
    
    import math
    angle_step = 360 / len(orbit_ops)
    
    for i, orbit_op_path in enumerate(orbit_ops):
        angle = math.radians(i * angle_step)
        
        orbit_x = center_pos.x + math.cos(angle) * radius
        orbit_z = center_pos.z + math.sin(angle) * radius
        orbit_y = center_pos.y
        
        transform_manager.set_world_position(orbit_op_path, orbit_x, orbit_y, orbit_z)
        transform_manager.align_to_target(orbit_op_path, center_op_path, 'look_at')
```

## Performance Optimization Patterns

### Efficient Operator Management

```python
class PerformanceOptimizedManager:
    """Performance-optimized operator management"""
    
    def __init__(self):
        self.op_cache = {}
        self.param_cache = {}
        self.last_frame_update = -1
    
    def cached_op(self, op_path):
        """Get cached operator reference"""
        if op_path not in self.op_cache:
            self.op_cache[op_path] = op(op_path)
        return self.op_cache[op_path]
    
    def cached_param_value(self, op_path, param_name, force_refresh=False):
        """Get cached parameter value"""
        cache_key = f"{op_path}.{param_name}"
        current_frame = absTime.frame
        
        if (force_refresh or 
            cache_key not in self.param_cache or 
            self.param_cache[cache_key]['frame'] != current_frame):
            
            target_op = self.cached_op(op_path)
            if target_op and hasattr(target_op.par, param_name):
                param = getattr(target_op.par, param_name)
                value = param.eval() if hasattr(param, 'eval') else param
                
                self.param_cache[cache_key] = {
                    'value': value,
                    'frame': current_frame
                }
            else:
                return None
        
        return self.param_cache[cache_key]['value']
    
    def batch_parameter_update(self, updates):
        """Update multiple parameters efficiently"""
        """
        updates format:
        [
            {'op_path': '/project1/geo1', 'param_name': 'tx', 'value': 1.0},
            {'op_path': '/project1/geo1', 'param_name': 'ty', 'value': 2.0},
            ...
        ]
        """
        grouped_updates = {}
        
        # Group updates by operator
        for update in updates:
            op_path = update['op_path']
            if op_path not in grouped_updates:
                grouped_updates[op_path] = []
            grouped_updates[op_path].append(update)
        
        # Apply grouped updates
        for op_path, op_updates in grouped_updates.items():
            target_op = self.cached_op(op_path)
            if target_op:
                for update in op_updates:
                    param_name = update['param_name']
                    value = update['value']
                    
                    if hasattr(target_op.par, param_name):
                        setattr(target_op.par, param_name, value)
                        
                        # Update cache
                        cache_key = f"{op_path}.{param_name}"
                        self.param_cache[cache_key] = {
                            'value': value,
                            'frame': absTime.frame
                        }
    
    def efficient_cook_chain(self, op_paths, parallel_groups=None):
        """Efficiently cook a chain of operators"""
        if parallel_groups:
            # Cook parallel groups first, then remaining in sequence
            for group in parallel_groups:
                for op_path in group:
                    target_op = self.cached_op(op_path)
                    if target_op:
                        target_op.cook()
            
            # Cook remaining ops not in parallel groups
            remaining_ops = [path for path in op_paths 
                           if not any(path in group for group in parallel_groups)]
            for op_path in remaining_ops:
                target_op = self.cached_op(op_path)
                if target_op:
                    target_op.cook()
        else:
            # Sequential cooking
            for op_path in op_paths:
                target_op = self.cached_op(op_path)
                if target_op:
                    target_op.cook()
    
    def cleanup_caches(self, max_age_frames=300):
        """Clean up old cache entries"""
        current_frame = absTime.frame
        
        # Clean parameter cache
        keys_to_remove = []
        for key, cache_entry in self.param_cache.items():
            if current_frame - cache_entry['frame'] > max_age_frames:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.param_cache[key]
        
        # Validate operator cache
        invalid_ops = []
        for op_path, cached_op in self.op_cache.items():
            if not cached_op or not cached_op.valid:
                invalid_ops.append(op_path)
        
        for op_path in invalid_ops:
            del self.op_cache[op_path]

# Global performance manager
perf_manager = PerformanceOptimizedManager()

# Usage examples
def efficient_animation_update():
    """Efficiently update multiple animated parameters"""
    current_time = absTime.seconds
    
    # Calculate new values
    updates = []
    for i in range(10):  # 10 objects
        op_path = f'/project1/geo{i+1}'
        
        # Calculate sine wave positions
        import math
        offset = i * 0.5
        x_pos = math.sin(current_time + offset) * 3
        y_pos = math.cos(current_time * 0.8 + offset) * 2
        
        updates.extend([
            {'op_path': op_path, 'param_name': 'tx', 'value': x_pos},
            {'op_path': op_path, 'param_name': 'ty', 'value': y_pos}
        ])
    
    # Apply all updates efficiently
    perf_manager.batch_parameter_update(updates)
    
    # Cook rendering chain efficiently
    render_chain = ['/project1/render1', '/project1/comp1', '/project1/out1']
    perf_manager.efficient_cook_chain(render_chain)

# Call cleanup periodically
def onFrameEnd():
    if absTime.frame % 100 == 0:  # Every 100 frames
        perf_manager.cleanup_caches()
```

## Real-World Integration Example

### Complete Performance System

```python
class LivePerformanceSystem:
    """Complete system for live performance control"""
    
    def __init__(self):
        self.safe_access = SafeOperatorAccess()
        self.param_animator = ParameterAnimationSystem()
        self.callback_manager = CallbackManager()
        self.transform_manager = TransformHierarchyManager()
        self.perf_manager = PerformanceOptimizedManager()
        
        self.audio_reactive_params = {}
        self.scene_presets = {}
        self.current_preset = None
    
    def setup_audio_reactive_system(self):
        """Set up comprehensive audio-reactive system"""
        # Register audio level callbacks
        self.callback_manager.register_chop_callback(
            '/project1/audio/levels', 
            self.on_audio_levels_changed
        )
        
        # Set up audio-reactive parameters
        self.audio_reactive_params = {
            'bass': {
                'targets': [
                    ('/project1/lights/strobe', 'dimmer'),
                    ('/project1/geo1', 'sx'),
                    ('/project1/geo1', 'sy')
                ],
                'multiplier': 2.0,
                'smoothing': 0.1
            },
            'mid': {
                'targets': [
                    ('/project1/cam1', 'ry'),
                    ('/project1/effects/blur', 'blur')
                ],
                'multiplier': 45.0,  # For rotation
                'smoothing': 0.05
            },
            'treble': {
                'targets': [
                    ('/project1/lights/rgb', 'colorr'),
                    ('/project1/lights/rgb', 'colorg'),
                    ('/project1/lights/rgb', 'colorb')
                ],
                'multiplier': 1.0,
                'smoothing': 0.2
            }
        }
    
    def on_audio_levels_changed(self, chop_op, changes, all_values):
        """Handle audio level changes"""
        for freq_band, config in self.audio_reactive_params.items():
            if freq_band in all_values:
                level = all_values[freq_band]
                smoothed_level = level * (1 - config['smoothing']) + \
                               config.get('last_level', 0) * config['smoothing']
                
                # Update all targets for this frequency band
                updates = []
                for op_path, param_name in config['targets']:
                    final_value = smoothed_level * config['multiplier']
                    updates.append({
                        'op_path': op_path,
                        'param_name': param_name,
                        'value': final_value
                    })
                
                self.perf_manager.batch_parameter_update(updates)
                config['last_level'] = smoothed_level
    
    def create_scene_preset(self, preset_name, preset_config):
        """Create a scene preset"""
        self.scene_presets[preset_name] = {
            'parameters': preset_config.get('parameters', []),
            'animations': preset_config.get('animations', []),
            'lighting_state': preset_config.get('lighting_state', {}),
            'camera_position': preset_config.get('camera_position', None)
        }
    
    def load_scene_preset(self, preset_name, transition_time=2.0):
        """Load a scene preset with smooth transition"""
        if preset_name not in self.scene_presets:
            debug(f"Preset '{preset_name}' not found")
            return False
        
        preset = self.scene_presets[preset_name]
        self.current_preset = preset_name
        
        # Apply parameter changes with animation
        for param_config in preset['parameters']:
            op_path = param_config['op_path']
            param_name = param_config['param_name']
            target_value = param_config['value']
            
            # Get current value
            current_value = self.perf_manager.cached_param_value(op_path, param_name)
            
            if current_value is not None:
                # Animate to target value
                self.param_animator.animate_parameter(op_path, param_name, {
                    'type': 'exponential',
                    'duration': transition_time,
                    'start_value': current_value,
                    'end_value': target_value,
                    'loop': False
                })
        
        # Apply lighting state
        if preset['lighting_state']:
            self.apply_lighting_state(preset['lighting_state'], transition_time)
        
        # Apply camera position
        if preset['camera_position']:
            camera_pos = preset['camera_position']
            self.transform_manager.set_world_position(
                '/project1/cam1',
                camera_pos['x'],
                camera_pos['y'],
                camera_pos['z']
            )
            
            # Animate camera orientation if specified
            if 'rx' in camera_pos:
                self.param_animator.animate_parameter('/project1/cam1', 'rx', {
                    'type': 'exponential',
                    'duration': transition_time,
                    'start_value': self.perf_manager.cached_param_value('/project1/cam1', 'rx'),
                    'end_value': camera_pos['rx'],
                    'loop': False
                })
        
        debug(f"Loading preset '{preset_name}' with {transition_time}s transition")
        return True
    
    def apply_lighting_state(self, lighting_state, transition_time):
        """Apply lighting configuration"""
        for light_path, light_config in lighting_state.items():
            for param_name, target_value in light_config.items():
                current_value = self.perf_manager.cached_param_value(light_path, param_name)
                
                if current_value is not None:
                    self.param_animator.animate_parameter(light_path, param_name, {
                        'type': 'linear',
                        'duration': transition_time,
                        'start_value': current_value,
                        'end_value': target_value,
                        'loop': False
                    })
    
    def update_system(self):
        """Main update loop - call from Execute DAT"""
        # Update all subsystems
        self.param_animator.update_animations()
        self.callback_manager.process_callbacks()
        
        # Periodic cleanup
        if absTime.frame % 300 == 0:  # Every 300 frames
            self.perf_manager.cleanup_caches()

# Global performance system
live_system = LivePerformanceSystem()

# Setup and usage
def initialize_performance_system():
    """Initialize the complete performance system"""
    live_system.setup_audio_reactive_system()
    
    # Create scene presets
    live_system.create_scene_preset('intro', {
        'parameters': [
            {'op_path': '/project1/geo1', 'param_name': 'sx', 'value': 1.0},
            {'op_path': '/project1/geo1', 'param_name': 'sy', 'value': 1.0},
            {'op_path': '/project1/lights/main', 'param_name': 'dimmer', 'value': 0.8}
        ],
        'camera_position': {'x': 0, 'y': 5, 'z': 10, 'rx': -15},
        'lighting_state': {
            '/project1/lights/rgb': {'colorr': 0.2, 'colorg': 0.4, 'colorb': 0.8}
        }
    })
    
    live_system.create_scene_preset('buildup', {
        'parameters': [
            {'op_path': '/project1/geo1', 'param_name': 'sx', 'value': 2.0},
            {'op_path': '/project1/geo1', 'param_name': 'sy', 'value': 2.0},
            {'op_path': '/project1/lights/main', 'param_name': 'dimmer', 'value': 1.0}
        ],
        'camera_position': {'x': 3, 'y': 8, 'z': 15, 'rx': -25},
        'lighting_state': {
            '/project1/lights/rgb': {'colorr': 0.8, 'colorg': 0.6, 'colorb': 0.2}
        }
    })

# Call from Execute DAT
def onFrameEnd():
    live_system.update_system()

# Call from button callbacks or MIDI triggers
def trigger_preset_change(preset_name):
    live_system.load_scene_preset(preset_name, transition_time=3.0)
```

---

## Performance Notes

- **Caching**: Use operator and parameter caching for frequently accessed values
- **Batch Updates**: Group parameter updates to minimize individual operator access
- **Selective Cooking**: Only cook operators that have actually changed
- **Memory Management**: Regularly clean up caches and expired references
- **Error Handling**: Always include robust error handling for production systems

## Cross-References

**Related Documentation:**
- [MODULE_td_Module](../PYTHON_/PY_td_Module.md) - Core API reference
- [PY_Working_with_OPs_in_Python](../PYTHON_/PY_Working_with_OPs_in_Python.md) - Basic operator manipulation
- [CLASS_OP_Class](../CLASSES_/CLASS_OP_Class.md) - Operator class methods
- [EX_OPS](./EX_OPS.md) - Basic operator examples

---

*This documentation provides advanced Python API patterns essential for complex TouchDesigner automation, real-time performance systems, and professional-grade interactive applications.*