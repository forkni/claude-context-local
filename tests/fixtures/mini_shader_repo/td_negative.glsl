// Negative cases for the TD-prefix builtin filter (name.startswith("TD") and
// len(name) > 2 and name[2].isupper()): neither name below matches the rule,
// so both must survive as real call edges, not get silently dropped.
float td_helper(float x) {
    return x * 2.0;
}

float TD(float x) {
    return x + 1.0;
}

void main() {
    float a = td_helper(1.0);
    float b = TD(2.0);
    gl_FragColor = vec4(a + b, 0.0, 0.0, 1.0);
}
