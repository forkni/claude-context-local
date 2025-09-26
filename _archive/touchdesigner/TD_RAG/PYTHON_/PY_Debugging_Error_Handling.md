---
category: PYTHON
document_type: examples
difficulty: intermediate
time_estimate: 45-60 minutes
operators:
- Error_DAT
- Info_CHOP
- Info_DAT
- Panel_CHOP
- Execute_DAT
- Text_DAT
concepts:
- python_debugging
- error_handling
- debugging_systems
- error_monitoring
- crash_prevention
- performance_monitoring
- python_debugging
prerequisites:
- PY_TouchDesigner_fundamentals
- PY_Extensions_Development
- PY_Working_with_OPs_in_Python
workflows:
- debugging_networks
- error_analysis
- python_debugging
- performance_monitoring
- crash_prevention
keywords:
- python debugging
- error handling
- touchdesigner debugging
- error monitoring
- crash recovery
- python errors
- debug systems
- error detection
- python logging
tags:
- python
- debugging
- errors
- monitoring
- systems
- advanced
relationships:
  PY_Extensions_Development: strong
  PY_Working_with_OPs_in_Python: strong
  PERF_Optimize: medium
  CLASS_Error_DAT: strong
related_docs:
- PY_Extensions_Development
- PY_Working_with_OPs_in_Python
- PERF_Optimize
- CLASS_Error_DAT
hierarchy:
  secondary: advanced_python
  tertiary: debugging_systems
question_patterns:
- Python debugging in TouchDesigner?
- How to handle errors in TouchDesigner Python?
- TouchDesigner error monitoring systems?
- Python crash recovery in TouchDesigner?
common_use_cases:
- debugging_networks
- error_analysis
- python_debugging
- performance_monitoring
---

# TouchDesigner Python Debugging & Error Handling

## 🎯 Quick Reference

**Purpose**: Advanced Python debugging and error handling systems for TouchDesigner
**Difficulty**: Intermediate
**Time to read**: 45-60 minutes
**Use for**: debugging_networks, error_analysis, python_debugging, performance_monitoring

## 🔗 Learning Path

**Prerequisites**: [TouchDesigner Python Fundamentals] → [Extensions Development] → [Working with OPs]
**This document**: PYTHON debugging and error handling systems
**Next steps**: [Performance Optimization] → [Complex System Integration]

## TouchDesigner Error Monitoring System

### Comprehensive Error Monitor Extension

