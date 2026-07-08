import { useState } from "react";
import Modal from "./Modal";

export default function TestPanel({ questions, lastAttempt, onSubmit, onAskExplanation, onComplain }) {
  const [retaking, setRetaking] = useState(false);
  const [selected, setSelected] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [explanations, setExplanations] = useState({});
  const [complaintFor, setComplaintFor] = useState(null);
  const [complaintText, setComplaintText] = useState("");
  const [complaintSent, setComplaintSent] = useState(false);

  const showingResults = lastAttempt && !retaking;

  function selectAnswer(questionId, answerId) {
    setSelected((prev) => ({ ...prev, [questionId]: answerId }));
  }

  async function handleSubmit() {
    const answers = questions
      .filter((q) => selected[q.id_question])
      .map((q) => ({ id_question: q.id_question, id_answer: selected[q.id_question] }));

    if (answers.length !== questions.length) {
      window.alert("Ответьте на все вопросы перед завершением теста");
      return;
    }

    setSubmitting(true);
    try {
      const outcome = await onSubmit(answers);
      setResult(outcome);
      setRetaking(false);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleExplain(questionText, questionId) {
    try {
      const text = await onAskExplanation(questionText);
      setExplanations((prev) => ({ ...prev, [questionId]: text }));
    } catch {
      setExplanations((prev) => ({
        ...prev,
        [questionId]: "ИИ-ассистент временно недоступен. Попробуйте позже.",
      }));
    }
  }

  async function handleSendComplaint() {
    await onComplain(complaintFor, complaintText);
    setComplaintSent(true);
  }

  if (showingResults || result) {
    const answersById = new Map((lastAttempt?.answers || []).map((a) => [a.id_question, a]));
    const percent = result?.percent ?? lastAttempt?.percent ?? 0;
    const passed = result?.passed ?? lastAttempt?.passed ?? false;

    return (
      <div>
        <p>
          Результат последнего прохождения: <strong>{percent}%</strong> ({passed ? "зачтено" : "не зачтено"})
        </p>
        {questions.map((q) => {
          const answered = answersById.get(q.id_question);
          const isCorrect = answered?.is_correct;
          return (
            <div
              key={q.id_question}
              className={`question-block ${answered ? (isCorrect ? "correct" : "incorrect") : ""}`}
            >
              <div className="row-between">
                <strong>Вопрос {q.id_question}:</strong>
                {!q.is_verified && <span title="Вопрос сгенерирован ИИ">🤖</span>}
              </div>
              <p>{q.question_text}</p>
              {q.answers.map((a) => (
                <div key={a.id_answer} className="answer-option">
                  <span
                    className={`answer-swatch ${
                      answered?.id_answer === a.id_answer ? (isCorrect ? "correct" : "wrong") : ""
                    }`}
                  />
                  {a.answer_text}
                </div>
              ))}
              {!isCorrect && answered && (
                <div className="row mt-16">
                  <button className="btn btn-secondary" onClick={() => handleExplain(q.question_text, q.id_question)}>
                    🤖 Попросить пояснение ИИ
                  </button>
                  {!q.is_verified && (
                    <button className="link-button" onClick={() => setComplaintFor(q.id_question)}>
                      Пожаловаться на вопрос
                    </button>
                  )}
                </div>
              )}
              {explanations[q.id_question] && (
                <div className="alert alert-success mt-16">{explanations[q.id_question]}</div>
              )}
            </div>
          );
        })}
        {!passed && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setResult(null);
              setSelected({});
              setRetaking(true);
            }}
          >
            Пройти тест заново
          </button>
        )}

        {complaintFor && (
          <Modal
            onClose={() => {
              setComplaintFor(null);
              setComplaintSent(false);
              setComplaintText("");
            }}
          >
            {complaintSent ? (
              <h3>Жалоба успешно отправлена!</h3>
            ) : (
              <>
                <h3>Жалоба на вопрос</h3>
                <p>Укажите причину жалобы</p>
                <textarea
                  rows={4}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
                  value={complaintText}
                  onChange={(e) => setComplaintText(e.target.value)}
                />
                <button className="btn btn-primary mt-16" onClick={handleSendComplaint}>
                  Отправить жалобу
                </button>
              </>
            )}
          </Modal>
        )}
      </div>
    );
  }

  return (
    <div>
      {questions.map((q) => (
        <div key={q.id_question} className="question-block">
          <strong>Вопрос {q.id_question}:</strong>
          <p>{q.question_text}</p>
          {q.answers.map((a) => (
            <label key={a.id_answer} className="answer-option">
              <input
                type="radio"
                name={`question-${q.id_question}`}
                checked={selected[q.id_question] === a.id_answer}
                onChange={() => selectAnswer(q.id_question, a.id_answer)}
              />
              {a.answer_text}
            </label>
          ))}
        </div>
      ))}
      <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Проверяем…" : "Завершить тест"}
      </button>
    </div>
  );
}
