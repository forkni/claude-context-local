// Same function names as effect_a.glsl (process, main) — exercises
// same-file call resolution instead of a cross-file name collision.
vec3 process(vec3 color) {
    return color * 2.0;
}

void main() {
    vec3 c = process(vec3(1.0));
    gl_FragColor = vec4(c, 1.0);
}
