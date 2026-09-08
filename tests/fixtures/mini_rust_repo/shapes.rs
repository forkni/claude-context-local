pub struct Circle {
    pub radius: f64,
}

impl Circle {
    pub fn new(radius: f64) -> Self {
        Circle { radius }
    }

    pub fn area(&self) -> f64 {
        std::f64::consts::PI * self.radius * self.radius
    }
}
