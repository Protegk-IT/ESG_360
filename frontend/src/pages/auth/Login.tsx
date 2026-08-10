import { useState } from "react";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import api, { setCsrfToken } from "../../services/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

interface LoginForm {
  username: string;
  password: string;
}


  export default function Login() {
    const navigate = useNavigate();

    const { login } = useAuth();

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

setCsrfToken(response.data.csrfToken ?? "");

login(response.data.user);

toast.success("Login Successful");

navigate("/accounts/dashboard/");
}catch (error: unknown) {
  if (axios.isAxiosError(error)) {
    // console.log("Axios error:", error);
    // console.log("Response:", error.response);
    // console.log("Request:", error.request);
    // console.log("Message:", error.message);

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
  <div className="flex min-h-screen items-center justify-center bg-[#F5F5FB] px-6">
    <div className="w-full max-w-md rounded-xl border border-[#8891A3] bg-white p-10 shadow-sm">

      {/* Logo */}

      <div className="mb-10 text-center">

        <h1 className="text-4xl font-extrabold tracking-tight text-[#22243A]">
          ESG<span className="text-[#4A3FD6]">360</span>
        </h1>

        <p className="mt-2 text-sm text-[#6B7280]">
          Enterprise Sustainability Platform
        </p>

      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-[#B3403B] bg-[#FBE9E8] px-4 py-3 text-sm text-[#B3403B]">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-6"
      >

        {/* Username */}

        <div>

          <label className="mb-2 block text-sm font-semibold text-[#22243A]">
            Username
          </label>

          <div className="relative">

            <User
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7280]"
            />

            <input
              type="text"
              name="username"
              placeholder="Enter username"
              value={formData.username}
              onChange={handleChange}
              required
              className="
                h-12
                w-full
                rounded-xl
                border
                border-[#8891A3]
                bg-white
                py-3
                pl-11
                pr-4
                text-sm
                text-[#22243A]
                outline-none
                transition

                placeholder:text-[#9AA1B0]

                focus:border-[#4A3FD6]
                focus:ring-2
                focus:ring-[#ECE9FB]
              "
            />

          </div>

        </div>

        {/* Password */}

        <div>

          <label className="mb-2 block text-sm font-semibold text-[#22243A]">
            Password
          </label>

          <div className="relative">

            <Lock
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7280]"
            />

            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Enter password"
              value={formData.password}
              onChange={handleChange}
              required
              className="
                h-12
                w-full
                rounded-xl
                border
                border-[#8891A3]
                bg-white
                py-3
                pl-11
                pr-12
                text-sm
                text-[#22243A]
                outline-none
                transition

                placeholder:text-[#9AA1B0]

                focus:border-[#4A3FD6]
                focus:ring-2
                focus:ring-[#ECE9FB]
              "
            />

            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7280] hover:text-[#4A3FD6]"
            >
              {showPassword ? (
                <EyeOff size={18} />
              ) : (
                <Eye size={18} />
              )}
            </button>

          </div>

        </div>

        <button
          type="submit"
          disabled={loading}
          className="
            h-12
            w-full
            rounded-xl
            bg-[#4A3FD6]
            font-semibold
            text-white
            transition

            hover:bg-[#3D33C0]

            focus:ring-2
            focus:ring-[#ECE9FB]

            disabled:cursor-not-allowed
            disabled:opacity-60
          "
        >
          {loading ? "Signing In..." : "Sign In"}
        </button>

      </form>

      <div className="mt-10 border-t border-[#E5E7EB] pt-6 text-center text-xs text-[#6B7280]">
        © 2026 ESG360. All Rights Reserved.
      </div>

    </div>
  </div>
);
}
