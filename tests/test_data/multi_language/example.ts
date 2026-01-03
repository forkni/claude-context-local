// TypeScript test file
interface User {
    id: number;
    name: string;
    email: string;
}

type Status = 'active' | 'inactive' | 'pending';

class UserService {
    private users: User[] = [];
    
    async getUser(id: number): Promise<User | undefined> {
        return this.users.find(u => u.id === id);
    }
    
    addUser(user: User): void {
        this.users.push(user);
    }
}

function genericFunction<T>(value: T): T {
    return value;
}

enum Role {
    Admin = 'ADMIN',
    User = 'USER',
    Guest = 'GUEST'
}

export { UserService, User, Status, Role };