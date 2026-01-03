// C++ test file
#include <iostream>
#include <memory>

namespace Math {
    template<typename T>
    class Calculator {
    private:
        T result;
    
    public:
        Calculator() : result(T{}) {}
        
        static T calculateSum(T a, T b) {
            return a + b;
        }
        
        Calculator& add(T value) {
            result += value;
            return *this;
        }
        
        Calculator& multiply(T value) {
            result *= value;
            return *this;
        }
        
        T getResult() const {
            return result;
        }
    };

    enum class Operation {
        ADD,
        SUBTRACT, 
        MULTIPLY,
        DIVIDE
    };

    template<typename T>
    T applyOperation(Operation op, T a, T b) {
        switch (op) {
            case Operation::ADD: return a + b;
            case Operation::SUBTRACT: return a - b;
            case Operation::MULTIPLY: return a * b;
            case Operation::DIVIDE: return a / b;
            default: return T{};
        }
    }
}

struct Point {
    double x, y;
    
    Point(double x = 0, double y = 0) : x(x), y(y) {}
    
    double distance() const {
        return std::sqrt(x*x + y*y);
    }
};

int main() {
    Math::Calculator<double> calc;
    auto result = calc.add(10.0).multiply(2.0).getResult();
    std::cout << "Result: " << result << std::endl;
    return 0;
}