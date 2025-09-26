---
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: 45-60 minutes
operators:
- Audio_Device_In_CHOP
- Audio_File_In_CHOP
- Audio_Spectrum_CHOP
- Audio_Analysis_CHOP
- Filter_CHOP
- Math_CHOP
- Lag_CHOP
- Limit_CHOP
- CHOP_Execute_DAT
- Timer_CHOP
- Fan_CHOP
- Constant_CHOP
- LFO_CHOP
concepts:
- audio_analysis
- frequency_analysis
- real_time_audio_processing
- audio_reactive_visuals
- beat_detection
- spectral_analysis
- audio_trigger_systems
- performance_optimization
prerequisites:
- CHOP_fundamentals
- Python_scripting
- Audio_processing_basics
workflows:
- audio_reactive_installations
- live_performance_systems
- music_visualization
- interactive_audio_systems
- real_time_audio_analysis
keywords:
- audio reactive
- frequency analysis
- beat detection
- spectrum analysis
- audio triggers
- real-time audio
- music visualization
- audio processing
- spectral data
- frequency bands
tags:
- audio
- reactive
- real-time
- analysis
- visualization
- performance
- interactive
- music
relationships:
  EX_Advanced_Python_API_Patterns: strong
  EX_GLSL_Shader_Integration_Patterns: strong
  PERF_Optimize: medium
  PY_Debugging_Error_Handling: medium
  REF_Troubleshooting_Guide: medium
related_docs:
- EX_Advanced_Python_API_Patterns
- EX_GLSL_Shader_Integration_Patterns
- PERF_Optimize
- PY_Debugging_Error_Handling
- REF_Troubleshooting_Guide
hierarchy:
  secondary: advanced_examples
  tertiary: audio_systems
question_patterns:
- Audio-reactive systems in TouchDesigner?
- How to analyze audio in real-time?
- Beat detection and audio triggers?
- Audio visualization techniques?
common_use_cases:
- audio_reactive_installations
- live_performance_systems
- music_visualization
- interactive_audio_systems
---

# Audio-Reactive Systems in TouchDesigner

## 🎯 Quick Reference

**Purpose**: Advanced audio-reactive system development with real-time analysis and visualization
**Difficulty**: Advanced
**Time to read**: 45-60 minutes
**Use for**: audio_reactive_installations, live_performance_systems, music_visualization

## 🔗 Learning Path

**Prerequisites**: [CHOP Fundamentals] → [Python Scripting] → [Audio Processing Basics]
**This document**: EXAMPLES advanced audio systems
**Next steps**: Live performance integration and optimization

## Audio Analysis and Processing Foundation

### Comprehensive Audio Analysis System

