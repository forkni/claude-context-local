// TSX test file
import React, { FC, useState } from 'react';

interface Props {
    title: string;
    initialCount?: number;
}

const TypedCounter: FC<Props> = ({ title, initialCount = 0 }) => {
    const [count, setCount] = useState<number>(initialCount);
    
    const increment = (): void => {
        setCount(prev => prev + 1);
    };
    
    return (
        <div>
            <h1>{title}</h1>
            <p>Count: {count}</p>
            <button onClick={increment}>+</button>
        </div>
    );
};

interface User {
    id: number;
    name: string;
}

function UserList({ users }: { users: User[] }) {
    return (
        <ul>
            {users.map(user => (
                <li key={user.id}>{user.name}</li>
            ))}
        </ul>
    );
}

export { TypedCounter, UserList };