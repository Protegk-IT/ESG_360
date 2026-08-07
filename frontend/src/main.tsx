import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import "@fontsource/lato/300.css";
import "@fontsource/lato/400.css";
import "@fontsource/lato/700.css";
import App from './App.tsx'
import { AuthProvider } from "@/context/AuthContext";

createRoot(document.getElementById('root')!).render(
  <AuthProvider>
  <StrictMode>
    <App />
  </StrictMode>,
  </AuthProvider>
)
