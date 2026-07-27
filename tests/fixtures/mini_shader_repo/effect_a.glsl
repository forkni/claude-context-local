// Rounded-box signed distance helper — builtin-only body (abs/length/max),
// so it must resolve to zero call edges of its own.
float roundedBoxSDF(vec3 pos, vec3 size, float radius) {
    vec3 q = abs(pos) - size + radius;
    return length(max(q, 0.0)) - radius;
}

vec3 process(vec3 color) {
    return color * 0.5;
}

void main() {
    float d = roundedBoxSDF(gl_FragCoord.xyz, vec3(1.0), 0.1);
    vec3 c = process(vec3(d));
    gl_FragColor = vec4(c, 1.0);
}
