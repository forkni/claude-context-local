"""
TouchDesigner Data Processing Module
Handles data transformation, filtering, and analysis for TouchDesigner projects.
"""

import math
from typing import List, Optional, Tuple, Union


def process_audio_data(audio_input: List[float], sample_rate: int = 44100) -> dict:
    """
    Process audio data to extract useful information.

    Args:
        audio_input: List of audio samples
        sample_rate: Audio sample rate in Hz

    Returns:
        Dictionary with processed audio information
    """
    try:
        if not audio_input:
            return {"error": "No audio data provided"}

        # Calculate basic audio statistics
        amplitude = max(abs(sample) for sample in audio_input)
        rms = math.sqrt(sum(sample**2 for sample in audio_input) / len(audio_input))

        # Detect peaks
        peaks = detect_audio_peaks(audio_input, threshold=amplitude * 0.7)

        # Calculate frequency domain information (simplified)
        dominant_freq = estimate_dominant_frequency(audio_input, sample_rate)

        return {
            "amplitude": amplitude,
            "rms": rms,
            "peak_count": len(peaks),
            "dominant_frequency": dominant_freq,
            "sample_count": len(audio_input),
            "duration": len(audio_input) / sample_rate,
        }

    except Exception as e:
        return {"error": f"Audio processing failed: {e}"}


def detect_audio_peaks(data: List[float], threshold: float = 0.5) -> List[int]:
    """
    Detect peaks in audio data above specified threshold.

    Args:
        data: Audio sample data
        threshold: Minimum amplitude for peak detection

    Returns:
        List of sample indices where peaks occur
    """
    peaks = []
    for i in range(1, len(data) - 1):
        if data[i] > threshold and data[i] > data[i - 1] and data[i] > data[i + 1]:
            peaks.append(i)
    return peaks


def estimate_dominant_frequency(data: List[float], sample_rate: int) -> float:
    """
    Estimate the dominant frequency in audio data using zero-crossing rate.

    Args:
        data: Audio sample data
        sample_rate: Sample rate in Hz

    Returns:
        Estimated dominant frequency in Hz
    """
    try:
        # Simple zero-crossing rate estimation
        zero_crossings = 0
        for i in range(1, len(data)):
            if (data[i] >= 0) != (data[i - 1] >= 0):
                zero_crossings += 1

        # Estimate frequency from zero crossings
        freq = (zero_crossings * sample_rate) / (2 * len(data))
        return freq

    except Exception:
        return 0.0


def smooth_data(data: List[float], window_size: int = 5) -> List[float]:
    """
    Apply moving average smoothing to data.

    Args:
        data: Input data to smooth
        window_size: Size of smoothing window

    Returns:
        Smoothed data array
    """
    try:
        if window_size <= 1:
            return data.copy()

        smoothed = []
        half_window = window_size // 2

        for i in range(len(data)):
            start = max(0, i - half_window)
            end = min(len(data), i + half_window + 1)
            window_data = data[start:end]
            smoothed.append(sum(window_data) / len(window_data))

        return smoothed

    except Exception as e:
        print(f"Smoothing error: {e}")
        return data.copy()


def normalize_data(
    data: List[float], target_min: float = 0.0, target_max: float = 1.0
) -> List[float]:
    """
    Normalize data to specified range.

    Args:
        data: Input data to normalize
        target_min: Target minimum value
        target_max: Target maximum value

    Returns:
        Normalized data array
    """
    try:
        if not data:
            return []

        data_min = min(data)
        data_max = max(data)
        data_range = data_max - data_min

        if data_range == 0:
            # All values are the same
            return [target_min] * len(data)

        # Normalize to target range
        normalized = []
        target_range = target_max - target_min

        for value in data:
            norm_value = ((value - data_min) / data_range) * target_range + target_min
            normalized.append(norm_value)

        return normalized

    except Exception as e:
        print(f"Normalization error: {e}")
        return data.copy()


def filter_outliers(data: List[float], threshold: float = 2.0) -> List[float]:
    """
    Remove outliers from data using standard deviation method.

    Args:
        data: Input data
        threshold: Number of standard deviations for outlier threshold

    Returns:
        Data with outliers removed
    """
    try:
        if len(data) < 3:
            return data.copy()

        mean_val = sum(data) / len(data)
        variance = sum((x - mean_val) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance)

        filtered = []
        for value in data:
            if abs(value - mean_val) <= threshold * std_dev:
                filtered.append(value)

        return filtered

    except Exception as e:
        print(f"Outlier filtering error: {e}")
        return data.copy()


