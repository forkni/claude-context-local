// C test file
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    double result;
} Calculator;

typedef enum {
    ADD,
    SUBTRACT,
    MULTIPLY,
    DIVIDE
} Operation;

double calculate_sum(double a, double b) {
    return a + b;
}

Calculator* new_calculator() {
    Calculator* calc = malloc(sizeof(Calculator));
    calc->result = 0.0;
    return calc;
}

Calculator* add_value(Calculator* calc, double value) {
    calc->result += value;
    return calc;
}

Calculator* multiply_value(Calculator* calc, double value) {
    calc->result *= value;
    return calc;
}

double get_result(Calculator* calc) {
    return calc->result;
}

double apply_operation(Operation op, double a, double b) {
    switch (op) {
        case ADD: return a + b;
        case SUBTRACT: return a - b;
        case MULTIPLY: return a * b;
        case DIVIDE: return a / b;
        default: return 0.0;
    }
}

void free_calculator(Calculator* calc) {
    free(calc);
}

int main() {
    Calculator* calc = new_calculator();
    add_value(calc, 10);
    multiply_value(calc, 2);
    printf("Result: %f\n", get_result(calc));
    free_calculator(calc);
    return 0;
}