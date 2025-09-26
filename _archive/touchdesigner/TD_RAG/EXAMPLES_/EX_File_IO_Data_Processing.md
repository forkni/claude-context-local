---
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: 55-75 minutes
operators:
- File_In_DAT
- File_Out_DAT
- Folder_DAT
- Table_DAT
- Text_DAT
- Convert_DAT
- Script_DAT
- Execute_DAT
- Movie_File_In_TOP
- Movie_File_Out_TOP
- Audio_File_In_CHOP
- Audio_File_Out_CHOP
- Constant_DAT
concepts:
- file_input_output
- data_processing
- file_system_operations
- data_conversion
- batch_processing
- real_time_file_monitoring
- data_validation
- file_format_handling
- streaming_data
- data_persistence
prerequisites:
- TouchDesigner_fundamentals
- Python_scripting
- File_system_basics
workflows:
- data_import_export
- batch_file_processing
- real_time_data_monitoring
- media_file_management
- data_conversion_pipelines
keywords:
- file io
- data processing
- file import
- file export
- batch processing
- data conversion
- file monitoring
- media files
- csv processing
- json data
- xml parsing
tags:
- file
- data
- import
- export
- processing
- conversion
- batch
- monitoring
- media
- persistence
relationships:
  EX_Advanced_Python_API_Patterns: strong
  EX_Network_OSC_Communication: medium
  PY_Debugging_Error_Handling: medium
  REF_Troubleshooting_Guide: medium
  PERF_Optimize: medium
related_docs:
- EX_Advanced_Python_API_Patterns
- EX_Network_OSC_Communication
- PY_Debugging_Error_Handling
- REF_Troubleshooting_Guide
- PERF_Optimize
hierarchy:
  secondary: advanced_examples
  tertiary: file_data_processing
question_patterns:
- File I/O operations in TouchDesigner?
- How to process data files in TouchDesigner?
- Batch file processing examples?
- Real-time file monitoring in TouchDesigner?
common_use_cases:
- data_import_export
- batch_file_processing
- real_time_data_monitoring
- media_file_management
---

# File I/O and Data Processing in TouchDesigner

## 🎯 Quick Reference

**Purpose**: Advanced file I/O operations and data processing patterns for TouchDesigner
**Difficulty**: Advanced
**Time to read**: 55-75 minutes
**Use for**: data_import_export, batch_file_processing, real_time_data_monitoring

## 🔗 Learning Path

**Prerequisites**: [TouchDesigner Fundamentals] → [Python Scripting] → [File System Basics]
**This document**: EXAMPLES advanced file I/O and data processing
**Next steps**: Production data pipeline deployment

## File System Operations Manager

### Comprehensive File Management System

