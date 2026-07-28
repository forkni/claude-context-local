// A user call nested inside another user call's argument list, alongside a
// nested builtin call — the walk must find "helper" and correctly drop the
// nested "dot"/"vec3" builtin targets, regardless of nesting depth.
vec3 helper(vec3 v) {
    return v * 2.0;
}

void main() {
    vec3 a = vec3(1.0);
    vec3 b = vec3(2.0);
    vec3 result = helper(vec3(1.0, dot(a, b), 2.0));
    gl_FragColor = vec4(result, 1.0);
}
