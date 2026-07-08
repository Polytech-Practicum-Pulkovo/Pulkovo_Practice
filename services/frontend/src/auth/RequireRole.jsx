import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function RequireRole({ roles }) {
  const { role } = useAuth();

  if (!roles.includes(role)) {
    return <Navigate to="/app/profile" replace />;
  }

  return <Outlet />;
}
