// Basic GLSL example for multi-language chunker smoke testing.

uniform float uTime;

struct Wave {
    float amplitude;
    float frequency;
};

float computeWave(Wave w, float x) {
    return w.amplitude * sin(w.frequency * x + uTime);
}

void main() {
    Wave w = Wave(1.0, 2.0);
    float y = computeWave(w, 0.5);
    gl_FragColor = vec4(y, y, y, 1.0);
}