```python
class AudioAnalysisSystem:
    """Complete audio analysis system with multiple detection methods"""
    
    def __init__(self):
        self.audio_inputs = {}
        self.analysis_chains = {}
        self.detection_systems = {}
        self.history_buffers = {}
        self.setup_audio_analysis()
    
    def setup_audio_analysis(self):
        """Set up comprehensive audio analysis infrastructure"""
        # Create analysis container
        parent_comp = op('/project1') or root
        self.analysis_container = parent_comp.create(baseCOMP, 'audio_analysis')
        
        debug("Audio analysis system initialized")
    
    def create_audio_input_chain(self, input_name, source_config):
        """Create complete audio input and preprocessing chain"""
        try:
            container = self.analysis_container
            
            # Create audio input based on source type
            if source_config['type'] == 'device':
                audio_in = container.create(audiodeviceinCHOP, f"{input_name}_in")
                # Configure audio device input
                if 'device' in source_config:
                    audio_in.par.device = source_config['device']
                audio_in.par.sample = source_config.get('sample_rate', 44100)
                audio_in.par.channels = source_config.get('channels', 2)
                
            elif source_config['type'] == 'file':
                audio_in = container.create(audiofileinCHOP, f"{input_name}_in")
                if 'file_path' in source_config:
                    audio_in.par.file = source_config['file_path']
                audio_in.par.play = True
                
            else:
                debug(f"Unknown audio source type: {source_config['type']}")
                return None
            
            # Create preprocessing chain
            preprocessing_chain = self.create_preprocessing_chain(container, input_name, audio_in)
            
            # Create analysis chain
            analysis_chain = self.create_analysis_chain(container, input_name, preprocessing_chain)
            
            # Store references
            self.audio_inputs[input_name] = {
                'source': audio_in,
                'preprocessing': preprocessing_chain,
                'analysis': analysis_chain,
                'config': source_config
            }
            
            debug(f"Created audio input chain: {input_name}")
            return analysis_chain
            
        except Exception as e:
            debug(f"Error creating audio input chain {input_name}: {str(e)}")
            return None
    
    def create_preprocessing_chain(self, container, input_name, audio_source):
        """Create audio preprocessing chain"""
        chain = {}
        
        # Normalize audio levels
        normalize = container.create(mathCHOP, f"{input_name}_normalize")
        normalize.inputConnectors[0].connect(audio_source)
        normalize.par.combchops = 'maximum'
        normalize.par.gain = 1.0
        chain['normalize'] = normalize
        
        # Apply smoothing/filtering
        smooth = container.create(filterCHOP, f"{input_name}_smooth")
        smooth.inputConnectors[0].connect(normalize)
        smooth.par.filtertype = 'lowpass'
        smooth.par.cutoff = 20000  # Remove extreme high frequencies
        smooth.par.order = 2
        chain['smooth'] = smooth
        
        # Create mono mix for certain analyses
        mono = container.create(mathCHOP, f"{input_name}_mono")
        mono.inputConnectors[0].connect(smooth)
        mono.par.combchops = 'average'  # Average all channels to mono
        chain['mono'] = mono
        
        return chain
    
    def create_analysis_chain(self, container, input_name, preprocessing_chain):
        """Create comprehensive audio analysis chain"""
        analysis = {}
        
        # Get preprocessed audio
        stereo_source = preprocessing_chain['smooth']
        mono_source = preprocessing_chain['mono']
        
        # Spectrum analysis
        spectrum = container.create(audiospectrumCHOP, f"{input_name}_spectrum")
        spectrum.inputConnectors[0].connect(stereo_source)
        spectrum.par.method = 'fft'
        spectrum.par.resolution = 1024
        spectrum.par.overlap = 0.5
        spectrum.par.windowtype = 'hann'
        analysis['spectrum'] = spectrum
        
        # Frequency band analysis
        bands = self.create_frequency_bands(container, input_name, spectrum)
        analysis['bands'] = bands
        
        # RMS level analysis
        rms = container.create(mathCHOP, f"{input_name}_rms")
        rms.inputConnectors[0].connect(mono_source)
        rms.par.combchops = 'rms'
        analysis['rms'] = rms
        
        # Peak detection
        peak = container.create(mathCHOP, f"{input_name}_peak")
        peak.inputConnectors[0].connect(mono_source)
        peak.par.combchops = 'maximum'
        analysis['peak'] = peak
        
        # Audio analysis (onset detection, etc.)
        audio_analysis = container.create(audioanalysisCHOP, f"{input_name}_analysis")
        audio_analysis.inputConnectors[0].connect(mono_source)
        audio_analysis.par.onset = True
        audio_analysis.par.pitch = True
        analysis['analysis'] = audio_analysis
        
        return analysis
    
    def create_frequency_bands(self, container, input_name, spectrum_chop):
        """Create frequency band analysis from spectrum"""
        bands = {}
        
        # Define frequency bands (customizable)
        band_definitions = {
            'sub_bass': {'min': 20, 'max': 60},
            'bass': {'min': 60, 'max': 250},
            'low_mid': {'min': 250, 'max': 500},
            'mid': {'min': 500, 'max': 2000},
            'high_mid': {'min': 2000, 'max': 4000},
            'presence': {'min': 4000, 'max': 6000},
            'brilliance': {'min': 6000, 'max': 20000}
        }
        
        for band_name, freq_range in band_definitions.items():
            # Create math CHOP to extract frequency band
            band_math = container.create(mathCHOP, f"{input_name}_{band_name}")
            band_math.inputConnectors[0].connect(spectrum_chop)
            
            # Configure to extract specific frequency range
            # This is a simplified approach - in practice, you'd use more sophisticated filtering
            band_math.par.combchops = 'average'
            
            # Apply gain based on frequency importance
            band_math.par.gain = self.get_band_gain(band_name)
            
            bands[band_name] = band_math
        
        return bands
    
    def get_band_gain(self, band_name):
        """Get gain multiplier for frequency band"""
        # Adjust gains to balance different frequency ranges
        gain_map = {
            'sub_bass': 1.5,
            'bass': 2.0,
            'low_mid': 1.2,
            'mid': 1.0,
            'high_mid': 1.1,
            'presence': 0.9,
            'brilliance': 0.8
        }
        return gain_map.get(band_name, 1.0)

# Global audio analysis system
audio_system = AudioAnalysisSystem()
```

### Beat Detection and Rhythm Analysis

