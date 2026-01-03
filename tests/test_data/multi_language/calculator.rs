// Rust test file
#[derive(Debug)]
pub struct Calculator {
    result: f64,
}

impl Calculator {
    pub fn new() -> Self {
        Calculator { result: 0.0 }
    }
    
    pub fn add(&mut self, value: f64) -> &mut Self {
        self.result += value;
        self
    }
    
    pub fn multiply(&mut self, value: f64) -> &mut Self {
        self.result *= value;
        self
    }
    
    pub fn get_result(&self) -> f64 {
        self.result
    }
}

pub fn calculate_sum(a: f64, b: f64) -> f64 {
    a + b
}

pub trait MathOperations {
    fn calculate(&self, a: f64, b: f64) -> f64;
}

#[derive(Debug, Clone, Copy)]
pub enum Operation {
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl Operation {
    pub fn apply(self, a: f64, b: f64) -> f64 {
        match self {
            Operation::Add => a + b,
            Operation::Subtract => a - b,
            Operation::Multiply => a * b,
            Operation::Divide => a / b,
        }
    }
}

#[derive(Debug)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }
    
    pub fn distance(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

macro_rules! calculate {
    ($op:expr, $a:expr, $b:expr) => {
        $op.apply($a, $b)
    };
}

pub async fn async_calculate(a: f64, b: f64) -> f64 {
    tokio::time::sleep(tokio::time::Duration::from_millis(1)).await;
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_calculator() {
        let mut calc = Calculator::new();
        let result = calc.add(10.0).multiply(2.0).get_result();
        assert_eq!(result, 20.0);
    }
}