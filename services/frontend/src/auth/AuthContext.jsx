import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { roleFromPosition } from "../utils/role";

const AuthContext = createContext(null);

const STORAGE_KEY = "pulkovo_employee";

function loadStoredEmployee() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [employee, setEmployee] = useState(loadStoredEmployee);

  const login = useCallback((employeeData) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(employeeData));
    setEmployee(employeeData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setEmployee(null);
  }, []);

  const updateEmployee = useCallback((patch) => {
    setEmployee((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      employee,
      role: roleFromPosition(employee?.position),
      isAuthenticated: Boolean(employee),
      login,
      logout,
      updateEmployee,
    }),
    [employee, login, logout, updateEmployee]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
