import { useEffect, useMemo, useState } from "react";
import {
  deleteQuestion,
  getProgram,
  listComplaints,
  listPrograms,
  listQuestions,
  resolveComplaint,
  updateQuestion,
} from "../../api/courseManagement";
import Modal from "../../components/Modal";

function BankTab() {
  const [programs, setPrograms] = useState([]);
  const [topics, setTopics] = useState([]);
  const [programId, setProgramId] = useState("");
  const [topicId, setTopicId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(null);
  const [complaintsForQuestion, setComplaintsForQuestion] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(null);

  useEffect(() => {
    listPrograms().then(setPrograms);
  }, []);

  useEffect(() => {
    if (!programId) {
      setTopics([]);
      setTopicId("");
      return;
    }
    getProgram(programId).then((program) => setTopics(program.topics || []));
  }, [programId]);

  function reloadQuestions() {
    if (!topicId) {
      setQuestions([]);
      return;
    }
    listQuestions(topicId).then(setQuestions);
  }

  useEffect(reloadQuestions, [topicId]);

  const filtered = useMemo(
    () => questions.filter((q) => q.question_text.toLowerCase().includes(search.toLowerCase())),
    [questions, search]
  );

  function startEdit(question) {
    setEditingId(question.id_question);
    setEditDraft({
      question_text: question.question_text,
      answers: question.answers.map((a) => ({ ...a })),
    });
  }

  async function saveEdit(questionId) {
    await updateQuestion(questionId, {
      question_text: editDraft.question_text,
      answers: editDraft.answers,
    });
    setEditingId(null);
    reloadQuestions();
  }

  async function handleDelete(questionId) {
    await deleteQuestion(questionId);
    setConfirmingDelete(null);
    reloadQuestions();
  }

  async function openComplaints(questionId) {
    const all = await listComplaints();
    setComplaintsForQuestion(all.filter((c) => c.id_question === questionId));
  }

  return (
    <div>
      <div className="filters-grid">
        <select value={programId} onChange={(e) => setProgramId(e.target.value)}>
          <option value="">Курс…</option>
          {programs.map((p) => (
            <option key={p.id_program} value={p.id_program}>
              {p.name}
            </option>
          ))}
        </select>
        <select value={topicId} onChange={(e) => setTopicId(e.target.value)} disabled={!programId}>
          <option value="">Тема…</option>
          {topics.map((t) => (
            <option key={t.id_topic} value={t.id_topic}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <input
        className="search-input mb-16"
        placeholder="Поиск"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {!topicId && <div className="empty-state">Выберите курс и тему, чтобы увидеть вопросы</div>}
      {topicId && filtered.length === 0 && <div className="empty-state">Не нашлось ни одного вопроса</div>}

      {filtered.map((q) => (
        <div key={q.id_question} className="panel mb-16" style={{ padding: 16 }}>
          {editingId === q.id_question ? (
            <div>
              <input
                style={{ width: "100%", padding: 8, marginBottom: 10 }}
                value={editDraft.question_text}
                onChange={(e) => setEditDraft({ ...editDraft, question_text: e.target.value })}
              />
              {editDraft.answers.map((a, idx) => (
                <div key={a.id_answer} className="row mb-16">
                  <input
                    type="radio"
                    name={`correct-answer-${q.id_question}`}
                    checked={a.is_correct}
                    onChange={() => {
                      const answers = editDraft.answers.map((answer, answerIdx) => ({
                        ...answer,
                        is_correct: answerIdx === idx,
                      }));
                      setEditDraft({ ...editDraft, answers });
                    }}
                  />
                  <input
                    style={{ flex: 1, padding: 6 }}
                    value={a.answer_text}
                    onChange={(e) => {
                      const answers = [...editDraft.answers];
                      answers[idx] = { ...a, answer_text: e.target.value };
                      setEditDraft({ ...editDraft, answers });
                    }}
                  />
                </div>
              ))}
              <button className="btn btn-primary" onClick={() => saveEdit(q.id_question)}>
                Подтвердить
              </button>
            </div>
          ) : (
            <div className="row-between">
              <div>
                <strong>
                  Вопрос {q.id_question}: {!q.is_verified && "🤖"}
                </strong>
                <p>{q.question_text}</p>
                {q.answers.map((a) => (
                  <div key={a.id_answer} className="answer-option">
                    <span className={`answer-swatch ${a.is_correct ? "correct" : ""}`} />
                    {a.answer_text}
                  </div>
                ))}
              </div>
              <div className="row" style={{ flexDirection: "column" }}>
                <button className="btn btn-danger" onClick={() => setConfirmingDelete(q.id_question)}>
                  Удалить вопрос
                </button>
                <button className="btn btn-secondary" onClick={() => startEdit(q)}>
                  Изменить вопрос
                </button>
                <button className="btn btn-primary" onClick={() => openComplaints(q.id_question)}>
                  Посмотреть жалобы
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {confirmingDelete && (
        <Modal onClose={() => setConfirmingDelete(null)}>
          <h3>Удалить вопрос?</h3>
          <p>Подтвердите удаление вопроса {confirmingDelete}.</p>
          <div className="row">
            <button className="btn btn-secondary" onClick={() => setConfirmingDelete(null)}>
              Назад
            </button>
            <button className="btn btn-danger" onClick={() => handleDelete(confirmingDelete)}>
              Удалить вопрос
            </button>
          </div>
        </Modal>
      )}

      {complaintsForQuestion && (
        <Modal onClose={() => setComplaintsForQuestion(null)}>
          <h3>Жалобы на вопрос</h3>
          {complaintsForQuestion.length === 0 && <p>Жалоб пока нет</p>}
          {complaintsForQuestion.map((c) => (
            <div key={c.id_complaint} className="mb-16">
              <strong>Жалоба {c.id_complaint}</strong>
              <p>Комментарий: {c.complaint_text || "—"}</p>
            </div>
          ))}
        </Modal>
      )}
    </div>
  );
}

function ComplaintsTab() {
  const [complaints, setComplaints] = useState([]);

  function reload() {
    return listComplaints().then(setComplaints);
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleResolve(id) {
    await resolveComplaint(id, true);
    reload();
  }

  return (
    <div>
      {complaints.map((c) => (
        <div key={c.id_complaint} className="panel row-between mb-16" style={{ padding: 16 }}>
          <div>
            <strong>Жалоба {c.id_complaint}</strong>
            <div>
              Вопрос: <u>{c.question_text}</u>
            </div>
            <div>Комментарий: {c.complaint_text}</div>
          </div>
          {c.is_solved ? (
            <span className="badge badge-green">Решена ✓</span>
          ) : (
            <button className="btn btn-primary" onClick={() => handleResolve(c.id_complaint)}>
              Отметить решённой ✓
            </button>
          )}
        </div>
      ))}
      {complaints.length === 0 && <div className="empty-state">Жалоб пока нет</div>}
    </div>
  );
}

export default function QuestionBankPage() {
  const [tab, setTab] = useState("bank");

  return (
    <div>
      <h1>Банк вопросов</h1>
      <div className="tabs mb-16">
        <div className={`tab ${tab === "bank" ? "active" : ""}`} onClick={() => setTab("bank")}>
          Банк вопросов
        </div>
        <div className={`tab ${tab === "complaints" ? "active" : ""}`} onClick={() => setTab("complaints")}>
          Жалобы на вопросы
        </div>
      </div>
      {tab === "bank" ? <BankTab /> : <ComplaintsTab />}
    </div>
  );
}
