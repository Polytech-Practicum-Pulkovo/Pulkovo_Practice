import { useEffect, useRef, useState } from "react";
import Modal from "./Modal";

const TEST_DURATION_MINUTES = 45;

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function TestPanel({ questions, lastAttempt, session, onStart, onSubmit, onAskExplanation, onComplain }) {
  const [selected, setSelected] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [remaining, setRemaining] = useState(session?.seconds_remaining ?? 0);
  const [timedOut, setTimedOut] = useState(false);
  const [explanations, setExplanations] = useState({});
  const [complaintFor, setComplaintFor] = useState(null);
  const [complaintText, setComplaintText] = useState("");
  const [complaintSent, setComplaintSent] = useState(false);
  const selectedRef = useRef(selected);

  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  useEffect(() => {
    if (!session) return undefined;

    const deadline = new Date(session.started_at).getTime() + session.duration_seconds * 1000;
    let expired = false;

    async function submitOnTimeout() {
      const answers = questions
        .filter((q) => selectedRef.current[q.id_question])
        .map((q) => ({ id_question: q.id_question, id_answer: selectedRef.current[q.id_question] }));
      setTimedOut(true);
      setSubmitting(true);
      try {
        await onSubmit(answers);
      } finally {
        setSubmitting(false);
      }
    }

    function tick() {
      const secs = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setRemaining(secs);
      if (secs <= 0 && !expired) {
        expired = true;
        clearInterval(interval);
        submitOnTimeout();
      }
    }

    const interval = setInterval(tick, 1000);
    tick();

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

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
      await onSubmit(answers);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStart() {
    setStarting(true);
    try {
      setSelected({});
      setTimedOut(false);
      await onStart();
    } finally {
      setStarting(false);
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

  // Тест уже начат — показываем вопросы и таймер.
  if (session) {
    return (
      <div>
        <div className="alert alert-info mb-16">⏱ Осталось времени: {formatTime(remaining)}</div>
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

  // Тест уже проходили — показываем результаты последней попытки.
  if (lastAttempt) {
    const answersById = new Map((lastAttempt.answers || []).map((a) => [a.id_question, a]));
    const { percent, passed } = lastAttempt;

    return (
      <div>
        {timedOut && (
          <div className="alert alert-error mb-16">
            ⏱ Время на прохождение теста истекло — тест завершён автоматически, неотвеченные вопросы
            засчитаны как неверные.
          </div>
        )}
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

        <button className="btn btn-primary" onClick={handleStart} disabled={starting}>
          {starting ? "Запускаем…" : "Начать заново"}
        </button>

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

  // Тест ещё не проходили — показываем информацию перед началом.
  return (
    <div>
      <h3>Перед началом теста</h3>
      <p>Количество вопросов: {questions.length}</p>
      <p>Время на прохождение: {TEST_DURATION_MINUTES} мин.</p>
      <p>
        После начала теста материалы и чат с ИИ будут недоступны во всех курсах до завершения теста. Если
        время истечёт, тест завершится автоматически, а неотвеченные вопросы будут засчитаны как неверные.
      </p>
      <button className="btn btn-primary" onClick={handleStart} disabled={starting || questions.length === 0}>
        {starting ? "Запускаем…" : "Начать"}
      </button>
      {questions.length === 0 && <p className="alert alert-error mt-16">Вопросы по теме ещё не готовы.</p>}
    </div>
  );
}
