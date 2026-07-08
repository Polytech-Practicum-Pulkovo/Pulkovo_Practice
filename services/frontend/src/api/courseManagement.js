import { API } from "./config";
import { get, post, put, del } from "./client";

const base = API.courseManagement;

export function listPrograms() {
  return get(base, "/programs");
}

export function getProgram(programId) {
  return get(base, `/programs/${programId}`);
}

export function createProgram(payload) {
  return post(base, "/programs", payload);
}

export function deleteProgram(programId) {
  return del(base, `/programs/${programId}`);
}

export function addLiterature(programId, name, link) {
  return post(base, `/programs/${programId}/literature`, { name, link });
}

export function deleteLiterature(literatureId) {
  return del(base, `/literature/${literatureId}`);
}

export function listPositions() {
  return get(base, "/positions");
}

export function listDepartments() {
  return get(base, "/departments");
}

export function listAssignments(idProgram) {
  return get(base, "/assignments", { id_program: idProgram });
}

export function bulkAssign(idProgram, idPosition) {
  return post(base, "/assignments/bulk", { id_program: idProgram, id_position: idPosition });
}

export function bulkUnassign(idProgram, idPosition) {
  return del(base, "/assignments/bulk", { id_program: idProgram, id_position: idPosition });
}

export function addTopicManual(idProgram, name) {
  return post(base, "/topics/manual", { id_program: idProgram, name });
}

export function addTopicsAi(idProgram, candidateTopics) {
  return post(base, "/topics/ai-distribution", { id_program: idProgram, candidate_topics: candidateTopics });
}

export function deleteTopic(topicId) {
  return del(base, `/topics/${topicId}`);
}

export function generateQuestions(idTopic, count = 5) {
  return post(base, "/questions/generate", { id_topic: idTopic, count });
}

export function listQuestions(topicId) {
  return get(base, "/questions", { topic_id: topicId });
}

export function updateQuestion(questionId, payload) {
  return put(base, `/questions/${questionId}`, payload);
}

export function deleteQuestion(questionId) {
  return del(base, `/questions/${questionId}`);
}

export function updateAnswer(answerId, answerText, isCorrect) {
  return put(base, `/answers/${answerId}`, { answer_text: answerText, is_correct: isCorrect });
}

export function listComplaints(isSolved) {
  return get(base, "/complaints", { is_solved: isSolved });
}

export function resolveComplaint(complaintId, isSolved = true) {
  return put(base, `/complaints/${complaintId}/resolve`, { is_solved: isSolved });
}
