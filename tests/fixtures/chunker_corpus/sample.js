// Tiny JS fixture: async function, generator, class with method.

async function fetchData(url) {
    return url;
}

function* counter() {
    let n = 0;
    yield n++;
}

class Animal {
    constructor(name) {
        this.name = name;
    }

    speak() {
        return this.name;
    }
}
