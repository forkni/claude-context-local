// Go test file
package main

import "fmt"

type Calculator struct {
    result float64
}

func NewCalculator() *Calculator {
    return &Calculator{result: 0.0}
}

func CalculateSum(a, b float64) float64 {
    return a + b
}

func (c *Calculator) Add(value float64) *Calculator {
    c.result += value
    return c
}

func (c *Calculator) Multiply(value float64) *Calculator {
    c.result *= value
    return c
}

func (c *Calculator) GetResult() float64 {
    return c.result
}

type MathOperations interface {
    Calculate(a, b float64) float64
}

type Operation int

const (
    Add Operation = iota
    Subtract
    Multiply 
    Divide
)

func (op Operation) Apply(a, b float64) float64 {
    switch op {
    case Add:
        return a + b
    case Subtract:
        return a - b
    case Multiply:
        return a * b
    case Divide:
        return a / b
    default:
        return 0
    }
}

func main() {
    calc := NewCalculator()
    result := calc.Add(10).Multiply(2).GetResult()
    fmt.Printf("Result: %f\n", result)
}