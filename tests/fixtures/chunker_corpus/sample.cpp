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

// Plain struct (not class) with a C-style function-pointer member --
// exercises both the parenthesized_declarator unwrap fix and struct-member
// parent_chunk_id linkage.
struct Table {
    void (*cb)(int, int);
};

// Anonymous struct typedef -- exercises the cpp-path anonymous-typedef
// naming fallback (name lives on the parent type_definition, not this
// specifier).
typedef struct {
    int x;
    int y;
} Vec3;
