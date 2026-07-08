export function roleFromPosition(position) {
  if (!position) return "employee";
  if (position.includes("Администратор")) return "admin";
  if (position.includes("Специалист")) return "specialist";
  return "employee";
}

export const ROLE_LABELS = {
  employee: "Работник",
  specialist: "Специалист по ОТ",
  admin: "Администратор",
};

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