```python
import os
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

class FileSystemManager:
    """Advanced file system operations and monitoring"""
    
    def __init__(self):
        self.monitored_folders = {}
        self.file_processors = {}
        self.file_history = {}
        self.processing_queue = []
        self.setup_file_system()
    
    def setup_file_system(self):
        """Initialize file system management"""
        parent_comp = op('/project1') or root
        self.file_container = parent_comp.create(baseCOMP, 'file_system')
        
        # Create folder monitors
        self.folder_monitors = {}
        
        # Create file processing history
        self.processing_history = []
        
        debug("File System Manager initialized")
    
    def setup_folder_monitor(self, monitor_name, folder_path, config=None):
        """Set up real-time folder monitoring"""
        try:
            if config is None:
                config = {}
            
            container = self.file_container
            
            # Create Folder DAT for monitoring
            folder_dat = container.create(folderDAT, f"{monitor_name}_monitor")
            folder_dat.par.folder = folder_path
            folder_dat.par.refresh.pulse()  # Initial refresh
            
            # Create Execute DAT for change detection
            execute_dat = container.create(executeDAT, f"{monitor_name}_execute")
            execute_dat.text = self.generate_folder_callback_script(monitor_name)
            
            monitor_config = {
                'folder_dat': folder_dat,
                'execute_dat': execute_dat,
                'folder_path': folder_path,
                'config': config,
                'last_scan': absTime.seconds,
                'file_states': {},
                'active': True
            }
            
            self.monitored_folders[monitor_name] = monitor_config
            
            # Perform initial scan
            self.scan_folder(monitor_name)
            
            debug(f"Set up folder monitor: {monitor_name} -> {folder_path}")
            return monitor_config
            
        except Exception as e:
            debug(f"Error setting up folder monitor {monitor_name}: {str(e)}")
            return None
    
    def generate_folder_callback_script(self, monitor_name):
        """Generate callback script for folder monitoring"""
        script = f'''
# Folder monitoring callback for {monitor_name}

def onTableChange(dat):
    """Handle folder contents change"""
    try:
        if hasattr(mod, 'file_manager'):
            mod.file_manager.handle_folder_change('{monitor_name}')
        else:
            debug(f"Folder change detected in {monitor_name}")
    except Exception as e:
        debug(f"Error in folder callback for {monitor_name}: {{str(e)}}")
'''
        return script
    
    def handle_folder_change(self, monitor_name):
        """Handle changes in monitored folders"""
        try:
            if monitor_name not in self.monitored_folders:
                return
            
            debug(f"Folder change detected in {monitor_name}")
            self.scan_folder(monitor_name)
            
        except Exception as e:
            debug(f"Error handling folder change: {str(e)}")
    
    def scan_folder(self, monitor_name):
        """Scan folder for changes and process new/modified files"""
        try:
            if monitor_name not in self.monitored_folders:
                return
            
            monitor_config = self.monitored_folders[monitor_name]
            folder_dat = monitor_config['folder_dat']
            folder_path = monitor_config['folder_path']
            
            if not folder_dat or folder_dat.numRows < 2:
                return
            
            current_files = {}
            
            # Parse folder DAT contents (skip header row)
            for row in range(1, folder_dat.numRows):
                if folder_dat.numCols >= 4:
                    file_name = folder_dat.cell(row, 0)
                    file_size = folder_dat.cell(row, 2) 
                    file_modified = folder_dat.cell(row, 3)
                    
                    if file_name:
                        full_path = os.path.join(folder_path, file_name)
                        current_files[file_name] = {
                            'path': full_path,
                            'size': file_size,
                            'modified': file_modified,
                            'row_index': row
                        }
            
            # Compare with previous scan
            previous_files = monitor_config['file_states']
            
            # Check for new or modified files
            for file_name, file_info in current_files.items():
                if file_name not in previous_files:
                    # New file
                    self.handle_new_file(monitor_name, file_name, file_info)
                elif previous_files[file_name]['modified'] != file_info['modified']:
                    # Modified file
                    self.handle_modified_file(monitor_name, file_name, file_info)
            
            # Check for deleted files
            for file_name in previous_files:
                if file_name not in current_files:
                    self.handle_deleted_file(monitor_name, file_name)
            
            # Update file states
            monitor_config['file_states'] = current_files
            monitor_config['last_scan'] = absTime.seconds
            
        except Exception as e:
            debug(f"Error scanning folder {monitor_name}: {str(e)}")
    
    def handle_new_file(self, monitor_name, file_name, file_info):
        """Handle new file detection"""
        try:
            debug(f"New file detected in {monitor_name}: {file_name}")
            
            monitor_config = self.monitored_folders[monitor_name]
            config = monitor_config['config']
            
            # Auto-process if enabled
            if config.get('auto_process', False):
                self.queue_file_for_processing(file_info['path'], 'new_file')
            
            # Trigger custom handlers if registered
            if 'new_file_handler' in config:
                config['new_file_handler'](monitor_name, file_name, file_info)
                
        except Exception as e:
            debug(f"Error handling new file: {str(e)}")
    
    def handle_modified_file(self, monitor_name, file_name, file_info):
        """Handle file modification detection"""
        try:
            debug(f"Modified file detected in {monitor_name}: {file_name}")
            
            monitor_config = self.monitored_folders[monitor_name]
            config = monitor_config['config']
            
            # Auto-process if enabled
            if config.get('auto_process', False):
                self.queue_file_for_processing(file_info['path'], 'modified_file')
            
            # Trigger custom handlers if registered
            if 'modified_file_handler' in config:
                config['modified_file_handler'](monitor_name, file_name, file_info)
                
        except Exception as e:
            debug(f"Error handling modified file: {str(e)}")
    
    def handle_deleted_file(self, monitor_name, file_name):
        """Handle file deletion detection"""
        try:
            debug(f"Deleted file detected in {monitor_name}: {file_name}")
            
            monitor_config = self.monitored_folders[monitor_name]
            config = monitor_config['config']
            
            # Trigger custom handlers if registered
            if 'deleted_file_handler' in config:
                config['deleted_file_handler'](monitor_name, file_name)
                
        except Exception as e:
            debug(f"Error handling deleted file: {str(e)}")
    
    def queue_file_for_processing(self, file_path, operation_type):
        """Queue file for batch processing"""
        processing_item = {
            'file_path': file_path,
            'operation_type': operation_type,
            'timestamp': absTime.seconds,
            'status': 'queued'
        }
        
        self.processing_queue.append(processing_item)
        debug(f"Queued file for processing: {file_path}")
    
    def process_file_queue(self, max_files_per_frame=1):
        """Process queued files (call from main update loop)"""
        try:
            processed_count = 0
            
            while self.processing_queue and processed_count < max_files_per_frame:
                item = self.processing_queue.pop(0)
                
                try:
                    success = self.process_file(item['file_path'], item['operation_type'])
                    item['status'] = 'completed' if success else 'failed'
                    item['completed_time'] = absTime.seconds
                    
                    # Add to history
                    self.processing_history.append(item)
                    
                    # Keep history manageable
                    if len(self.processing_history) > 1000:
                        self.processing_history = self.processing_history[-500:]
                    
                    processed_count += 1
                    
                except Exception as e:
                    debug(f"Error processing file {item['file_path']}: {str(e)}")
                    item['status'] = 'error'
                    item['error'] = str(e)
                    self.processing_history.append(item)
            
        except Exception as e:
            debug(f"Error in file queue processing: {str(e)}")
    
    def process_file(self, file_path, operation_type):
        """Process individual file based on type"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Determine processor based on file extension
            if file_ext in ['.csv', '.tsv']:
                return self.process_csv_file(file_path)
            elif file_ext in ['.json']:
                return self.process_json_file(file_path)
            elif file_ext in ['.xml']:
                return self.process_xml_file(file_path)
            elif file_ext in ['.txt', '.log']:
                return self.process_text_file(file_path)
            elif file_ext in ['.wav', '.aiff', '.mp3']:
                return self.process_audio_file(file_path)
            elif file_ext in ['.mov', '.mp4', '.avi']:
                return self.process_video_file(file_path)
            else:
                debug(f"Unknown file type for processing: {file_ext}")
                return False
                
        except Exception as e:
            debug(f"Error processing file {file_path}: {str(e)}")
            return False
    
    def register_file_processor(self, file_extension, processor_func):
        """Register custom file processor for specific extensions"""
        self.file_processors[file_extension.lower()] = processor_func
        debug(f"Registered file processor for {file_extension}")

# Global file system manager
file_manager = FileSystemManager()

# Make available to module system
if hasattr(mod, '__dict__'):
    mod.file_manager = file_manager
```

### Data File Processing Systems

