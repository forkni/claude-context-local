/* Tiny C fixture: function, struct, typedef. */

int add(int a, int b) {
    return a + b;
}

struct Point {
    int x;
    int y;
};

typedef struct {
    float r;
    float g;
    float b;
} Color;
