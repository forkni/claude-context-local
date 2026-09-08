pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    pub fn magnitude(&self) -> f64 {
        self.magnitude_sq().sqrt()
    }

    fn magnitude_sq(&self) -> f64 {
        self.x * self.x + self.y * self.y
    }
}

pub fn origin() -> Point {
    Point::new(0.0, 0.0)
}
