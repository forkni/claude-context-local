#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 3) out;

void emitVerts() {
    for (int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        EmitVertex();
    }
    EndPrimitive();
}

void tail() {
    emitVerts();
}

void main() {
    tail();
}