```python
class BeatDetectionSystem:
    """Advanced beat detection and rhythm analysis"""
    
    def __init__(self):
        self.beat_detectors = {}
        self.rhythm_patterns = {}
        self.tempo_tracking = {}
        
    def create_beat_detector(self, input_name, audio_analysis_chain, config=None):
        """Create comprehensive beat detection system"""
        if config is None:
            config = self.get_default_beat_config()
        
        container = audio_system.analysis_container
        detector = {}
        
        # Get audio source (typically bass/low-mid frequencies work best for beats)
        if 'bands' in audio_analysis_chain:
            bass_source = audio_analysis_chain['bands']['bass']
            kick_source = audio_analysis_chain['bands']['sub_bass']
        else:
            # Fallback to RMS if bands not available
            bass_source = audio_analysis_chain.get('rms')
            kick_source = bass_source
        
        if not bass_source:
            debug(f"No suitable audio source for beat detection: {input_name}")
            return None
        
        # Onset detection (primary beat detection)
        if 'analysis' in audio_analysis_chain:
            onset_source = audio_analysis_chain['analysis']
        else:
            # Create custom onset detection
            onset_source = self.create_custom_onset_detection(
                container, input_name, bass_source)
        
        detector['onset'] = onset_source
        
        # Beat tracking and tempo estimation
        beat_tracker = self.create_beat_tracker(container, input_name, onset_source, config)
        detector['tracker'] = beat_tracker
        
        # Rhythm pattern detection
        pattern_detector = self.create_rhythm_pattern_detector(
            container, input_name, beat_tracker, config)
        detector['patterns'] = pattern_detector
        
        # Beat prediction and stabilization
        predictor = self.create_beat_predictor(container, input_name, beat_tracker, config)
        detector['predictor'] = predictor
        
        self.beat_detectors[input_name] = detector
        debug(f"Created beat detector for: {input_name}")
        
        return detector
    
    def create_custom_onset_detection(self, container, input_name, audio_source):
        """Create custom onset detection algorithm"""
        onset_chain = {}
        
        # High-pass filter to remove low-frequency noise
        highpass = container.create(filterCHOP, f"{input_name}_onset_hp")
        highpass.inputConnectors[0].connect(audio_source)
        highpass.par.filtertype = 'highpass'
        highpass.par.cutoff = 80  # Remove very low frequencies
        onset_chain['highpass'] = highpass
        
        # Spectral flux calculation (difference between consecutive spectra)
        diff = container.create(mathCHOP, f"{input_name}_onset_diff")
        diff.inputConnectors[0].connect(highpass)
        diff.par.combchops = 'add'  # Simplified - real spectral flux is more complex
        diff.par.gain = 2.0
        onset_chain['diff'] = diff
        
        # Peak picking for onset detection
        peaks = container.create(mathCHOP, f"{input_name}_onset_peaks")
        peaks.inputConnectors[0].connect(diff)
        peaks.par.combchops = 'maximum'
        onset_chain['peaks'] = peaks
        
        # Threshold and trigger generation
        trigger = container.create(mathCHOP, f"{input_name}_onset_trigger")
        trigger.inputConnectors[0].connect(peaks)
        trigger.par.combchops = 'threshold'
        trigger.par.threshold = 0.3  # Adjustable onset sensitivity
        onset_chain['trigger'] = trigger
        
        return onset_chain['trigger']
    
    def create_beat_tracker(self, container, input_name, onset_source, config):
        """Create beat tracking system"""
        tracker = {}
        
        # Timer for beat intervals
        beat_timer = container.create(timerCHOP, f"{input_name}_beat_timer")
        beat_timer.par.initialize.pulse()  # Initialize timer
        tracker['timer'] = beat_timer
        
        # Tempo estimation based on onset intervals
        tempo_estimator = container.create(mathCHOP, f"{input_name}_tempo")
        tempo_estimator.inputConnectors[0].connect(onset_source)
        # This would typically involve more complex tempo tracking algorithms
        tempo_estimator.par.combchops = 'average'
        tracker['tempo'] = tempo_estimator
        
        # Beat phase tracking
        phase_tracker = container.create(mathCHOP, f"{input_name}_phase")
        phase_tracker.inputConnectors[0].connect(beat_timer)
        phase_tracker.par.combchops = 'add'
        tracker['phase'] = phase_tracker
        
        return tracker
    
    def create_rhythm_pattern_detector(self, container, input_name, beat_tracker, config):
        """Create rhythm pattern detection"""
        patterns = {}
        
        # Pattern buffer to store recent beat events
        pattern_buffer = container.create(delayCHOP, f"{input_name}_pattern_buffer")
        pattern_buffer.inputConnectors[0].connect(beat_tracker['timer'])
        pattern_buffer.par.delayunit = 'samples'
        pattern_buffer.par.delay = config.get('pattern_buffer_size', 32)
        patterns['buffer'] = pattern_buffer
        
        # Simple pattern recognition (can be extended)
        pattern_analyzer = container.create(mathCHOP, f"{input_name}_pattern_analyze")
        pattern_analyzer.inputConnectors[0].connect(pattern_buffer)
        pattern_analyzer.par.combchops = 'average'
        patterns['analyzer'] = pattern_analyzer
        
        return patterns
    
    def create_beat_predictor(self, container, input_name, beat_tracker, config):
        """Create beat prediction system"""
        predictor = {}
        
        # Predicted beat timing
        prediction = container.create(mathCHOP, f"{input_name}_beat_prediction")
        prediction.inputConnectors[0].connect(beat_tracker['phase'])
        prediction.par.combchops = 'add'
        predictor['prediction'] = prediction
        
        # Beat confidence estimation
        confidence = container.create(mathCHOP, f"{input_name}_beat_confidence")
        confidence.inputConnectors[0].connect(beat_tracker['tempo'])
        confidence.par.combchops = 'average'
        predictor['confidence'] = confidence
        
        return predictor
    
    def get_default_beat_config(self):
        """Get default beat detection configuration"""
        return {
            'sensitivity': 0.3,
            'tempo_range': {'min': 60, 'max': 180},  # BPM range
            'pattern_buffer_size': 32,
            'prediction_lookahead': 4  # beats to look ahead
        }

# Global beat detection system
beat_system = BeatDetectionSystem()
```

