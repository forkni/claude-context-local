// Tiny GLSL fixture: uniforms, main function with builtins + texture + math ops.

uniform mat4 uModel;
uniform sampler2D uTexture;

void main() {
    vec3 n = normalize(gl_Normal);
    gl_Position = uModel * vec4(n, 1.0);
    gl_FragColor = texture2D(uTexture, vec2(0.5));
}
