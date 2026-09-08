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

// Trait impl -- exercises the impl-naming fix: must be named "Point" (the
// Self type), not "Default" (the trait), and must carry `impl_trait`.
impl Default for Point {
    fn default() -> Self {
        Point { x: 0.0, y: 0.0 }
    }
}

// Trait definition -- container node, chunked with its own method surfaced.
trait Shape {
    fn area(&self) -> f64;
}

// Nested module -- exercises mod_item container traversal (children surface
// as their own chunks) and the namespace parent_type fix (a free fn directly
// inside a mod must not be promoted to chunk_type "method").
mod geometry {
    pub fn unit_length() -> f64 {
        1.0
    }

    pub struct Line {
        pub length: f64,
    }

    impl Line {
        pub fn new(length: f64) -> Self {
            Line { length }
        }
    }
}
