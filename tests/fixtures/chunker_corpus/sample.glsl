// Tiny GLSL fixture: layout+binding uniforms, a UBO block, a struct, object-
// and function-like macros, #include, an #ifdef guard, comment-attached
// const, and two functions where one calls the other.

#include "common.glslinc"

#define PI 3.14159265
#define SQUARE(x) ((x) * (x))

#ifdef USE_FOG
uniform float uFogDensity;
#endif

// Maximum number of lights this shader supports.
const int MAX_LIGHTS = 4;

layout(binding = 0) uniform sampler2D uTexture; // Texture sampler

layout(std140) uniform Camera {
    mat4 viewProj;
    vec3 position;
} cam;

// Physically-based material properties.
struct Material {
    vec3 albedo;
    float roughness;
};

// Shade a point using the given material and light direction.
vec3 shade(Material mat, vec3 lightDir) {
    return mat.albedo * max(dot(lightDir, vec3(0.0, 1.0, 0.0)), 0.0);
}

// Entry point: shades a fixed light direction and applies macro falloff.
void main() {
    Material mat = Material(vec3(1.0), 0.5);
    vec3 color = shade(mat, vec3(0.0, 1.0, 0.0));
    float falloff = SQUARE(1.0 / float(MAX_LIGHTS)) * PI;
    gl_FragColor = vec4(color * falloff, 1.0);
}