### Audio-Reactive Visual Control System

```python
class AudioReactiveController:
    """Comprehensive audio-reactive visual control system"""
    
    def __init__(self):
        self.reactive_mappings = {}
        self.visual_operators = {}
        self.control_chains = {}
        
    def create_reactive_mapping(self, mapping_name, config):
        """Create audio-reactive mapping with advanced controls"""
        mapping = {
            'name': mapping_name,
            'audio_source': config['audio_source'],
            'targets': config['targets'],
            'processing': config.get('processing', {}),
            'active': True,
            'history': []
        }
        
        # Create processing chain for this mapping
        processing_chain = self.create_mapping_processing_chain(mapping_name, config)
        mapping['chain'] = processing_chain
        
        self.reactive_mappings[mapping_name] = mapping
        debug(f"Created reactive mapping: {mapping_name}")
        
        return mapping
    
    def create_mapping_processing_chain(self, mapping_name, config):
        """Create processing chain for audio-reactive mapping"""
        container = audio_system.analysis_container
        chain = {}
        
        # Get audio source
        audio_source_path = config['audio_source']
        audio_source = op(audio_source_path)
        if not audio_source:
            debug(f"Audio source not found: {audio_source_path}")
            return None
        
        # Apply lag/smoothing
        if 'smoothing' in config['processing']:
            lag_chop = container.create(lagCHOP, f"{mapping_name}_lag")
            lag_chop.inputConnectors[0].connect(audio_source)
            lag_chop.par.lag = config['processing']['smoothing']
            chain['lag'] = lag_chop
            current_source = lag_chop
        else:
            current_source = audio_source
        
        # Apply scaling and offset
        if 'scale' in config['processing'] or 'offset' in config['processing']:
            math_chop = container.create(mathCHOP, f"{mapping_name}_scale")
            math_chop.inputConnectors[0].connect(current_source)
            
            if 'scale' in config['processing']:
                math_chop.par.gain = config['processing']['scale']
            if 'offset' in config['processing']:
                math_chop.par.add = config['processing']['offset']
                
            chain['scale'] = math_chop
            current_source = math_chop
        
        # Apply range limiting
        if 'min_value' in config['processing'] or 'max_value' in config['processing']:
            limit_chop = container.create(limitCHOP, f"{mapping_name}_limit")
            limit_chop.inputConnectors[0].connect(current_source)
            
            if 'min_value' in config['processing']:
                limit_chop.par.limitmin = True
                limit_chop.par.min = config['processing']['min_value']
            if 'max_value' in config['processing']:
                limit_chop.par.limitmax = True
                limit_chop.par.max = config['processing']['max_value']
                
            chain['limit'] = limit_chop
            current_source = limit_chop
        
        # Apply custom curve/response
        if 'response_curve' in config['processing']:
            curve_type = config['processing']['response_curve']
            curve_chop = container.create(mathCHOP, f"{mapping_name}_curve")
            curve_chop.inputConnectors[0].connect(current_source)
            
            if curve_type == 'exponential':
                curve_chop.par.combchops = 'power'
                curve_chop.par.power = config['processing'].get('curve_power', 2.0)
            elif curve_type == 'logarithmic':
                curve_chop.par.combchops = 'log'
            elif curve_type == 'sqrt':
                curve_chop.par.combchops = 'sqrt'
            
            chain['curve'] = curve_chop
            current_source = curve_chop
        
        chain['final_output'] = current_source
        return chain
    
    def update_reactive_mappings(self):
        """Update all active reactive mappings"""
        for mapping_name, mapping in self.reactive_mappings.items():
            if not mapping['active']:
                continue
                
            try:
                self.process_single_mapping(mapping)
            except Exception as e:
                debug(f"Error processing mapping {mapping_name}: {str(e)}")
    
    def process_single_mapping(self, mapping):
        """Process a single reactive mapping"""
        if not mapping['chain'] or 'final_output' not in mapping['chain']:
            return
        
        # Get processed audio value
        output_chop = mapping['chain']['final_output']
        if not output_chop or not output_chop.chans():
            return
        
        # Get current audio value
        audio_value = output_chop.chans()[0].vals[0] if len(output_chop.chans()[0].vals) > 0 else 0
        
        # Store in history for analysis
        mapping['history'].append({
            'timestamp': absTime.seconds,
            'frame': absTime.frame,
            'value': audio_value
        })
        
        # Keep history manageable
        if len(mapping['history']) > 1000:
            mapping['history'] = mapping['history'][-500:]
        
        # Apply to all targets
        for target_config in mapping['targets']:
            self.apply_to_target(audio_value, target_config, mapping)
    
    def apply_to_target(self, audio_value, target_config, mapping):
        """Apply audio value to target parameter"""
        try:
            target_op_path = target_config['operator']
            param_name = target_config['parameter']
            
            target_op = op(target_op_path)
            if not target_op or not hasattr(target_op.par, param_name):
                return
            
            # Apply additional target-specific processing
            final_value = audio_value
            
            if 'multiplier' in target_config:
                final_value *= target_config['multiplier']
            
            if 'target_min' in target_config or 'target_max' in target_config:
                target_min = target_config.get('target_min', 0.0)
                target_max = target_config.get('target_max', 1.0)
                final_value = target_min + (final_value * (target_max - target_min))
            
            # Set parameter value
            param = getattr(target_op.par, param_name)
            
            # Handle different parameter types
            if target_config.get('parameter_type') == 'pulse':
                # For pulse parameters, trigger on threshold
                threshold = target_config.get('pulse_threshold', 0.5)
                if audio_value > threshold:
                    param.pulse()
            else:
                # Standard parameter setting
                setattr(target_op.par, param_name, final_value)
                
        except Exception as e:
            debug(f"Error applying to target {target_config.get('operator', 'unknown')}: {str(e)}")

# Global audio-reactive controller
reactive_controller = AudioReactiveController()
```

