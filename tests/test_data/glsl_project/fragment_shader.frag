#version 330 core

in vec2 texCoord;
uniform sampler2D texture0;
uniform float alpha;

out vec4 fragColor;

void main() {
    vec4 texColor = texture(texture0, texCoord);
    fragColor = vec4(texColor.rgb, texColor.a * alpha);
}