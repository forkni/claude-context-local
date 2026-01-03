// Java test file
public class Calculator {
    private double result;
    
    public Calculator() {
        this.result = 0.0;
    }
    
    public static double calculateSum(double a, double b) {
        return a + b;
    }
    
    public Calculator add(double value) {
        this.result += value;
        return this;
    }
    
    public Calculator multiply(double value) {
        this.result *= value;
        return this;
    }
    
    public double getResult() {
        return this.result;
    }
}

interface MathOperations {
    double calculate(double a, double b);
}

enum Operation {
    ADD, SUBTRACT, MULTIPLY, DIVIDE;
    
    public double apply(double a, double b) {
        switch (this) {
            case ADD: return a + b;
            case SUBTRACT: return a - b; 
            case MULTIPLY: return a * b;
            case DIVIDE: return a / b;
            default: throw new IllegalArgumentException();
        }
    }
}