```python
class DataFileProcessor:
    """Advanced data file processing with validation and conversion"""
    
    def __init__(self):
        self.data_validators = {}
        self.conversion_pipelines = {}
        self.output_formatters = {}
        
    def process_csv_file(self, file_path, output_table_path=None):
        """Process CSV file with comprehensive error handling"""
        try:
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                debug(f"CSV file not found: {file_path}")
                return False
            
            # Create or get target table
            if output_table_path:
                target_table = op(output_table_path)
                if not target_table:
                    # Create table if it doesn't exist
                    parent_path = '/'.join(output_table_path.split('/')[:-1])
                    table_name = output_table_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_table = parent_op.create(tableDAT, table_name)
            else:
                # Create temporary table for processing
                parent_op = op('/project1') or root
                target_table = parent_op.create(tableDAT, 'temp_csv_data')
            
            # Configure File In DAT to read CSV
            file_in = target_table.par.file
            file_in.val = file_path
            
            # Refresh data
            target_table.par.loadonstartpulse.pulse()
            
            # Validate loaded data
            if target_table.numRows == 0:
                debug(f"No data loaded from CSV file: {file_path}")
                return False
            
            debug(f"Successfully loaded CSV: {file_path} ({target_table.numRows} rows, {target_table.numCols} cols)")
            
            # Apply data validation if configured
            if 'csv' in self.data_validators:
                validation_result = self.data_validators['csv'](target_table)
                if not validation_result['valid']:
                    debug(f"CSV validation failed: {validation_result['errors']}")
                    return False
            
            # Apply conversion pipeline if configured
            if 'csv' in self.conversion_pipelines:
                self.conversion_pipelines['csv'](target_table)
            
            return True
            
        except Exception as e:
            debug(f"Error processing CSV file {file_path}: {str(e)}")
            return False
    
    def process_json_file(self, file_path, output_table_path=None):
        """Process JSON file with structure analysis"""
        try:
            if not os.path.exists(file_path):
                debug(f"JSON file not found: {file_path}")
                return False
            
            # Read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Create target table
            if output_table_path:
                target_table = op(output_table_path)
                if not target_table:
                    parent_path = '/'.join(output_table_path.split('/')[:-1])
                    table_name = output_table_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_table = parent_op.create(tableDAT, table_name)
            else:
                parent_op = op('/project1') or root
                target_table = parent_op.create(tableDAT, 'temp_json_data')
            
            # Convert JSON to table format
            success = self.json_to_table(json_data, target_table)
            
            if success:
                debug(f"Successfully processed JSON: {file_path}")
                
                # Apply validation and conversion
                if 'json' in self.data_validators:
                    validation_result = self.data_validators['json'](target_table, json_data)
                    if not validation_result['valid']:
                        debug(f"JSON validation failed: {validation_result['errors']}")
                        return False
                
                if 'json' in self.conversion_pipelines:
                    self.conversion_pipelines['json'](target_table, json_data)
                
                return True
            else:
                debug(f"Failed to convert JSON to table: {file_path}")
                return False
                
        except json.JSONDecodeError as e:
            debug(f"JSON parsing error in {file_path}: {str(e)}")
            return False
        except Exception as e:
            debug(f"Error processing JSON file {file_path}: {str(e)}")
            return False
    
    def json_to_table(self, json_data, target_table):
        """Convert JSON data to TouchDesigner table format"""
        try:
            target_table.clear()
            
            if isinstance(json_data, list):
                # Array of objects - create table with object keys as columns
                if len(json_data) > 0 and isinstance(json_data[0], dict):
                    # Get all possible keys
                    all_keys = set()
                    for item in json_data:
                        if isinstance(item, dict):
                            all_keys.update(item.keys())
                    
                    all_keys = sorted(list(all_keys))
                    
                    # Create header row
                    target_table.appendRow(all_keys)
                    
                    # Add data rows
                    for item in json_data:
                        if isinstance(item, dict):
                            row_data = [str(item.get(key, '')) for key in all_keys]
                            target_table.appendRow(row_data)
                        else:
                            # Simple value
                            target_table.appendRow([str(item)])
                
                else:
                    # Array of simple values
                    target_table.appendRow(['value'])
                    for item in json_data:
                        target_table.appendRow([str(item)])
            
            elif isinstance(json_data, dict):
                # Single object - keys as first column, values as second
                target_table.appendRow(['key', 'value'])
                for key, value in json_data.items():
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value)
                    else:
                        value_str = str(value)
                    target_table.appendRow([str(key), value_str])
            
            else:
                # Single value
                target_table.appendRow(['value'])
                target_table.appendRow([str(json_data)])
            
            return True
            
        except Exception as e:
            debug(f"Error converting JSON to table: {str(e)}")
            return False
    
    def process_xml_file(self, file_path, output_table_path=None):
        """Process XML file with structure preservation"""
        try:
            if not os.path.exists(file_path):
                debug(f"XML file not found: {file_path}")
                return False
            
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Create target table
            if output_table_path:
                target_table = op(output_table_path)
                if not target_table:
                    parent_path = '/'.join(output_table_path.split('/')[:-1])
                    table_name = output_table_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_table = parent_op.create(tableDAT, table_name)
            else:
                parent_op = op('/project1') or root
                target_table = parent_op.create(tableDAT, 'temp_xml_data')
            
            # Convert XML to table format
            success = self.xml_to_table(root, target_table)
            
            if success:
                debug(f"Successfully processed XML: {file_path}")
                
                # Apply validation and conversion
                if 'xml' in self.data_validators:
                    validation_result = self.data_validators['xml'](target_table, root)
                    if not validation_result['valid']:
                        debug(f"XML validation failed: {validation_result['errors']}")
                        return False
                
                if 'xml' in self.conversion_pipelines:
                    self.conversion_pipelines['xml'](target_table, root)
                
                return True
            else:
                debug(f"Failed to convert XML to table: {file_path}")
                return False
                
        except ET.ParseError as e:
            debug(f"XML parsing error in {file_path}: {str(e)}")
            return False
        except Exception as e:
            debug(f"Error processing XML file {file_path}: {str(e)}")
            return False
    
    def xml_to_table(self, root_element, target_table):
        """Convert XML element tree to table format"""
        try:
            target_table.clear()
            
            # Create header row
            target_table.appendRow(['element_path', 'tag', 'text', 'attributes'])
            
            # Recursively process XML elements
            def process_element(element, path=''):
                current_path = f"{path}/{element.tag}" if path else element.tag
                
                # Get element text (strip whitespace)
                element_text = element.text.strip() if element.text else ''
                
                # Get attributes as JSON string
                attributes_str = json.dumps(element.attrib) if element.attrib else ''
                
                # Add row for this element
                target_table.appendRow([current_path, element.tag, element_text, attributes_str])
                
                # Process child elements
                for child in element:
                    process_element(child, current_path)
            
            process_element(root_element)
            return True
            
        except Exception as e:
            debug(f"Error converting XML to table: {str(e)}")
            return False
    
    def process_text_file(self, file_path, output_dat_path=None):
        """Process text/log files with line analysis"""
        try:
            if not os.path.exists(file_path):
                debug(f"Text file not found: {file_path}")
                return False
            
            # Create target DAT
            if output_dat_path:
                target_dat = op(output_dat_path)
                if not target_dat:
                    parent_path = '/'.join(output_dat_path.split('/')[:-1])
                    dat_name = output_dat_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_dat = parent_op.create(textDAT, dat_name)
            else:
                parent_op = op('/project1') or root
                target_dat = parent_op.create(textDAT, 'temp_text_data')
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Set content to DAT
            target_dat.text = content
            
            debug(f"Successfully loaded text file: {file_path} ({len(content)} characters)")
            
            # Apply text processing if configured
            if 'text' in self.conversion_pipelines:
                self.conversion_pipelines['text'](target_dat, content)
            
            return True
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                target_dat.text = content
                debug(f"Loaded text file with latin-1 encoding: {file_path}")
                return True
            except Exception as e:
                debug(f"Error reading text file with fallback encoding: {str(e)}")
                return False
        except Exception as e:
            debug(f"Error processing text file {file_path}: {str(e)}")
            return False
    
    def register_data_validator(self, file_type, validator_func):
        """Register data validation function for file type"""
        self.data_validators[file_type] = validator_func
        debug(f"Registered data validator for {file_type}")
    
    def register_conversion_pipeline(self, file_type, pipeline_func):
        """Register data conversion pipeline for file type"""
        self.conversion_pipelines[file_type] = pipeline_func
        debug(f"Registered conversion pipeline for {file_type}")

# Global data processor
data_processor = DataFileProcessor()

# Add processing methods to file manager
file_manager.process_csv_file = data_processor.process_csv_file
file_manager.process_json_file = data_processor.process_json_file
file_manager.process_xml_file = data_processor.process_xml_file
file_manager.process_text_file = data_processor.process_text_file
```

