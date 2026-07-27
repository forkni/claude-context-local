// Shared SDF helpers pulled in from the common include library.
#include "common.glslinc"

// Output gain multiplier applied to the final color.
#define GAIN 2.0

vec3 boost(vec3 color) {
    return color * GAIN;
}

void main() {
    gl_FragColor = vec4(boost(vec3(0.5)), 1.0);
}
