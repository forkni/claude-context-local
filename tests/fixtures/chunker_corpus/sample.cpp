// Tiny C++ fixture: template function, class, namespace.

template<typename T>
T add(T a, T b) {
    return a + b;
}

class Vector {
public:
    float x, y;
    Vector(float xi, float yi) : x(xi), y(yi) {}
    Vector& operator=(const Vector& other) {
        x = other.x;
        y = other.y;
        return *this;
    }
};

namespace math {
    int square(int n) {
        return n * n;
    }
}

// Declaration-only header-style class: both members are declarations with
// no body, exercising should_chunk_node's function-shaped narrowing.
class Shape {
public:
    void draw();
    virtual ~Shape();
};

// Pointer-returning out-of-class definition, qualified via `Foo::`.
class Foo {
public:
    int* getPtr();
};

int* Foo::getPtr() {
    return nullptr;
}

enum class Color { Red, Green, Blue };

using Number = int;