### Media File Processing System

```python
class MediaFileProcessor:
    """Advanced media file processing and management"""
    
    def __init__(self):
        self.media_cache = {}
        self.processing_operators = {}
        self.media_metadata = {}
        
    def process_audio_file(self, file_path, output_chop_path=None):
        """Process audio file with analysis and caching"""
        try:
            if not os.path.exists(file_path):
                debug(f"Audio file not found: {file_path}")
                return False
            
            # Create or get target CHOP
            if output_chop_path:
                target_chop = op(output_chop_path)
                if not target_chop:
                    parent_path = '/'.join(output_chop_path.split('/')[:-1])
                    chop_name = output_chop_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_chop = parent_op.create(audiofileinCHOP, chop_name)
            else:
                parent_op = file_manager.file_container
                target_chop = parent_op.create(audiofileinCHOP, 'temp_audio')
            
            # Configure audio file input
            target_chop.par.file = file_path
            target_chop.par.reload.pulse()
            
            # Wait for load (use delayed execution)
            def check_audio_loaded():
                if target_chop.chans():
                    debug(f"Successfully loaded audio: {file_path} ({len(target_chop.chans())} channels)")
                    
                    # Store metadata
                    metadata = self.extract_audio_metadata(target_chop, file_path)
                    self.media_metadata[file_path] = metadata
                    
                    # Apply audio processing if configured
                    if hasattr(self, 'audio_pipeline'):
                        self.audio_pipeline(target_chop, metadata)
                    
                    return True
                else:
                    debug(f"Failed to load audio file: {file_path}")
                    return False
            
            # Schedule load check
            run('check_audio_loaded()', delayFrames=10)
            
            return True
            
        except Exception as e:
            debug(f"Error processing audio file {file_path}: {str(e)}")
            return False
    
    def process_video_file(self, file_path, output_top_path=None):
        """Process video file with analysis and optimization"""
        try:
            if not os.path.exists(file_path):
                debug(f"Video file not found: {file_path}")
                return False
            
            # Create or get target TOP
            if output_top_path:
                target_top = op(output_top_path)
                if not target_top:
                    parent_path = '/'.join(output_top_path.split('/')[:-1])
                    top_name = output_top_path.split('/')[-1]
                    parent_op = op(parent_path) or op('/project1')
                    target_top = parent_op.create(moviefileinTOP, top_name)
            else:
                parent_op = file_manager.file_container
                target_top = parent_op.create(moviefileinTOP, 'temp_video')
            
            # Configure video file input
            target_top.par.file = file_path
            target_top.par.reload.pulse()
            
            def check_video_loaded():
                if target_top.width > 0 and target_top.height > 0:
                    debug(f"Successfully loaded video: {file_path} ({target_top.width}x{target_top.height})")
                    
                    # Store metadata
                    metadata = self.extract_video_metadata(target_top, file_path)
                    self.media_metadata[file_path] = metadata
                    
                    # Apply video processing if configured
                    if hasattr(self, 'video_pipeline'):
                        self.video_pipeline(target_top, metadata)
                    
                    return True
                else:
                    debug(f"Failed to load video file: {file_path}")
                    return False
            
            run('check_video_loaded()', delayFrames=10)
            
            return True
            
        except Exception as e:
            debug(f"Error processing video file {file_path}: {str(e)}")
            return False
    
    def extract_audio_metadata(self, audio_chop, file_path):
        """Extract metadata from loaded audio file"""
        try:
            metadata = {
                'file_path': file_path,
                'channels': len(audio_chop.chans()),
                'length_samples': audio_chop.chans()[0].vals.__len__() if audio_chop.chans() else 0,
                'sample_rate': audio_chop.rate if hasattr(audio_chop, 'rate') else 44100,
                'file_size': os.path.getsize(file_path),
                'load_time': absTime.seconds
            }
            
            if metadata['sample_rate'] > 0:
                metadata['duration_seconds'] = metadata['length_samples'] / metadata['sample_rate']
            else:
                metadata['duration_seconds'] = 0
            
            return metadata
            
        except Exception as e:
            debug(f"Error extracting audio metadata: {str(e)}")
            return {'file_path': file_path, 'error': str(e)}
    
    def extract_video_metadata(self, video_top, file_path):
        """Extract metadata from loaded video file"""
        try:
            metadata = {
                'file_path': file_path,
                'width': video_top.width,
                'height': video_top.height,
                'aspect_ratio': video_top.width / video_top.height if video_top.height > 0 else 1.0,
                'file_size': os.path.getsize(file_path),
                'load_time': absTime.seconds
            }
            
            # Try to get additional info from TOP
            if hasattr(video_top, 'movieLength'):
                metadata['length_frames'] = video_top.movieLength
            if hasattr(video_top, 'movieRate'):
                metadata['frame_rate'] = video_top.movieRate
                if 'length_frames' in metadata and metadata['frame_rate'] > 0:
                    metadata['duration_seconds'] = metadata['length_frames'] / metadata['frame_rate']
            
            return metadata
            
        except Exception as e:
            debug(f"Error extracting video metadata: {str(e)}")
            return {'file_path': file_path, 'error': str(e)}
    
    def create_media_playlist(self, media_files, playlist_name):
        """Create playlist from media files"""
        try:
            container = file_manager.file_container
            playlist_table = container.create(tableDAT, f"{playlist_name}_playlist")
            
            # Create playlist header
            playlist_table.appendRow(['index', 'file_path', 'duration', 'type', 'status'])
            
            for i, file_path in enumerate(media_files):
                if os.path.exists(file_path):
                    file_ext = Path(file_path).suffix.lower()
                    
                    if file_ext in ['.wav', '.aiff', '.mp3']:
                        media_type = 'audio'
                    elif file_ext in ['.mov', '.mp4', '.avi']:
                        media_type = 'video'
                    else:
                        media_type = 'unknown'
                    
                    # Get duration from metadata if available
                    duration = 0
                    if file_path in self.media_metadata:
                        duration = self.media_metadata[file_path].get('duration_seconds', 0)
                    
                    playlist_table.appendRow([
                        str(i),
                        file_path,
                        str(duration),
                        media_type,
                        'ready'
                    ])
                else:
                    playlist_table.appendRow([
                        str(i),
                        file_path,
                        '0',
                        'unknown',
                        'missing'
                    ])
            
            debug(f"Created media playlist: {playlist_name} with {len(media_files)} items")
            return playlist_table
            
        except Exception as e:
            debug(f"Error creating media playlist: {str(e)}")
            return None

# Global media processor
media_processor = MediaFileProcessor()

# Add media processing methods to file manager
file_manager.process_audio_file = media_processor.process_audio_file
file_manager.process_video_file = media_processor.process_video_file
```

