import { API } from "./config";
import { get, post } from "./client";

const base = API.personalData;

export function login(employeeNumber, password) {
  return post(base, "/auth/login", { employee_number: Number(employeeNumber), password });
}

export function changePassword(employeeId, oldPassword, newPassword) {
  return post(base, "/auth/change-password", {
    employee_id: employeeId,
    old_password: oldPassword,
    new_password: newPassword,
  });
}

export function forgotPassword(employeeNumber) {
  return post(base, "/auth/forgot-password", { employee_number: Number(employeeNumber) });
}

export function resetPassword(token, newPassword) {
  return post(base, "/auth/reset-password", { token, new_password: newPassword });
}

export function getEmployee(employeeId) {
  return get(base, `/employees/${employeeId}`);
}
