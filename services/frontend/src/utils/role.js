export function roleSlugFromRoleName(roleName) {
  if (!roleName) return "employee";
  if (roleName.includes("Администратор")) return "admin";
  if (roleName.includes("Специалист")) return "specialist";
  return "employee";
}

export const ROLE_LABELS = {
  employee: "Работник",
  specialist: "Специалист по ОТ",
  admin: "Администратор",
};

// Каждая следующая роль расширяет предыдущую: Специалист по ОТ включает весь
// функционал Работника, Администратор — весь функционал Специалиста по ОТ.
export const ROLE_LEVEL = {
  employee: 1,
  specialist: 2,
  admin: 3,
};

export function roleHasAccess(role, minRole) {
  return (ROLE_LEVEL[role] ?? 0) >= (ROLE_LEVEL[minRole] ?? 0);
}

export function fullName(person) {
  if (!person) return "";
  return [person.last_name, person.first_name, person.middle_name].filter(Boolean).join(" ");
}

export function initials(person) {
  if (!person) return "";
  const first = person.first_name?.[0] || "";
  const last = person.last_name?.[0] || "";
  return `${first}${last}`.toUpperCase();
}
