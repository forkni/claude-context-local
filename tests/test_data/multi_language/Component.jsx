// JSX test file
import React, { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    
    return (
        <div>
            <h1>Count: {count}</h1>
            <button onClick={() => setCount(count + 1)}>
                Increment
            </button>
        </div>
    );
}

const UserCard = ({ user }) => {
    return (
        <div className="user-card">
            <h2>{user.name}</h2>
            <p>{user.email}</p>
        </div>
    );
};

export { Counter, UserCard };