### Data Export and Batch Operations

```python
class DataExportManager:
    """Advanced data export and batch operations"""
    
    def __init__(self):
        self.export_templates = {}
        self.batch_operations = {}
        self.export_history = []
        
    def export_table_to_csv(self, table_dat, output_file_path, options=None):
        """Export table DAT to CSV file"""
        try:
            if not table_dat:
                debug("No table provided for CSV export")
                return False
            
            if options is None:
                options = {}
            
            # Prepare data
            rows_to_export = []
            
            # Include header if requested
            include_header = options.get('include_header', True)
            start_row = 0 if include_header else 1
            
            for row in range(start_row, table_dat.numRows):
                row_data = []
                for col in range(table_dat.numCols):
                    cell_value = table_dat.cell(row, col)
                    row_data.append(str(cell_value))
                rows_to_export.append(row_data)
            
            # Write to CSV
            with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                delimiter = options.get('delimiter', ',')
                writer = csv.writer(csvfile, delimiter=delimiter)
                
                for row_data in rows_to_export:
                    writer.writerow(row_data)
            
            debug(f"Exported table to CSV: {output_file_path} ({len(rows_to_export)} rows)")
            
            # Record export
            self.record_export_operation(table_dat.path, output_file_path, 'csv', True)
            
            return True
            
        except Exception as e:
            debug(f"Error exporting table to CSV: {str(e)}")
            self.record_export_operation(table_dat.path if table_dat else 'unknown', output_file_path, 'csv', False, str(e))
            return False
    
    def export_table_to_json(self, table_dat, output_file_path, options=None):
        """Export table DAT to JSON file"""
        try:
            if not table_dat:
                debug("No table provided for JSON export")
                return False
            
            if options is None:
                options = {}
            
            # Prepare data structure
            export_format = options.get('format', 'array_of_objects')  # or 'simple_array'
            
            if export_format == 'array_of_objects':
                # First row as headers
                if table_dat.numRows < 2:
                    debug("Table has insufficient rows for array_of_objects format")
                    return False
                
                headers = []
                for col in range(table_dat.numCols):
                    headers.append(str(table_dat.cell(0, col)))
                
                data_array = []
                for row in range(1, table_dat.numRows):
                    row_object = {}
                    for col in range(table_dat.numCols):
                        col_header = headers[col] if col < len(headers) else f'col_{col}'
                        cell_value = table_dat.cell(row, col)
                        
                        # Try to convert to appropriate type
                        try:
                            # Try integer first
                            if '.' not in str(cell_value):
                                row_object[col_header] = int(cell_value)
                            else:
                                # Try float
                                row_object[col_header] = float(cell_value)
                        except ValueError:
                            # Keep as string
                            row_object[col_header] = str(cell_value)
                    
                    data_array.append(row_object)
                
                json_data = data_array
            
            else:
                # Simple 2D array
                json_data = []
                for row in range(table_dat.numRows):
                    row_data = []
                    for col in range(table_dat.numCols):
                        cell_value = str(table_dat.cell(row, col))
                        row_data.append(cell_value)
                    json_data.append(row_data)
            
            # Write JSON file
            with open(output_file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
            
            debug(f"Exported table to JSON: {output_file_path}")
            
            self.record_export_operation(table_dat.path, output_file_path, 'json', True)
            return True
            
        except Exception as e:
            debug(f"Error exporting table to JSON: {str(e)}")
            self.record_export_operation(table_dat.path if table_dat else 'unknown', output_file_path, 'json', False, str(e))
            return False
    
    def batch_export_tables(self, table_configs, base_output_dir):
        """Batch export multiple tables with different formats"""
        try:
            if not os.path.exists(base_output_dir):
                os.makedirs(base_output_dir)
            
            export_results = []
            
            for config in table_configs:
                table_path = config['table_path']
                table_dat = op(table_path)
                
                if not table_dat:
                    debug(f"Table not found: {table_path}")
                    export_results.append({'table': table_path, 'success': False, 'error': 'Table not found'})
                    continue
                
                export_format = config.get('format', 'csv')
                filename = config.get('filename') or f"{table_dat.name}.{export_format}"
                output_path = os.path.join(base_output_dir, filename)
                
                # Export based on format
                if export_format == 'csv':
                    success = self.export_table_to_csv(table_dat, output_path, config.get('options'))
                elif export_format == 'json':
                    success = self.export_table_to_json(table_dat, output_path, config.get('options'))
                else:
                    debug(f"Unknown export format: {export_format}")
                    success = False
                
                export_results.append({
                    'table': table_path,
                    'output_path': output_path,
                    'format': export_format,
                    'success': success
                })
            
            debug(f"Batch export completed: {sum(1 for r in export_results if r['success'])}/{len(export_results)} successful")
            return export_results
            
        except Exception as e:
            debug(f"Error in batch export: {str(e)}")
            return []
    
    def create_data_backup(self, backup_name, include_patterns=None):
        """Create comprehensive data backup"""
        try:
            timestamp = str(int(absTime.seconds))
            backup_dir = f"/project1/backups/{backup_name}_{timestamp}"
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Default patterns to include
            if include_patterns is None:
                include_patterns = ['*table*', '*data*', '*csv*', '*json*']
            
            backup_manifest = {
                'backup_name': backup_name,
                'timestamp': timestamp,
                'patterns': include_patterns,
                'files': []
            }
            
            # Find matching operators
            matching_ops = []
            for pattern in include_patterns:
                found_ops = op('/').findChildren(name=pattern, maxDepth=10)
                matching_ops.extend(found_ops)
            
            # Remove duplicates
            unique_ops = list(set(matching_ops))
            
            # Export each operator's data
            for target_op in unique_ops:
                if hasattr(target_op, 'numRows'):  # Table-like operator
                    output_filename = f"{target_op.name}_{target_op.path.replace('/', '_')}.csv"
                    output_path = os.path.join(backup_dir, output_filename)
                    
                    success = self.export_table_to_csv(target_op, output_path)
                    backup_manifest['files'].append({
                        'operator_path': target_op.path,
                        'output_file': output_filename,
                        'success': success
                    })
            
            # Save manifest
            manifest_path = os.path.join(backup_dir, 'backup_manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(backup_manifest, f, indent=2)
            
            debug(f"Created data backup: {backup_dir} with {len(backup_manifest['files'])} files")
            return backup_dir
            
        except Exception as e:
            debug(f"Error creating data backup: {str(e)}")
            return None
    
    def record_export_operation(self, source_path, output_path, export_format, success, error=None):
        """Record export operation in history"""
        operation = {
            'timestamp': absTime.seconds,
            'source_path': source_path,
            'output_path': output_path,
            'format': export_format,
            'success': success,
            'error': error
        }
        
        self.export_history.append(operation)
        
        # Keep history manageable
        if len(self.export_history) > 1000:
            self.export_history = self.export_history[-500:]
    
    def get_export_statistics(self):
        """Get export operation statistics"""
        if not self.export_history:
            return {'total_operations': 0}
        
        total_ops = len(self.export_history)
        successful_ops = sum(1 for op in self.export_history if op['success'])
        
        # Format statistics
        format_stats = {}
        for op in self.export_history:
            format_name = op['format']
            if format_name not in format_stats:
                format_stats[format_name] = {'total': 0, 'successful': 0}
            format_stats[format_name]['total'] += 1
            if op['success']:
                format_stats[format_name]['successful'] += 1
        
        return {
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'success_rate': successful_ops / total_ops if total_ops > 0 else 0,
            'format_statistics': format_stats
        }

# Global export manager
export_manager = DataExportManager()
```

