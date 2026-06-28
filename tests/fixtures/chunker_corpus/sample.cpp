// Tiny C++ fixture: template function, class, namespace.

template<typename T>
T add(T a, T b) {
    return a + b;
}

class Vector {
public:
    float x, y;
    Vector(float xi, float yi) : x(xi), y(yi) {}
};

namespace math {
    int square(int n) {
        return n * n;
    }
}
