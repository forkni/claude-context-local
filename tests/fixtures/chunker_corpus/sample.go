// Tiny Go fixture: function, struct type, method with receiver.
package main

func Add(a, b int) int {
	return a + b
}

type Greeter struct {
	Name string
}

func (g Greeter) Greet() string {
	return "Hello, " + g.Name
}
