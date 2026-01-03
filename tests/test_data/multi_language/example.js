// JavaScript test file
function calculateSum(a, b) {
    return a + b;
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(value) {
        this.result += value;
        return this;
    }
}

const asyncFunction = async () => {
    const data = await fetch('/api');
    return data.json();
};

export default Calculator;