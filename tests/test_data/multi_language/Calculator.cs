// C# test file
using System;

namespace Math
{
    public class Calculator
    {
        private double result;
        
        public Calculator()
        {
            this.result = 0.0;
        }
        
        public static double CalculateSum(double a, double b)
        {
            return a + b;
        }
        
        public Calculator Add(double value)
        {
            this.result += value;
            return this;
        }
        
        public Calculator Multiply(double value)
        {
            this.result *= value;
            return this;
        }
        
        public double GetResult()
        {
            return this.result;
        }
        
        public double Result 
        { 
            get => result; 
            set => result = value; 
        }
        
        public event Action<double> ResultChanged;
        
        protected virtual void OnResultChanged(double newResult)
        {
            ResultChanged?.Invoke(newResult);
        }
    }

    public interface IMathOperations
    {
        double Calculate(double a, double b);
    }

    public enum Operation
    {
        Add,
        Subtract,
        Multiply,
        Divide
    }

    public static class OperationExtensions
    {
        public static double Apply(this Operation op, double a, double b)
        {
            return op switch
            {
                Operation.Add => a + b,
                Operation.Subtract => a - b,
                Operation.Multiply => a * b,
                Operation.Divide => a / b,
                _ => throw new ArgumentException()
            };
        }
    }

    public struct Point
    {
        public double X { get; set; }
        public double Y { get; set; }
        
        public Point(double x, double y)
        {
            X = x;
            Y = y;
        }
        
        public double Distance() => Math.Sqrt(X * X + Y * Y);
    }
}