### Complete Audio-Visual Performance System

```python
class AudioVisualPerformanceSystem:
    """Complete audio-visual performance system"""
    
    def __init__(self):
        self.performance_state = {
            'active': False,
            'current_scene': None,
            'audio_inputs': {},
            'visual_outputs': {},
            'mappings': {}
        }
        
        self.scenes = {}
        self.transitions = {}
        
    def initialize_performance_system(self):
        """Initialize complete performance system"""
        try:
            debug("Initializing audio-visual performance system...")
            
            # Create audio input chain
            self.setup_audio_inputs()
            
            # Create beat detection
            self.setup_beat_detection()
            
            # Create reactive mappings
            self.setup_reactive_mappings()
            
            # Create performance scenes
            self.setup_performance_scenes()
            
            self.performance_state['active'] = True
            debug("Audio-visual performance system initialized successfully")
            
        except Exception as e:
            debug(f"Error initializing performance system: {str(e)}")
    
    def setup_audio_inputs(self):
        """Set up audio input processing"""
        # Primary audio input (live or file)
        primary_config = {
            'type': 'device',  # or 'file'
            'device': 'default',
            'sample_rate': 44100,
            'channels': 2
        }
        
        primary_chain = audio_system.create_audio_input_chain('primary', primary_config)
        if primary_chain:
            self.performance_state['audio_inputs']['primary'] = primary_chain
            debug("Primary audio input created")
    
    def setup_beat_detection(self):
        """Set up beat detection system"""
        if 'primary' in self.performance_state['audio_inputs']:
            audio_chain = self.performance_state['audio_inputs']['primary']
            beat_detector = beat_system.create_beat_detector('primary', audio_chain)
            
            if beat_detector:
                self.performance_state['beat_detector'] = beat_detector
                debug("Beat detection system created")
    
    def setup_reactive_mappings(self):
        """Set up audio-reactive mappings"""
        # Bass-reactive scaling for visual elements
        bass_mapping = reactive_controller.create_reactive_mapping('bass_scale', {
            'audio_source': self.get_audio_path('primary', 'bands', 'bass'),
            'processing': {
                'smoothing': 0.1,
                'scale': 2.0,
                'min_value': 0.5,
                'max_value': 3.0,
                'response_curve': 'exponential',
                'curve_power': 1.5
            },
            'targets': [
                {
                    'operator': '/project1/visuals/main_geo',
                    'parameter': 'sx',
                    'multiplier': 1.0
                },
                {
                    'operator': '/project1/visuals/main_geo',
                    'parameter': 'sy',
                    'multiplier': 1.0
                }
            ]
        })
        
        # High-frequency reactive colors
        treble_mapping = reactive_controller.create_reactive_mapping('treble_color', {
            'audio_source': self.get_audio_path('primary', 'bands', 'brilliance'),
            'processing': {
                'smoothing': 0.05,
                'scale': 1.5,
                'response_curve': 'sqrt'
            },
            'targets': [
                {
                    'operator': '/project1/lighting/main_light',
                    'parameter': 'colorr',
                    'target_min': 0.2,
                    'target_max': 1.0
                },
                {
                    'operator': '/project1/lighting/main_light',
                    'parameter': 'colorg',
                    'target_min': 0.1,
                    'target_max': 0.8
                }
            ]
        })
        
        # Beat-triggered effects
        beat_mapping = reactive_controller.create_reactive_mapping('beat_triggers', {
            'audio_source': self.get_beat_trigger_path(),
            'processing': {
                'scale': 1.0
            },
            'targets': [
                {
                    'operator': '/project1/effects/strobe',
                    'parameter': 'trigger',
                    'parameter_type': 'pulse',
                    'pulse_threshold': 0.7
                },
                {
                    'operator': '/project1/effects/particle_burst',
                    'parameter': 'reset',
                    'parameter_type': 'pulse',
                    'pulse_threshold': 0.8
                }
            ]
        })
        
        self.performance_state['mappings'] = {
            'bass_scale': bass_mapping,
            'treble_color': treble_mapping,
            'beat_triggers': beat_mapping
        }
        
        debug("Audio-reactive mappings created")
    
    def setup_performance_scenes(self):
        """Set up performance scenes with different audio-reactive behaviors"""
        # Scene 1: Ambient
        self.scenes['ambient'] = {
            'name': 'Ambient',
            'mappings': {
                'bass_scale': {'scale_multiplier': 0.5, 'smoothing_override': 0.3},
                'treble_color': {'scale_multiplier': 0.8},
                'beat_triggers': {'active': False}
            },
            'visual_params': {
                '/project1/lighting/main_light': {'dimmer': 0.6, 'colorb': 0.8},
                '/project1/effects/ambient_particles': {'active': True}
            }
        }
        
        # Scene 2: High Energy
        self.scenes['high_energy'] = {
            'name': 'High Energy',
            'mappings': {
                'bass_scale': {'scale_multiplier': 2.0, 'smoothing_override': 0.05},
                'treble_color': {'scale_multiplier': 1.5},
                'beat_triggers': {'active': True, 'threshold_override': 0.5}
            },
            'visual_params': {
                '/project1/lighting/main_light': {'dimmer': 1.0, 'colorb': 0.2},
                '/project1/effects/strobe': {'intensity': 0.8},
                '/project1/effects/particle_burst': {'size': 2.0}
            }
        }
        
        # Scene 3: Breakdown
        self.scenes['breakdown'] = {
            'name': 'Breakdown',
            'mappings': {
                'bass_scale': {'scale_multiplier': 0.3, 'response_curve_override': 'linear'},
                'treble_color': {'scale_multiplier': 0.4},
                'beat_triggers': {'active': True, 'threshold_override': 0.9}
            },
            'visual_params': {
                '/project1/lighting/main_light': {'dimmer': 0.3},
                '/project1/effects/minimal_glow': {'active': True}
            }
        }
    
    def get_audio_path(self, input_name, analysis_type, band_name=None):
        """Get path to specific audio analysis component"""
        if input_name not in self.performance_state['audio_inputs']:
            return None
        
        analysis_chain = self.performance_state['audio_inputs'][input_name]
        
        if analysis_type == 'bands' and band_name:
            if 'bands' in analysis_chain and band_name in analysis_chain['bands']:
                return analysis_chain['bands'][band_name].path
        elif analysis_type in analysis_chain:
            return analysis_chain[analysis_type].path
        
        return None
    
    def get_beat_trigger_path(self):
        """Get path to beat trigger output"""
        if 'beat_detector' not in self.performance_state:
            return None
        
        beat_detector = self.performance_state['beat_detector']
        if 'predictor' in beat_detector and 'prediction' in beat_detector['predictor']:
            return beat_detector['predictor']['prediction'].path
        
        return None
    
    def switch_scene(self, scene_name, transition_time=2.0):
        """Switch to different performance scene"""
        if scene_name not in self.scenes:
            debug(f"Scene not found: {scene_name}")
            return False
        
        debug(f"Switching to scene: {scene_name}")
        
        scene = self.scenes[scene_name]
        
        # Apply scene-specific mapping modifications
        for mapping_name, mapping_overrides in scene['mappings'].items():
            if mapping_name in self.performance_state['mappings']:
                self.apply_mapping_overrides(mapping_name, mapping_overrides)
        
        # Apply visual parameter changes
        for op_path, params in scene['visual_params'].items():
            target_op = op(op_path)
            if target_op:
                for param_name, value in params.items():
                    if hasattr(target_op.par, param_name):
                        setattr(target_op.par, param_name, value)
        
        self.performance_state['current_scene'] = scene_name
        return True
    
    def apply_mapping_overrides(self, mapping_name, overrides):
        """Apply scene-specific overrides to mapping"""
        mapping = self.performance_state['mappings'].get(mapping_name)
        if not mapping:
            return
        
        # Store original config if not already stored
        if 'original_config' not in mapping:
            mapping['original_config'] = mapping['processing'].copy()
        
        # Apply overrides
        for override_key, override_value in overrides.items():
            if override_key == 'active':
                mapping['active'] = override_value
            elif override_key == 'scale_multiplier':
                original_scale = mapping['original_config'].get('scale', 1.0)
                mapping['processing']['scale'] = original_scale * override_value
            elif override_key == 'smoothing_override':
                mapping['processing']['smoothing'] = override_value
            elif override_key.endswith('_override'):
                base_key = override_key.replace('_override', '')
                mapping['processing'][base_key] = override_value
    
    def update_performance_system(self):
        """Main update loop for performance system"""
        if not self.performance_state['active']:
            return
        
        try:
            # Update reactive mappings
            reactive_controller.update_reactive_mappings()
            
            # Additional performance monitoring could go here
            
        except Exception as e:
            debug(f"Error in performance system update: {str(e)}")
    
    def get_system_status(self):
        """Get comprehensive system status"""
        status = {
            'active': self.performance_state['active'],
            'current_scene': self.performance_state['current_scene'],
            'audio_inputs_active': len(self.performance_state['audio_inputs']),
            'mappings_active': sum(1 for m in self.performance_state['mappings'].values() if m['active']),
            'beat_detection_active': 'beat_detector' in self.performance_state
        }
        
        return status

# Global audio-visual performance system
av_performance = AudioVisualPerformanceSystem()

# Convenience functions for live control
def init_audio_system():
    """Initialize the complete audio system"""
    av_performance.initialize_performance_system()

def switch_to_scene(scene_name):
    """Switch to performance scene"""
    return av_performance.switch_scene(scene_name)

def get_performance_status():
    """Get current performance system status"""
    return av_performance.get_system_status()

def emergency_audio_stop():
    """Emergency stop for audio system"""
    av_performance.performance_state['active'] = False
    debug("Audio system emergency stop activated")

# Main update function - call from Execute DAT
def update_audio_systems():
    """Main update function for all audio systems"""
    av_performance.update_performance_system()

# Example usage and setup
def setup_live_performance_example():
    """Complete example setup for live performance"""
    debug("Setting up live performance example...")
    
    # Initialize the system
    init_audio_system()
    
    # Start with ambient scene
    switch_to_scene('ambient')
    
    debug("Live performance system ready!")
    debug("Available scenes: ambient, high_energy, breakdown")
    debug("Use switch_to_scene('scene_name') to change scenes")
    debug("Use get_performance_status() to check system status")
```

