// Tiny TS fixture: exported async function, generic class with methods.

export async function fetchUser(id: number): Promise<string> {
    return String(id);
}

export class Container<T> {
    private value: T;

    constructor(val: T) {
        this.value = val;
    }

    get(): T {
        return this.value;
    }
}
