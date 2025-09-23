"""
TouchDesigner UI Callbacks
Handles button presses, sliders, and other UI interactions.
"""


def onOffToOn(channel, sampleIndex, val, prev):
    """
    Button callback for momentary button press.
    Triggered when button changes from Off to On state.

    Args:
        channel: The channel that triggered the callback
        sampleIndex: Sample index in the channel
        val: Current value (1.0 for On)
        prev: Previous value (0.0 for Off)
    """
    try:
        button_name = channel.par.name

        if button_name == "play":
            handle_play_button()
        elif button_name == "stop":
            handle_stop_button()
        elif button_name == "record":
            handle_record_button()
        elif button_name == "reset":
            handle_reset_button()
        else:
            print(f"Unknown button pressed: {button_name}")

    except Exception as e:
        print(f"Button callback error: {e}")


def onOnToOff(channel, sampleIndex, val, prev):
    """
    Button callback for button release.
    Triggered when button changes from On to Off state.
    """
    try:
        button_name = channel.par.name
        print(f"Button released: {button_name}")

    except Exception as e:
        print(f"Button release callback error: {e}")


def onValueChange(channel, sampleIndex, val, prev):
    """
    Slider/parameter value change callback.
    Handles continuous parameter changes like sliders and knobs.

    Args:
        channel: The channel that changed
        sampleIndex: Sample index in the channel
        val: New value
        prev: Previous value
    """
    try:
        param_name = channel.par.name

        # Handle different parameter types
        if param_name.startswith("volume"):
            handle_volume_change(param_name, val)
        elif param_name.startswith("speed"):
            handle_speed_change(param_name, val)
        elif param_name.startswith("opacity"):
            handle_opacity_change(param_name, val)
        elif param_name.startswith("size"):
            handle_size_change(param_name, val)
        else:
            # Generic parameter handling
            handle_generic_parameter(param_name, val, prev)

    except Exception as e:
        print(f"Value change callback error: {e}")


def handle_play_button():
    """Handle play button press - start timeline or animation."""
    try:
        # Get timeline component
        timeline = op("timeline1")
        if timeline:
            timeline.par.play = True
            print("Timeline started")

        # Trigger other play-related actions
        project_manager = op("project_manager")
        if project_manager and hasattr(project_manager, "start_playback"):
            project_manager.start_playback()

    except Exception as e:
        print(f"Play button error: {e}")


def handle_stop_button():
    """Handle stop button press - stop timeline or animation."""
    try:
        timeline = op("timeline1")
        if timeline:
            timeline.par.play = False
            print("Timeline stopped")

        # Trigger other stop-related actions
        project_manager = op("project_manager")
        if project_manager and hasattr(project_manager, "stop_playback"):
            project_manager.stop_playback()

    except Exception as e:
        print(f"Stop button error: {e}")


def handle_record_button():
    """Handle record button press - start recording."""
    try:
        # Check if already recording
        record_state = op("record_state")
        if record_state and record_state.par.value0:
            print("Already recording, stopping...")
            stop_recording()
        else:
            print("Starting recording...")
            start_recording()

    except Exception as e:
        print(f"Record button error: {e}")


def handle_reset_button():
    """Handle reset button press - reset to initial state."""
    try:
        # Reset timeline
        timeline = op("timeline1")
        if timeline:
            timeline.par.play = False
            timeline.par.start = 0
            timeline.par.cuepoint = 0

        # Reset project manager
        project_manager = op("project_manager")
        if project_manager and hasattr(project_manager, "reset_project"):
            project_manager.reset_project()

        print("System reset completed")

    except Exception as e:
        print(f"Reset button error: {e}")


def start_recording():
    """Start recording functionality."""
    try:
        # Set recording state
        record_state = op("record_state")
        if record_state:
            record_state.par.value0 = 1

        # Start movie file out
        movie_out = op("moviefileout1")
        if movie_out:
            movie_out.par.record = True

        print("Recording started")

    except Exception as e:
        print(f"Start recording error: {e}")


def stop_recording():
    """Stop recording functionality."""
    try:
        # Clear recording state
        record_state = op("record_state")
        if record_state:
            record_state.par.value0 = 0

        # Stop movie file out
        movie_out = op("moviefileout1")
        if movie_out:
            movie_out.par.record = False

        print("Recording stopped")

    except Exception as e:
        print(f"Stop recording error: {e}")


def handle_volume_change(param_name: str, value: float):
    """Handle volume parameter changes."""
    try:
        # Apply volume to audio components
        audio_comps = op.findChildren(type=CHOP, name="*audio*")
        for comp in audio_comps:
            if hasattr(comp.par, "gain"):
                comp.par.gain = value

        print(f"Volume updated: {param_name} = {value:.2f}")

    except Exception as e:
        print(f"Volume change error: {e}")


def handle_speed_change(param_name: str, value: float):
    """Handle speed/rate parameter changes."""
    try:
        # Update timeline speed
        timeline = op("timeline1")
        if timeline and hasattr(timeline.par, "rate"):
            timeline.par.rate = value

        print(f"Speed updated: {param_name} = {value:.2f}")

    except Exception as e:
        print(f"Speed change error: {e}")


def handle_opacity_change(param_name: str, value: float):
    """Handle opacity/alpha parameter changes."""
    try:
        # Update visual components opacity
        visual_comps = op.findChildren(type=TOP)
        for comp in visual_comps:
            if hasattr(comp.par, "opacity"):
                comp.par.opacity = value

        print(f"Opacity updated: {param_name} = {value:.2f}")

    except Exception as e:
        print(f"Opacity change error: {e}")


def handle_size_change(param_name: str, value: float):
    """Handle size/scale parameter changes."""
    try:
        # Update transform components
        transform_comps = op.findChildren(type=TOP, name="*transform*")
        for comp in transform_comps:
            if hasattr(comp.par, "scale"):
                comp.par.scale = value

        print(f"Size updated: {param_name} = {value:.2f}")

    except Exception as e:
        print(f"Size change error: {e}")


def handle_generic_parameter(param_name: str, value: float, prev_value: float):
    """Handle generic parameter changes."""
    try:
        # Log parameter change
        change_amount = abs(value - prev_value)

        if change_amount > 0.01:  # Only log significant changes
            print(
                f"Parameter changed: {param_name} from {prev_value:.3f} to {value:.3f}"
            )

        # Store in project history if needed
        history_dat = op("parameter_history")
        if history_dat:
            timestamp = absTime.seconds
            history_dat.appendRow([timestamp, param_name, value])

    except Exception as e:
        print(f"Generic parameter error: {e}")


def onWhileOn(channel, sampleIndex, val, prev):
    """
    Callback triggered continuously while button is held down.
    Useful for continuous actions during button press.
    """
    try:
        button_name = channel.par.name

        if button_name == "increment":
            # Continuous increment while held
            increment_value()
        elif button_name == "scroll":
            # Continuous scrolling
            handle_scroll_action()

    except Exception as e:
        print(f"While-on callback error: {e}")


def increment_value():
    """Increment a counter or value continuously."""
    try:
        counter = op("counter1")
        if counter:
            current_val = counter.par.value0
            counter.par.value0 = current_val + 0.1

    except Exception as e:
        print(f"Increment error: {e}")


def handle_scroll_action():
    """Handle continuous scrolling action."""
    try:
        # Update scroll position
        scroll_pos = op("scroll_position")
        if scroll_pos:
            current_pos = scroll_pos.par.value0
            scroll_pos.par.value0 = current_pos + 1

    except Exception as e:
        print(f"Scroll action error: {e}")
