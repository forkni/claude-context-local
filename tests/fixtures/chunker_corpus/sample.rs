// Tiny Rust fixture: async function, struct, impl block.

pub async fn fetch(url: &str) -> String {
    String::from(url)
}

struct Point {
    x: f64,
    y: f64,
}

impl Point {
    pub fn distance(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}
