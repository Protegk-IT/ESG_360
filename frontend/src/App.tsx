import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/auth/Login";

function Dashboard() {

    return (

        <div className="p-10 text-3xl">

            Dashboard

        </div>

    );

}

export default function App() {

    return (

        <BrowserRouter>

            <Routes>

                <Route
                    path="/"
                    element={<Login />}
                />
                <Route
                    path="/dashboard"
                    element={<Dashboard />}
                />

            </Routes>

        </BrowserRouter>

    );

}