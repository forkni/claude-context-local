// Tiny C# fixture: class with async method and generic method.

public class Calculator {
    public async System.Threading.Tasks.Task<int> AddAsync(int a, int b) {
        return a + b;
    }

    public T Identity<T>(T value) {
        return value;
    }
}
