import { Navigate, Outlet } from "react-router-dom";
import { roleHasAccess } from "../utils/role";
import { useAuth } from "./AuthContext";

export default function RequireRole({ minRole }) {
  const { role } = useAuth();

  if (!roleHasAccess(role, minRole)) {
    return <Navigate to="/app/profile" replace />;
  }

  return <Outlet />;
}
