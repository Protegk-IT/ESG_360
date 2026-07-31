import { useState } from "react";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import api, { setCsrfToken } from "../../services/api";

interface LoginForm {
  username: string;
  password: string;
}

// interface ErrorResponse {
//   detail?: string;
//   message?: string;
//   success?: boolean;
// }

export default function Login() {
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [formData, setFormData] = useState<LoginForm>({
    username: "",
    password: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
    const response = await api.post("/accounts/login/", formData);
    setCsrfToken(response.data.csrf_token ?? "");

    console.log("SUCCESS:", response.status);
    console.log(response.data);

    alert("Login Success");

    navigate("/accounts/dashboard/");
}catch (error: unknown) {
  if (axios.isAxiosError(error)) {
    console.log("Axios error:", error);
    console.log("Response:", error.response);
    console.log("Request:", error.request);
    console.log("Message:", error.message);

    if (error.response) {
      setError(
        error.response.data?.message ??
        error.response.data?.detail ??
        "Login failed"
      );
    } else {
      setError(error.message);
    }
  } else {
    console.log(error);
    setError("Unknown error");
  }
}
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-6">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-10 shadow-lg">
        {/* Logo */}

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">
            ESG360
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            Enterprise Sustainability Platform
          </p>
        </div>

        {/* Error */}

        {error && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="space-y-6"
        >
          {/* Username */}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Username
            </label>

            <div className="relative">
              <User
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
              />

              <input
                type="text"
                name="username"
                placeholder="Enter username"
                value={formData.username}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-4 outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100"
              />
            </div>
          </div>

          {/* Password */}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Password
            </label>

            <div className="relative">
              <Lock
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
              />

              <input
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Enter password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-12 outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100"
              />

              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>
            </div>
          </div>

          {/* Remember */}

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 text-gray-600">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-orange-500 focus:ring-orange-500"
              />

              Remember me
            </label>

            <button
              type="button"
              className="font-medium text-orange-500 hover:text-orange-600"
            >
              Forgot Password?
            </button>
          </div>

          {/* Button */}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-orange-500 py-3 font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
          >
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        {/* Footer */}

        <div className="mt-8 border-t pt-5 text-center text-xs text-gray-400">
          © 2026 ESG360. All Rights Reserved.
        </div>
      </div>
    </div>
  );
}