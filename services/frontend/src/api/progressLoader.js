import { API } from "./config";
import { get } from "./client";

const base = API.progressLoader;

export function listProgramCompletions(employeeId, withProgress = false) {
  return get(base, "/program-completions", { employee_id: employeeId, with_progress: withProgress });
}

export function getProgramCompletion(completionId) {
  return get(base, `/program-completions/${completionId}`);
}

export function getJournal(filters) {
  return get(base, "/journal", filters);
}

export function getStats(filters) {
  return get(base, "/stats", filters);
}