## Performance Optimization for Audio Systems

### Audio System Performance Monitor

```python
class AudioPerformanceMonitor:
    """Monitor and optimize audio system performance"""
    
    def __init__(self):
        self.performance_data = {}
        self.optimization_suggestions = []
        
    def analyze_audio_chain_performance(self, chain_name, audio_chain):
        """Analyze performance of audio processing chain"""
        performance_info = {
            'chain_name': chain_name,
            'total_cook_time': 0,
            'operator_count': 0,
            'slowest_operators': [],
            'recommendations': []
        }
        
        # Analyze each operator in the chain
        for stage_name, stage_ops in audio_chain.items():
            if isinstance(stage_ops, dict):
                # Multiple operators in this stage
                for op_name, stage_op in stage_ops.items():
                    if stage_op and hasattr(stage_op, 'cookTime'):
                        cook_time = stage_op.cookTime
                        performance_info['total_cook_time'] += cook_time
                        performance_info['operator_count'] += 1
                        
                        if cook_time > 5.0:  # Operators taking more than 5ms
                            performance_info['slowest_operators'].append({
                                'path': stage_op.path,
                                'cook_time': cook_time,
                                'stage': f"{stage_name}.{op_name}"
                            })
            else:
                # Single operator
                if stage_ops and hasattr(stage_ops, 'cookTime'):
                    cook_time = stage_ops.cookTime
                    performance_info['total_cook_time'] += cook_time
                    performance_info['operator_count'] += 1
                    
                    if cook_time > 5.0:
                        performance_info['slowest_operators'].append({
                            'path': stage_ops.path,
                            'cook_time': cook_time,
                            'stage': stage_name
                        })
        
        # Generate recommendations
        if performance_info['total_cook_time'] > 16.67:  # More than one frame at 60fps
            performance_info['recommendations'].append(
                f"Chain taking {performance_info['total_cook_time']:.2f}ms - consider optimization"
            )
        
        if len(performance_info['slowest_operators']) > 0:
            performance_info['recommendations'].append(
                f"Found {len(performance_info['slowest_operators'])} slow operators - check parameters"
            )
        
        return performance_info
    
    def optimize_audio_chain(self, chain_name):
        """Apply automatic optimizations to audio chain"""
        optimizations_applied = []
        
        if chain_name not in audio_system.analysis_chains:
            return optimizations_applied
        
        audio_chain = audio_system.analysis_chains[chain_name]
        
        # Optimize spectrum analysis
        if 'analysis' in audio_chain and 'spectrum' in audio_chain['analysis']:
            spectrum_op = audio_chain['analysis']['spectrum']
            if spectrum_op and hasattr(spectrum_op.par, 'resolution'):
                current_res = spectrum_op.par.resolution.eval()
                if current_res > 1024:
                    spectrum_op.par.resolution = 1024
                    optimizations_applied.append("Reduced spectrum resolution to 1024")
        
        # Optimize filter settings
        for stage_name, stage_content in audio_chain.items():
            if isinstance(stage_content, dict):
                for op_name, stage_op in stage_content.items():
                    if stage_op and 'filter' in stage_op.type.lower():
                        if hasattr(stage_op.par, 'order') and stage_op.par.order.eval() > 4:
                            stage_op.par.order = 4
                            optimizations_applied.append(f"Reduced filter order for {stage_op.path}")
        
        return optimizations_applied

# Global audio performance monitor
audio_perf_monitor = AudioPerformanceMonitor()

# Performance monitoring function
def monitor_audio_performance():
    """Monitor all audio system performance"""
    debug("=== Audio System Performance Report ===")
    
    for input_name, audio_chain in audio_system.audio_inputs.items():
        analysis_chain = audio_chain.get('analysis', {})
        perf_info = audio_perf_monitor.analyze_audio_chain_performance(input_name, analysis_chain)
        
        debug(f"Chain: {perf_info['chain_name']}")
        debug(f"  Total cook time: {perf_info['total_cook_time']:.2f}ms")
        debug(f"  Operator count: {perf_info['operator_count']}")
        
        if perf_info['slowest_operators']:
            debug("  Slow operators:")
            for slow_op in perf_info['slowest_operators']:
                debug(f"    {slow_op['path']}: {slow_op['cook_time']:.2f}ms")
        
        if perf_info['recommendations']:
            debug("  Recommendations:")
            for rec in perf_info['recommendations']:
                debug(f"    - {rec}")
```

## Cross-References

**Related Documentation:**
- [EX_Advanced_Python_API_Patterns](./EX_Advanced_Python_API_Patterns.md) - Advanced Python integration
- [EX_GLSL_Shader_Integration_Patterns](./EX_GLSL_Shader_Integration_Patterns.md) - Audio-reactive shaders
- [PERF_Optimize](../PERFORMANCE_/PERF_Optimize.md) - Audio performance optimization
- [PY_Debugging_Error_Handling](../PYTHON_/PY_Debugging_Error_Handling.md) - Python debugging systems
- [REF_Troubleshooting_Guide](../REFERENCE_/REF_Troubleshooting_Guide.md) - Systematic debugging workflows

**TouchDesigner Operators:**
- [Audio Device In CHOP](../TD_/TD_OPERATORS/CHOP/audiodeviceinCHOP.md)
- [Audio Spectrum CHOP](../TD_/TD_OPERATORS/CHOP/audiospectrumCHOP.md)
- [Audio Analysis CHOP](../TD_/TD_OPERATORS/CHOP/audioanalysisCHOP.md)

---

*This comprehensive audio-reactive systems guide provides production-ready patterns for real-time audio analysis, beat detection, and audio-visual performance systems in TouchDesigner.*