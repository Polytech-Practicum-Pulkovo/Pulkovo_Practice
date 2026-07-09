import { API } from "./config";
import { get, post, del } from "./client";

const base = API.courseProgress;

export function getCourse(completionId) {
  return get(base, `/courses/${completionId}`);
}

export function getTopic(completionId, topicId, employeeId) {
  return get(base, `/courses/${completionId}/topics/${topicId}`, { employee_id: employeeId });
}

export function markMaterialRead(completionId, materialId) {
  return post(base, `/courses/${completionId}/materials/${materialId}/read`);
}

export function materialFileUrl(materialId) {
  return `${base}/materials/${materialId}/file`;
}

export function navigate(completionId, fromSection, toSection, testInProgress) {
  return post(base, `/courses/${completionId}/navigate`, {
    from_section: fromSection,
    to_section: toSection,
    test_in_progress: testInProgress,
  });
}

export function submitTopicTest(completionId, topicId, employeeId, answers) {
  return post(base, `/courses/${completionId}/topics/${topicId}/submit-test`, {
    employee_id: employeeId,
    answers,
    is_final_test: false,
  });
}

export function getFinalTest(completionId) {
  return get(base, `/courses/${completionId}/final-test`);
}

export function submitFinalTest(completionId, employeeId, answers) {
  return post(base, `/courses/${completionId}/final-test/submit`, {
    employee_id: employeeId,
    answers,
    is_final_test: true,
  });
}

export function createComplaint(idQuestion, complaintText) {
  return post(base, "/complaints", { id_question: idQuestion, complaint_text: complaintText });
}

export function askAssistant(employeeId, topicId, message, catalogFile) {
  return post(base, "/assistant/ask", {
    employee_id: employeeId,
    topic_id: topicId,
    message,
    catalog_file: catalogFile || null,
  });
}

export function getTestSession(employeeId) {
  return get(base, `/employees/${employeeId}/test-session`);
}

export function startTestSession(employeeId, { idProgramCompletion, idTopic, isFinalTest }) {
  return post(base, `/employees/${employeeId}/test-session/start`, {
    id_program_completion: idProgramCompletion,
    id_topic: idTopic ?? null,
    is_final_test: isFinalTest,
  });
}

export function clearTestSession(employeeId) {
  return del(base, `/employees/${employeeId}/test-session`);
}