## Complete Integration Example

### Production Data Pipeline System

```python
class ProductionDataPipeline:
    """Complete production data pipeline with monitoring"""
    
    def __init__(self):
        self.pipeline_config = {}
        self.active_pipelines = {}
        self.setup_data_pipeline()
    
    def setup_data_pipeline(self):
        """Set up complete data pipeline system"""
        debug("Setting up production data pipeline...")
        
        # Set up folder monitoring
        self.setup_data_monitoring()
        
        # Set up data validation
        self.setup_data_validation()
        
        # Set up conversion pipelines
        self.setup_conversion_pipelines()
        
        # Set up export automation
        self.setup_export_automation()
        
        debug("Production data pipeline ready!")
    
    def setup_data_monitoring(self):
        """Set up comprehensive data folder monitoring"""
        # Monitor input data folder
        input_config = {
            'auto_process': True,
            'new_file_handler': self.handle_new_data_file,
            'modified_file_handler': self.handle_modified_data_file
        }
        
        file_manager.setup_folder_monitor('data_input', '/project1/data/input', input_config)
        
        # Monitor media folder
        media_config = {
            'auto_process': True,
            'new_file_handler': self.handle_new_media_file
        }
        
        file_manager.setup_folder_monitor('media_input', '/project1/media/input', media_config)
    
    def setup_data_validation(self):
        """Set up data validation rules"""
        def validate_csv_data(table_dat):
            """Validate CSV data integrity"""
            errors = []
            
            # Check minimum requirements
            if table_dat.numRows < 2:
                errors.append("CSV file has no data rows")
            
            if table_dat.numCols < 1:
                errors.append("CSV file has no columns")
            
            # Check for empty headers
            for col in range(table_dat.numCols):
                header = str(table_dat.cell(0, col)).strip()
                if not header:
                    errors.append(f"Empty header in column {col}")
            
            return {'valid': len(errors) == 0, 'errors': errors}
        
        def validate_json_data(table_dat, json_data):
            """Validate JSON data structure"""
            errors = []
            
            if not json_data:
                errors.append("JSON data is empty")
            
            return {'valid': len(errors) == 0, 'errors': errors}
        
        # Register validators
        data_processor.register_data_validator('csv', validate_csv_data)
        data_processor.register_data_validator('json', validate_json_data)
    
    def setup_conversion_pipelines(self):
        """Set up data conversion pipelines"""
        def csv_pipeline(table_dat):
            """Process CSV data after loading"""
            debug(f"Processing CSV data: {table_dat.path}")
            
            # Example: Convert specific columns to parameters
            if table_dat.numRows > 1 and table_dat.numCols >= 2:
                # Use second row first column as a parameter value
                try:
                    value = float(table_dat.cell(1, 0))
                    target_op = op('/project1/control_values')
                    if target_op and hasattr(target_op.par, 'value1'):
                        target_op.par.value1 = value
                        debug(f"Set control value from CSV: {value}")
                except ValueError:
                    debug("Could not convert CSV value to float")
        
        def json_pipeline(table_dat, json_data):
            """Process JSON data after loading"""
            debug(f"Processing JSON data: {table_dat.path}")
            
            # Example: Apply JSON configuration to system
            if isinstance(json_data, dict):
                if 'settings' in json_data:
                    self.apply_json_settings(json_data['settings'])
        
        # Register pipelines
        data_processor.register_conversion_pipeline('csv', csv_pipeline)
        data_processor.register_conversion_pipeline('json', json_pipeline)
    
    def setup_export_automation(self):
        """Set up automated export processes"""
        # Example: Auto-export system state every 5 minutes
        def auto_export_system_state():
            timestamp = str(int(absTime.seconds))
            output_dir = f"/project1/exports/auto_{timestamp}"
            
            # Export key tables
            export_configs = [
                {
                    'table_path': '/project1/system_status',
                    'format': 'json',
                    'filename': 'system_status.json'
                },
                {
                    'table_path': '/project1/performance_data',
                    'format': 'csv',
                    'filename': 'performance_data.csv'
                }
            ]
            
            results = export_manager.batch_export_tables(export_configs, output_dir)
            debug(f"Auto-exported system data: {sum(1 for r in results if r['success'])}/{len(results)} successful")
        
        # Schedule periodic export (every 300 seconds = 5 minutes)
        run('auto_export_system_state()', delayMilliSeconds=300000)
    
    def handle_new_data_file(self, monitor_name, file_name, file_info):
        """Handle new data file detection"""
        debug(f"New data file handler: {file_name}")
        
        # Custom processing based on file type
        file_ext = Path(file_name).suffix.lower()
        
        if file_ext == '.json' and 'config' in file_name.lower():
            # Configuration file - process immediately
            self.process_config_file(file_info['path'])
        
        elif file_ext == '.csv' and 'sensor' in file_name.lower():
            # Sensor data - process and visualize
            self.process_sensor_data(file_info['path'])
    
    def handle_modified_data_file(self, monitor_name, file_name, file_info):
        """Handle modified data file detection"""
        debug(f"Modified data file handler: {file_name}")
        
        # Re-process modified files
        self.handle_new_data_file(monitor_name, file_name, file_info)
    
    def handle_new_media_file(self, monitor_name, file_name, file_info):
        """Handle new media file detection"""
        debug(f"New media file handler: {file_name}")
        
        # Auto-load media files into appropriate operators
        file_ext = Path(file_name).suffix.lower()
        
        if file_ext in ['.wav', '.mp3']:
            # Load audio file
            media_processor.process_audio_file(file_info['path'], '/project1/audio/input_chop')
        
        elif file_ext in ['.mov', '.mp4']:
            # Load video file
            media_processor.process_video_file(file_info['path'], '/project1/video/input_top')
    
    def process_config_file(self, config_file_path):
        """Process configuration file"""
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            
            debug(f"Processing config file: {config_file_path}")
            
            # Apply configuration
            if 'settings' in config_data:
                self.apply_json_settings(config_data['settings'])
            
            if 'parameters' in config_data:
                self.apply_parameter_settings(config_data['parameters'])
                
        except Exception as e:
            debug(f"Error processing config file: {str(e)}")
    
    def apply_json_settings(self, settings):
        """Apply JSON settings to TouchDesigner"""
        try:
            for setting_name, setting_value in settings.items():
                if setting_name == 'master_volume':
                    target_op = op('/project1/audio/master')
                    if target_op and hasattr(target_op.par, 'gain'):
                        target_op.par.gain = setting_value
                        debug(f"Applied setting: master_volume = {setting_value}")
                
                elif setting_name == 'camera_position':
                    if isinstance(setting_value, list) and len(setting_value) >= 3:
                        cam_op = op('/project1/cam1')
                        if cam_op:
                            cam_op.par.tx = setting_value[0]
                            cam_op.par.ty = setting_value[1]
                            cam_op.par.tz = setting_value[2]
                            debug(f"Applied camera position: {setting_value}")
                            
        except Exception as e:
            debug(f"Error applying JSON settings: {str(e)}")
    
    def apply_parameter_settings(self, parameters):
        """Apply parameter settings from configuration"""
        try:
            for param_config in parameters:
                operator_path = param_config.get('operator')
                param_name = param_config.get('parameter')
                value = param_config.get('value')
                
                if operator_path and param_name and value is not None:
                    target_op = op(operator_path)
                    if target_op and hasattr(target_op.par, param_name):
                        setattr(target_op.par, param_name, value)
                        debug(f"Applied parameter: {operator_path}.{param_name} = {value}")
                        
        except Exception as e:
            debug(f"Error applying parameter settings: {str(e)}")
    
    def process_sensor_data(self, sensor_file_path):
        """Process sensor data file"""
        try:
            # Load sensor data into table
            success = data_processor.process_csv_file(sensor_file_path, '/project1/sensor_data')
            
            if success:
                sensor_table = op('/project1/sensor_data')
                if sensor_table and sensor_table.numRows > 1:
                    # Extract latest sensor reading (last row)
                    last_row = sensor_table.numRows - 1
                    
                    if sensor_table.numCols >= 2:
                        try:
                            sensor_value = float(sensor_table.cell(last_row, 1))
                            
                            # Apply to visualization
                            viz_op = op('/project1/sensor_visualization')
                            if viz_op and hasattr(viz_op.par, 'intensity'):
                                viz_op.par.intensity = sensor_value
                                debug(f"Updated sensor visualization: {sensor_value}")
                                
                        except ValueError:
                            debug("Could not parse sensor value")
                            
        except Exception as e:
            debug(f"Error processing sensor data: {str(e)}")
    
    def get_pipeline_status(self):
        """Get comprehensive pipeline status"""
        status = {
            'monitored_folders': len(file_manager.monitored_folders),
            'processing_queue_size': len(file_manager.processing_queue),
            'export_statistics': export_manager.get_export_statistics(),
            'media_cache_size': len(media_processor.media_cache),
            'active_processors': len(data_processor.conversion_pipelines)
        }
        
        return status

# Global production pipeline
data_pipeline = ProductionDataPipeline()

# Main update functions
def update_file_systems():
    """Main update function for file systems"""
    try:
        # Process file queue
        file_manager.process_file_queue(max_files_per_frame=2)
        
        # Update folder monitors (refresh periodically)
        if absTime.frame % 300 == 0:  # Every 5 seconds at 60fps
            for monitor_name in file_manager.monitored_folders:
                file_manager.scan_folder(monitor_name)
        
    except Exception as e:
        debug(f"Error in file systems update: {str(e)}")

def get_system_status():
    """Get comprehensive system status"""
    return {
        'timestamp': absTime.seconds,
        'frame': absTime.frame,
        'file_system': {
            'monitored_folders': len(file_manager.monitored_folders),
            'processing_queue': len(file_manager.processing_queue)
        },
        'data_pipeline': data_pipeline.get_pipeline_status(),
        'export_stats': export_manager.get_export_statistics()
    }

# Convenience functions
def export_all_tables_csv(output_dir):
    """Export all table DATs to CSV files"""
    all_tables = op('/').findChildren(type=tableDAT, maxDepth=10)
    
    export_configs = []
    for table in all_tables:
        export_configs.append({
            'table_path': table.path,
            'format': 'csv',
            'filename': f"{table.name}.csv"
        })
    
    return export_manager.batch_export_tables(export_configs, output_dir)

def create_project_backup():
    """Create complete project data backup"""
    return export_manager.create_data_backup('project_backup')

# Initialize file system
debug("File I/O and Data Processing system initialized")
debug("Available functions:")
debug("  - update_file_systems() - Main update loop")
debug("  - export_all_tables_csv(dir) - Export all tables")
debug("  - create_project_backup() - Create data backup")
debug("  - get_system_status() - Get status info")
```

## Cross-References

**Related Documentation:**
- [EX_Advanced_Python_API_Patterns](./EX_Advanced_Python_API_Patterns.md) - Advanced Python integration
- [EX_Network_OSC_Communication](./EX_Network_OSC_Communication.md) - Network data exchange
- [PY_Debugging_Error_Handling](../PYTHON_/PY_Debugging_Error_Handling.md) - Python debugging systems
- [REF_Troubleshooting_Guide](../REFERENCE_/REF_Troubleshooting_Guide.md) - File I/O troubleshooting workflows
- [PERF_Optimize](../PERFORMANCE_/PERF_Optimize.md) - File processing optimization

**TouchDesigner Operators:**
- [File In DAT](../TD_/TD_OPERATORS/DAT/fileinDAT.md)
- [Folder DAT](../TD_/TD_OPERATORS/DAT/folderDAT.md)
- [Table DAT](../TD_/TD_OPERATORS/DAT/tableDAT.md)
- [Movie File In TOP](../TD_/TD_OPERATORS/TOP/moviefileinTOP.md)

---

*This comprehensive file I/O and data processing guide provides production-ready patterns for data import/export, real-time file monitoring, media processing, and automated data pipelines in TouchDesigner.*