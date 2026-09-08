mod geometry;
mod shapes;

use geometry::Point;
use shapes::Circle;

fn describe_point(p: &Point) -> f64 {
    p.magnitude()
}

pub fn run() -> f64 {
    let start = geometry::origin();
    let p = Point::new(3.0, 4.0);
    let c = Circle::new(2.0);
    describe_point(&p) + c.area() + start.x
}