```python
from typing import Dict, List, Optional, Any, Callable
try:
    from td import OP, COMP, DAT, CHOP
except ImportError:
    OP = COMP = DAT = CHOP = 'OP'  # Fallback for development

class TouchDesignerErrorMonitor:
    """Advanced error monitoring system for TouchDesigner projects"""
    
    def __init__(self, ownerComp: COMP):
        self.ownerComp: COMP = ownerComp
        self.error_dat: Optional[DAT] = None
        self.error_history: List[Dict] = []
        self.monitoring_active: bool = True
        self.max_history_size: int = 500
        self.setup_error_monitoring()
    
    def setup_error_monitoring(self) -> None:
        """Set up Error DAT and monitoring infrastructure"""
        try:
            # Create or find Error DAT
            self.error_dat = self.ownerComp.op('error_monitor')
            if not self.error_dat:
                self.error_dat = self.ownerComp.create(errorDAT, 'error_monitor')
                debug("Created Error DAT for monitoring")
            
            # Configure Error DAT parameters
            if hasattr(self.error_dat.par, 'maxlines'):
                self.error_dat.par.maxlines = 1000
            
            # Create status table for error summary
            self.status_table = self.ownerComp.op('error_status')
            if not self.status_table:
                self.status_table = self.ownerComp.create(tableDAT, 'error_status')
                self.initialize_status_table()
            
        except Exception as e:
            debug(f"Error setting up error monitoring: {str(e)}")
    
    def initialize_status_table(self) -> None:
        """Initialize error status summary table"""
        try:
            if self.status_table:
                self.status_table.clear()
                self.status_table.appendRow(['operator', 'error_type', 'count', 'last_seen'])
        except Exception as e:
            debug(f"Error initializing status table: {str(e)}")
    
    def get_current_errors(self) -> List[Dict[str, Any]]:
        """Get current errors from Error DAT"""
        if not self.error_dat or not self.error_dat.valid:
            return []
        
        errors = []
        for row in range(1, self.error_dat.numRows):  # Skip header row
            try:
                row_data = self.error_dat.row(row)
                if len(row_data) >= 4:
                    error_info = {
                        'operator': row_data[0].val,
                        'error_type': row_data[1].val,
                        'message': row_data[2].val,
                        'timestamp': row_data[3].val
                    }
                    errors.append(error_info)
            except Exception as e:
                debug(f"Error reading error data row {row}: {str(e)}")
                continue
        
        return errors
    
    def check_network_errors(self, network_path: str = '/') -> Dict[str, Any]:
        """Comprehensive network error checking with TouchDesigner operators"""
        try:
            network_op = op(network_path)
            if not network_op:
                debug(f"Network path not found: {network_path}")
                return {'errors': [], 'script_errors': [], 'total_count': 0}
            
            # Get all errors recursively
            all_errors = network_op.errors(recurse=True)
            script_errors = network_op.scriptErrors(recurse=True)
            
            debug(f"=== Error Report for {network_path} ===")
            debug(f"Total errors: {len(all_errors)}")
            debug(f"Script errors: {len(script_errors)}")
            
            # Report all errors with details
            for error in all_errors:
                debug(f"ERROR in {error['op'].path}: {error['text']}")
            
            # Report script-specific errors
            for script_error in script_errors:
                debug(f"SCRIPT ERROR in {script_error['op'].path}: {script_error['text']}")
            
            return {
                'errors': all_errors,
                'script_errors': script_errors,
                'total_count': len(all_errors) + len(script_errors)
            }
            
        except Exception as e:
            debug(f"Error checking network errors: {str(e)}")
            return {'errors': [], 'script_errors': [], 'total_count': 0}
    
    def log_error_state(self) -> None:
        """Log current error state for analysis"""
        if not self.monitoring_active:
            return
        
        try:
            current_errors = self.get_current_errors()
            
            if current_errors:
                debug(f"=== Current Error State ({len(current_errors)} errors) ===")
                for error in current_errors:
                    debug(f"{error['timestamp']}: {error['operator']} - {error['message']}")
            else:
                debug("No current errors detected")
            
            # Add to history
            self.error_history.append({
                'timestamp': absTime.seconds,
                'frame': absTime.frame,
                'error_count': len(current_errors),
                'errors': current_errors.copy()
            })
            
            # Keep history manageable
            if len(self.error_history) > self.max_history_size:
                self.error_history = self.error_history[-self.max_history_size // 2:]
                
            # Update status table
            self.update_error_status_table(current_errors)
            
        except Exception as e:
            debug(f"Error logging error state: {str(e)}")
    
    def update_error_status_table(self, current_errors: List[Dict]) -> None:
        """Update error status summary table"""
        try:
            if not self.status_table:
                return
            
            # Clear and reinitialize
            self.status_table.clear()
            self.status_table.appendRow(['operator', 'error_type', 'count', 'last_seen'])
            
            # Count errors by operator
            error_counts = {}
            for error in current_errors:
                key = f"{error['operator']}:{error['error_type']}"
                if key not in error_counts:
                    error_counts[key] = {
                        'operator': error['operator'],
                        'error_type': error['error_type'],
                        'count': 0,
                        'last_seen': error['timestamp']
                    }
                error_counts[key]['count'] += 1
                error_counts[key]['last_seen'] = max(error_counts[key]['last_seen'], error['timestamp'])
            
            # Add to table
            for error_info in error_counts.values():
                self.status_table.appendRow([
                    error_info['operator'],
                    error_info['error_type'],
                    str(error_info['count']),
                    error_info['last_seen']
                ])
                
        except Exception as e:
            debug(f"Error updating status table: {str(e)}")
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error history for patterns and trends"""
        if len(self.error_history) < 2:
            return {'message': 'Insufficient error history for pattern analysis'}
        
        try:
            # Find recurring errors
            error_frequency = {}
            recent_errors = self.error_history[-50:]  # Last 50 entries
            
            for history_entry in recent_errors:
                for error in history_entry['errors']:
                    error_key = f"{error['operator']}:{error['message']}"
                    error_frequency[error_key] = error_frequency.get(error_key, 0) + 1
            
            # Find patterns
            patterns = {
                'frequent_errors': [],
                'error_trends': {},
                'problematic_operators': set()
            }
            
            # Identify frequent errors (occurred more than 3 times)
            for error_key, frequency in error_frequency.items():
                if frequency > 3:
                    operator, message = error_key.split(':', 1)
                    patterns['frequent_errors'].append({
                        'operator': operator,
                        'message': message,
                        'frequency': frequency
                    })
                    patterns['problematic_operators'].add(operator)
            
            # Error trend analysis
            if len(self.error_history) >= 10:
                recent_count = sum(entry['error_count'] for entry in self.error_history[-5:])
                older_count = sum(entry['error_count'] for entry in self.error_history[-10:-5])
                
                if recent_count > older_count * 1.5:
                    patterns['error_trends']['trend'] = 'increasing'
                elif recent_count < older_count * 0.5:
                    patterns['error_trends']['trend'] = 'decreasing'
                else:
                    patterns['error_trends']['trend'] = 'stable'
                
                patterns['error_trends']['recent_avg'] = recent_count / 5
                patterns['error_trends']['older_avg'] = older_count / 5
            
            return patterns
            
        except Exception as e:
            debug(f"Error analyzing error patterns: {str(e)}")
            return {'error': f"Pattern analysis failed: {str(e)}"}
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary"""
        try:
            current_errors = self.get_current_errors()
            patterns = self.analyze_error_patterns()
            
            return {
                'current_error_count': len(current_errors),
                'total_history_entries': len(self.error_history),
                'monitoring_active': self.monitoring_active,
                'patterns': patterns,
                'recent_errors': current_errors[-10:] if current_errors else []  # Last 10 errors
            }
            
        except Exception as e:
            debug(f"Error getting error summary: {str(e)}")
            return {'error': f"Summary generation failed: {str(e)}"}


class TouchDesignerDebugLogger:
    """Enhanced debugging logger with TouchDesigner integration"""
    
    def __init__(self, ownerComp: COMP):
        self.ownerComp: COMP = ownerComp
        self.debug_levels = {
            'ERROR': 0,
            'WARNING': 1,
            'INFO': 2,
            'DEBUG': 3
        }
        self.current_level: int = 2  # INFO level by default
        self.debug_dat: Optional[DAT] = None
        self.setup_debug_output()
    
    def setup_debug_output(self) -> None:
        """Set up dedicated TouchDesigner debug output DAT"""
        try:
            self.debug_dat = self.ownerComp.op('debug_output')
            if not self.debug_dat:
                self.debug_dat = self.ownerComp.create(textDAT, 'debug_output')
                self.debug_dat.par.extension = 'txt'
                debug("Debug output DAT created")
        except Exception as e:
            debug(f"Error setting up debug output: {str(e)}")
    
    def log(self, message: str, level: str = 'INFO', source_op: Optional[OP] = None) -> None:
        """Enhanced logging with levels and TouchDesigner source tracking"""
        if self.debug_levels.get(level, 2) > self.current_level:
            return  # Skip if level is too detailed for current setting
        
        try:
            # Get caller information
            import inspect
            frame = inspect.currentframe().f_back
            caller_filename = frame.f_code.co_filename.split('\\')[-1]  # Get just filename
            caller_line = frame.f_lineno
            caller_function = frame.f_code.co_name
            
            # Format debug message
            timestamp = f"{absTime.seconds:.3f}"
            frame_info = f"F:{absTime.frame}"
            source_info = f"{caller_filename}:{caller_line} in {caller_function}()"
            
            if source_op and hasattr(source_op, 'path'):
                source_info += f" [{source_op.path}]"
            
            formatted_message = f"[{timestamp}|{frame_info}] {level}: {message}"
            formatted_source = f"    Source: {source_info}"
            
            # Output to textport
            debug(formatted_message)
            debug(formatted_source)
            
            # Also output to debug DAT
            if self.debug_dat and self.debug_dat.valid:
                current_text = self.debug_dat.text
                new_entry = f"{formatted_message}\n{formatted_source}\n"
                new_text = new_entry + current_text
                
                # Keep debug DAT manageable (last 2000 lines)
                lines = new_text.split('\n')
                if len(lines) > 2000:
                    lines = lines[:2000]
                    new_text = '\n'.join(lines)
                
                self.debug_dat.text = new_text
                
        except Exception as e:
            # Fallback to basic debug if enhanced logging fails
            debug(f"Enhanced logging failed, basic message: {message}")
            debug(f"Logging error: {str(e)}")
    
    def error(self, message: str, source_op: Optional[OP] = None) -> None:
        """Log error message"""
        self.log(message, 'ERROR', source_op)
    
    def warning(self, message: str, source_op: Optional[OP] = None) -> None:
        """Log warning message"""
        self.log(message, 'WARNING', source_op)
    
    def info(self, message: str, source_op: Optional[OP] = None) -> None:
        """Log info message"""
        self.log(message, 'INFO', source_op)
    
    def debug_msg(self, message: str, source_op: Optional[OP] = None) -> None:
        """Log debug message"""
        self.log(message, 'DEBUG', source_op)
    
    def trace_execution(self, func: Callable) -> Callable:
        """Decorator to trace TouchDesigner function execution"""
        def wrapper(*args, **kwargs):
            self.debug_msg(f"Entering {func.__name__} with args: {args}, kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                self.debug_msg(f"Exiting {func.__name__} with result: {result}")
                return result
            except Exception as e:
                self.error(f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper
    
    def dump_operator_state(self, op_path: str) -> None:
        """Dump comprehensive TouchDesigner operator state for debugging"""
        try:
            target_op = op(op_path)
            if not target_op:
                self.error(f"Operator not found: {op_path}")
                return
            
            self.info(f"=== Operator State Dump: {op_path} ===")
            self.info(f"Type: {target_op.type}, Family: {target_op.family}")
            self.info(f"Valid: {target_op.valid}, Display: {target_op.display}")
            
            if hasattr(target_op, 'cookCount'):
                self.info(f"Cook Count: {target_op.cookCount}")
            if hasattr(target_op, 'cookTime'):
                self.info(f"Cook Time: {target_op.cookTime}ms")
            
            # Dump key parameters (not all to avoid spam)
            self.info("Key Parameters:")
            key_params = ['active', 'bypass', 'display', 'render', 'export']
            for param_name in key_params:
                if hasattr(target_op.par, param_name):
                    try:
                        param = getattr(target_op.par, param_name)
                        value = param.eval()
                        self.info(f"  {param_name}: {value}")
                    except:
                        self.info(f"  {param_name}: <evaluation error>")
            
            # Dump connections
            self.info(f"Inputs: {len(target_op.inputs)}")
            for i, input_conn in enumerate(target_op.inputs):
                if input_conn:
                    self.info(f"  Input {i}: {input_conn.path}")
                else:
                    self.info(f"  Input {i}: <not connected>")
            
            # Output connection count
            total_output_connections = sum(len(output.connections) for output in target_op.outputs)
            self.info(f"Outputs: {len(target_op.outputs)} connectors, {total_output_connections} total connections")
            
        except Exception as e:
            self.error(f"Error dumping operator state for {op_path}: {str(e)}")
    
    def capture_python_stack(self) -> None:
        """Capture and log TouchDesigner Python call stack"""
        try:
            if hasattr(project, 'pythonStack'):
                stack_info = project.pythonStack()
                self.info("=== TouchDesigner Python Call Stack ===")
                self.info(stack_info)
            else:
                import traceback
                stack_info = traceback.format_stack()
                self.info("=== Python Call Stack ===")
                for line in stack_info:
                    self.info(line.strip())
        except Exception as e:
            self.error(f"Error capturing Python stack: {str(e)}")


class TouchDesignerInfoMonitor:
    """TouchDesigner Info monitoring system for performance and state tracking"""
    
    def __init__(self, ownerComp: COMP):
        self.ownerComp: COMP = ownerComp
        self.info_chops: Dict[str, CHOP] = {}
        self.info_dats: Dict[str, DAT] = {}
        self.panel_chops: Dict[str, CHOP] = {}
        self.monitoring_active: bool = True
    
    def create_info_monitor(self, target_op_path: str, monitor_name: Optional[str] = None) -> Optional[CHOP]:
        """Create Info CHOP to monitor TouchDesigner target operator"""
        try:
            if not monitor_name:
                monitor_name = f"info_{target_op_path.replace('/', '_').replace('.', '_')}"
            
            # Create Info CHOP
            info_chop = self.ownerComp.create(infoCHOP, monitor_name)
            if not info_chop:
                debug(f"Failed to create Info CHOP: {monitor_name}")
                return None
            
            # Configure to monitor target
            info_chop.par.op = target_op_path
            
            self.info_chops[target_op_path] = info_chop
            debug(f"Created Info CHOP monitor for {target_op_path}")
            return info_chop
            
        except Exception as e:
            debug(f"Error creating info monitor for {target_op_path}: {str(e)}")
            return None
    
    def create_panel_monitor(self, panel_comp_path: str, monitor_name: Optional[str] = None) -> Optional[CHOP]:
        """Create Panel CHOP to monitor TouchDesigner panel component"""
        try:
            if not monitor_name:
                monitor_name = f"panel_{panel_comp_path.replace('/', '_').replace('.', '_')}"
            
            panel_chop = self.ownerComp.create(panelCHOP, monitor_name)
            if not panel_chop:
                debug(f"Failed to create Panel CHOP: {monitor_name}")
                return None
            
            # Configure to monitor panel
            panel_chop.par.comp = panel_comp_path
            
            self.panel_chops[panel_comp_path] = panel_chop
            debug(f"Created Panel CHOP monitor for {panel_comp_path}")
            return panel_chop
            
        except Exception as e:
            debug(f"Error creating panel monitor for {panel_comp_path}: {str(e)}")
            return None
    
    def create_string_info_monitor(self, target_op_path: str, monitor_name: Optional[str] = None) -> Optional[DAT]:
        """Create Info DAT to monitor TouchDesigner string information"""
        try:
            if not monitor_name:
                monitor_name = f"info_dat_{target_op_path.replace('/', '_').replace('.', '_')}"
            
            info_dat = self.ownerComp.create(infoDAT, monitor_name)
            if not info_dat:
                debug(f"Failed to create Info DAT: {monitor_name}")
                return None
            
            # Configure to monitor target
            info_dat.par.op = target_op_path
            
            self.info_dats[target_op_path] = info_dat
            debug(f"Created Info DAT monitor for {target_op_path}")
            return info_dat
            
        except Exception as e:
            debug(f"Error creating string info monitor for {target_op_path}: {str(e)}")
            return None
    
    def get_monitored_values(self, target_op_path: str) -> Dict[str, Any]:
        """Get current monitored values for TouchDesigner target operator"""
        values = {}
        
        try:
            # Get Info CHOP values
            if target_op_path in self.info_chops:
                info_chop = self.info_chops[target_op_path]
                if info_chop.valid:
                    for chan in info_chop.chans():
                        chan_value = chan.vals[0] if len(chan.vals) > 0 else 0
                        values[f"chop_{chan.name}"] = chan_value
            
            # Get Info DAT values
            if target_op_path in self.info_dats:
                info_dat = self.info_dats[target_op_path]
                if info_dat.valid:
                    for row in range(info_dat.numRows):
                        if info_dat.numCols > 1:
                            key = info_dat.cell(row, 0)
                            value = info_dat.cell(row, 1)
                            if key:  # Only add if key is not empty
                                values[f"dat_{key}"] = value
            
            # Get Panel CHOP values
            if target_op_path in self.panel_chops:
                panel_chop = self.panel_chops[target_op_path]
                if panel_chop.valid:
                    for chan in panel_chop.chans():
                        chan_value = chan.vals[0] if len(chan.vals) > 0 else 0
                        values[f"panel_{chan.name}"] = chan_value
        
        except Exception as e:
            debug(f"Error getting monitored values for {target_op_path}: {str(e)}")
        
        return values
    
    def log_monitored_state(self) -> None:
        """Log current state of all monitored TouchDesigner operators"""
        if not self.monitoring_active:
            return
        
        try:
            debug("=== TouchDesigner Monitored Operator States ===")
            
            all_targets = set()
            all_targets.update(self.info_chops.keys())
            all_targets.update(self.info_dats.keys())
            all_targets.update(self.panel_chops.keys())
            
            for target_path in all_targets:
                values = self.get_monitored_values(target_path)
                if values:
                    debug(f"{target_path}:")
                    for key, value in values.items():
                        debug(f"  {key}: {value}")
                        
        except Exception as e:
            debug(f"Error logging monitored state: {str(e)}")
    
    def cleanup_invalid_monitors(self) -> None:
        """Clean up monitors for invalid or deleted operators"""
        try:
            # Clean up Info CHOPs
            invalid_chops = []
            for target_path, info_chop in self.info_chops.items():
                if not info_chop.valid or not op(target_path):
                    invalid_chops.append(target_path)
            
            for target_path in invalid_chops:
                debug(f"Removing invalid Info CHOP monitor: {target_path}")
                del self.info_chops[target_path]
            
            # Clean up Info DATs
            invalid_dats = []
            for target_path, info_dat in self.info_dats.items():
                if not info_dat.valid or not op(target_path):
                    invalid_dats.append(target_path)
            
            for target_path in invalid_dats:
                debug(f"Removing invalid Info DAT monitor: {target_path}")
                del self.info_dats[target_path]
            
            # Clean up Panel CHOPs
            invalid_panels = []
            for target_path, panel_chop in self.panel_chops.items():
                if not panel_chop.valid or not op(target_path):
                    invalid_panels.append(target_path)
            
            for target_path in invalid_panels:
                debug(f"Removing invalid Panel CHOP monitor: {target_path}")
                del self.panel_chops[target_path]
                
        except Exception as e:
            debug(f"Error cleaning up invalid monitors: {str(e)}")


# TouchDesigner Debugging Extension Example
class DebugSystemExt:
    """
    TouchDesigner Extension for comprehensive debugging system
    Place this in an Extension and initialize from Execute DAT
    """
    
    def __init__(self, ownerComp: COMP):
        self.ownerComp: COMP = ownerComp
        
        # Initialize debugging systems
        self.error_monitor = TouchDesignerErrorMonitor(ownerComp)
        self.debug_logger = TouchDesignerDebugLogger(ownerComp)
        self.info_monitor = TouchDesignerInfoMonitor(ownerComp)
        
        # System state
        self.monitoring_active = True
        self.last_check_time = absTime.seconds
        
        self.debug_logger.info("TouchDesigner Debug System Extension initialized")
    
    def StartMonitoring(self) -> None:
        """Start comprehensive monitoring"""
        self.monitoring_active = True
        self.debug_logger.info("Monitoring started")
    
    def StopMonitoring(self) -> None:
        """Stop monitoring"""
        self.monitoring_active = False
        self.debug_logger.info("Monitoring stopped")
    
    def LogErrorState(self) -> None:
        """Log current error state"""
        if self.monitoring_active:
            self.error_monitor.log_error_state()
    
    def CreateInfoMonitor(self, target_path: str) -> bool:
        """Create info monitor for target operator"""
        try:
            chop_monitor = self.info_monitor.create_info_monitor(target_path)
            dat_monitor = self.info_monitor.create_string_info_monitor(target_path)
            
            success = chop_monitor is not None or dat_monitor is not None
            if success:
                self.debug_logger.info(f"Info monitor created for {target_path}")
            else:
                self.debug_logger.warning(f"Failed to create info monitor for {target_path}")
            
            return success
            
        except Exception as e:
            self.debug_logger.error(f"Error creating info monitor: {str(e)}")
            return False
    
    def DumpOperatorState(self, op_path: str) -> None:
        """Dump comprehensive operator state"""
        self.debug_logger.dump_operator_state(op_path)
    
    def GetErrorSummary(self) -> Dict[str, Any]:
        """Get comprehensive error summary"""
        return self.error_monitor.get_error_summary()
    
    def PerformHealthCheck(self) -> Dict[str, Any]:
        """Perform system health check"""
        try:
            # Check errors
            network_errors = self.error_monitor.check_network_errors('/')
            
            # Check monitoring system health
            monitor_health = {
                'error_monitor_active': self.error_monitor.monitoring_active,
                'info_monitors_count': len(self.info_monitor.info_chops) + len(self.info_monitor.info_dats),
                'debug_logger_active': self.debug_logger.debug_dat.valid if self.debug_logger.debug_dat else False
            }
            
            # Performance indicators
            current_time = absTime.seconds
            performance = {
                'uptime': current_time - self.last_check_time,
                'current_frame': absTime.frame
            }
            
            health_report = {
                'timestamp': current_time,
                'errors': network_errors,
                'monitor_health': monitor_health,
                'performance': performance,
                'status': 'healthy' if network_errors['total_count'] == 0 else 'issues_detected'
            }
            
            self.debug_logger.info(f"Health check completed: {health_report['status']}")
            return health_report
            
        except Exception as e:
            self.debug_logger.error(f"Health check failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}


# Usage Examples and Utility Functions
def setup_comprehensive_debugging(owner_comp: COMP) -> DebugSystemExt:
    """Set up comprehensive TouchDesigner debugging system"""
    debug_system = DebugSystemExt(owner_comp)
    
    # Create monitors for common problem operators
    common_targets = [
        '/project1/render1',
        '/project1/out1',
        '/project1/geo1'
    ]
    
    for target in common_targets:
        if op(target):
            debug_system.CreateInfoMonitor(target)
    
    debug("Comprehensive debugging system set up")
    return debug_system

def emergency_debug_dump(target_paths: List[str]) -> None:
    """Emergency debug dump for critical operators"""
    debug("=== EMERGENCY DEBUG DUMP ===")
    
    temp_logger = TouchDesignerDebugLogger(root)
    
    for path in target_paths:
        temp_logger.dump_operator_state(path)
    
    # Also dump project-level information
    temp_logger.info(f"Project: {project.name}")
    temp_logger.info(f"Frame: {absTime.frame}, Time: {absTime.seconds}")
    temp_logger.info(f"Total operators: {len(root.findChildren(depth=10))}")
    
    temp_logger.capture_python_stack()
    
    debug("Emergency debug dump completed")

# Debugging decorator for TouchDesigner functions
def td_debug_trace(debug_logger: TouchDesignerDebugLogger):
    """Decorator factory for tracing TouchDesigner functions"""
    return debug_logger.trace_execution

# Example usage in Execute DAT
def onFrameEnd():
    """Example frame-end monitoring - place in Execute DAT"""
    # This would be used in an Execute DAT with proper extension reference
    try:
        # Access the debug extension
        if hasattr(me.parent().ext, 'DebugSystem'):
            debug_system = me.parent().ext.DebugSystem
            
            # Periodic error checking (every 60 frames = 1 second at 60fps)
            if absTime.frame % 60 == 0:
                debug_system.LogErrorState()
            
            # Health check every 10 seconds
            if absTime.frame % 600 == 0:
                health_report = debug_system.PerformHealthCheck()
                if health_report['status'] != 'healthy':
                    debug(f"Health check alert: {health_report}")
                    
    except Exception as e:
        debug(f"Error in debug monitoring: {str(e)}")
```

## Cross-References

**Related Documentation:**
- [PY_Extensions_Development](../PYTHON_/PY_Extensions_Development.md) - Extension development patterns
- [PY_Working_with_OPs_in_Python](../PYTHON_/PY_Working_with_OPs_in_Python.md) - Python operator manipulation
- [PERF_Optimize](../PERFORMANCE_/PERF_Optimize.md) - Performance optimization techniques
- [CLASS_Error_DAT](../CLASSES_/CLASS_Error_DAT.md) - Error DAT class reference

**Key Debugging Patterns:**
- **Error Monitoring System** - Automated error detection and logging
- **Enhanced Debug Logger** - Advanced logging with TouchDesigner integration  
- **Info Monitor System** - Performance and state tracking
- **Extension Integration** - Proper TouchDesigner extension debugging patterns

---

*This Python debugging guide provides comprehensive error handling and monitoring systems specifically designed for TouchDesigner development, with proper typing, error handling, and integration patterns.*