def calculate_derivative(data: List[float], dt: float = 1.0) -> List[float]:
    """
    Calculate numerical derivative of data.

    Args:
        data: Input data
        dt: Time step between samples

    Returns:
        Derivative data
    """
    try:
        if len(data) < 2:
            return []

        derivative = []
        for i in range(1, len(data)):
            diff = (data[i] - data[i - 1]) / dt
            derivative.append(diff)

        return derivative

    except Exception as e:
        print(f"Derivative calculation error: {e}")
        return []


def interpolate_data(data: List[float], target_length: int) -> List[float]:
    """
    Interpolate data to target length using linear interpolation.

    Args:
        data: Input data
        target_length: Desired output length

    Returns:
        Interpolated data
    """
    try:
        if not data or target_length <= 0:
            return []

        if len(data) == target_length:
            return data.copy()

        if len(data) == 1:
            return [data[0]] * target_length

        interpolated = []
        scale_factor = (len(data) - 1) / (target_length - 1)

        for i in range(target_length):
            pos = i * scale_factor
            lower_idx = int(pos)
            upper_idx = min(lower_idx + 1, len(data) - 1)

            if lower_idx == upper_idx:
                interpolated.append(data[lower_idx])
            else:
                fraction = pos - lower_idx
                interpolated_val = (
                    data[lower_idx] * (1 - fraction) + data[upper_idx] * fraction
                )
                interpolated.append(interpolated_val)

        return interpolated

    except Exception as e:
        print(f"Interpolation error: {e}")
        return data.copy()


def analyze_motion_data(position_data: List[Tuple[float, float, float]]) -> dict:
    """
    Analyze 3D motion data to extract movement characteristics.

    Args:
        position_data: List of (x, y, z) position tuples

    Returns:
        Dictionary with motion analysis results
    """
    try:
        if len(position_data) < 2:
            return {"error": "Insufficient motion data"}

        # Calculate velocities
        velocities = []
        distances = []

        for i in range(1, len(position_data)):
            prev_pos = position_data[i - 1]
            curr_pos = position_data[i]

            # Calculate distance moved
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            dz = curr_pos[2] - prev_pos[2]

            distance = math.sqrt(dx * dx + dy * dy + dz * dz)
            distances.append(distance)
            velocities.append(distance)  # Assuming unit time steps

        # Calculate motion statistics
        total_distance = sum(distances)
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0
        max_velocity = max(velocities) if velocities else 0

        # Calculate acceleration
        accelerations = calculate_derivative(velocities)
        avg_acceleration = (
            sum(accelerations) / len(accelerations) if accelerations else 0
        )

        return {
            "total_distance": total_distance,
            "average_velocity": avg_velocity,
            "maximum_velocity": max_velocity,
            "average_acceleration": avg_acceleration,
            "sample_count": len(position_data),
            "motion_smoothness": 1.0 / (1.0 + avg_acceleration)
            if avg_acceleration > 0
            else 1.0,
        }

    except Exception as e:
        return {"error": f"Motion analysis failed: {e}"}


def create_data_buffer(size: int) -> List[float]:
    """
    Create a circular data buffer for real-time data processing.

    Args:
        size: Buffer size

    Returns:
        Initialized buffer filled with zeros
    """
    return [0.0] * size


def update_buffer(buffer: List[float], new_value: float) -> List[float]:
    """
    Update circular buffer with new value.

    Args:
        buffer: Existing buffer
        new_value: New value to add

    Returns:
        Updated buffer
    """
    try:
        # Shift all values and add new one
        updated = buffer[1:] + [new_value]
        return updated

    except Exception as e:
        print(f"Buffer update error: {e}")
        return buffer


def export_data_to_csv(
    data: Union[List[float], List[List[float]]],
    filename: str,
    headers: Optional[List[str]] = None,
) -> bool:
    """
    Export data to CSV file format.

    Args:
        data: Data to export (1D or 2D list)
        filename: Output filename
        headers: Optional column headers

    Returns:
        True if export successful
    """
    try:
        import csv

        # Ensure data is 2D
        if data and isinstance(data[0], (int, float)):
            # Convert 1D to 2D
            data = [[value] for value in data]

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Write headers if provided
            if headers:
                writer.writerow(headers)

            # Write data rows
            for row in data:
                writer.writerow(row)

        print(f"Data exported to: {filename}")
        return True

    except Exception as e:
        print(f"CSV export error: {e}")
        return False
