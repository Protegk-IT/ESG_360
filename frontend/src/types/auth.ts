export interface LoginForm {
    username: string;
    password: string;
}

export interface LoginResponse {
    message: string;
    username: string;
    full_name: string;
}