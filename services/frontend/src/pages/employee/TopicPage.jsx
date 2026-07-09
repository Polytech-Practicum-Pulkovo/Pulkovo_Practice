import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  askAssistant,
  createComplaint,
  getTestSession,
  getTopic,
  markMaterialRead,
  materialFileUrl,
  startTestSession,
  submitTopicTest,
} from "../../api/courseProgress";
import { useAuth } from "../../auth/AuthContext";
import TestPanel from "../../components/TestPanel";

const SESSION_POLL_MS = 20000;

const TABS = ["materials", "chat", "test"];
const TAB_LABEL = { materials: "Материалы по теме", chat: "Чат с AI", test: "Контрольный тест" };

function materialDisplayName(fileLink) {
  return fileLink.replace(/^[0-9a-f]{32}_/, "");
}

export default function TopicPage() {
  const { completionId, topicId } = useParams();
  const { employee } = useAuth();
  const [topic, setTopic] = useState(null);
  const [session, setSession] = useState(null);
  const [tab, setTab] = useState("materials");
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);

  function reload() {
    return getTopic(completionId, topicId, employee.id_employee).then(setTopic);
  }

  function reloadSession() {
    return getTestSession(employee.id_employee).then((s) => setSession(s.active ? s : null));
  }

  useEffect(() => {
    reload();
    reloadSession();
    const interval = setInterval(reloadSession, SESSION_POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completionId, topicId]);

  useEffect(() => {
    if (session && tab !== "test") setTab("test");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  if (!topic) return <p>Загрузка…</p>;

  const allMaterialsRead = topic.materials.every((m) => m.is_read);
  const isMySession =
    session &&
    !session.is_final_test &&
    session.id_topic === Number(topicId) &&
    session.id_program_completion === Number(completionId);

  function isTabLocked(key) {
    if (session) {
      if (key === "test") return !isMySession;
      return true;
    }
    if (key !== "materials" && !allMaterialsRead) return true;
    return false;
  }

  function tabLockReason(key) {
    if (session) {
      if (key === "test" && !isMySession) {
        return "Сначала завершите тест, который уже начат в другом месте";
      }
      if (key !== "test") {
        return "Материалы и чат недоступны во время прохождения теста";
      }
    }
    if (key !== "materials" && !allMaterialsRead) return "Сначала изучите материалы темы";
    return "";
  }

  async function handleMarkRead(materialId) {
    await markMaterialRead(completionId, materialId);
    await reload();
  }

  async function handleSendChat(e) {
    e.preventDefault();
    if (!chatInput.trim()) return;
    setSending(true);
    try {
      await askAssistant(employee.id_employee, Number(topicId), chatInput);
      setChatInput("");
      await reload();
    } catch {
      window.alert("ИИ-ассистент временно недоступен. Попробуйте позже.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <Link to={`/app/courses/${completionId}`}>‹ К просмотру курса</Link>
      <h1>{topic.name}</h1>

      <div className="tabs mb-16">
        {TABS.map((key) => {
          const locked = isTabLocked(key);
          return (
            <div
              key={key}
              className={`tab ${tab === key ? "active" : ""}`}
              style={locked ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
              onClick={() => !locked && setTab(key)}
              title={locked ? tabLockReason(key) : ""}
            >
              {TAB_LABEL[key]}
            </div>
          );
        })}
      </div>

      <div className="panel" style={{ padding: 20 }}>
        {tab === "materials" && isTabLocked("materials") && <p>⚠ {tabLockReason("materials")}</p>}
        {tab === "materials" && !isTabLocked("materials") && (
          <div>
            {topic.materials.map((m) => (
              <div key={m.id_learning_material} className="card row-between mb-16">
                <div>📊 {materialDisplayName(m.file_link)}</div>
                {m.is_read ? (
                  <span className="badge badge-green">Изучено</span>
                ) : (
                  <a
                    className="btn btn-secondary"
                    href={materialFileUrl(m.id_learning_material)}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => handleMarkRead(m.id_learning_material)}
                  >
                    Скачать презентацию
                  </a>
                )}
              </div>
            ))}
            {topic.materials.length === 0 && <p>Материалы по теме отсутствуют.</p>}
          </div>
        )}

        {tab === "chat" && isTabLocked("chat") && <p>⚠ {tabLockReason("chat")}</p>}
        {tab === "chat" && !isTabLocked("chat") && (
          <div className="chat-window" style={{ padding: 0 }}>
            {topic.chat_history.length === 0 && (
              <div className="chat-bubble">
                <div className="bubble-text">
                  Привет! Это бот-помощник в изучении необходимого тебе материала. Задай любой вопрос по теме!
                </div>
              </div>
            )}
            {topic.chat_history.map((entry) => (
              <div key={entry.id_request}>
                <div className="chat-bubble user">
                  <div className="bubble-text">{entry.message_text}</div>
                </div>
                <div className="chat-bubble">
                  <div className="bubble-text">{entry.ai_response_text}</div>
                </div>
              </div>
            ))}
            <form className="chat-input-row" onSubmit={handleSendChat}>
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Введите сообщение"
              />
              <button className="btn btn-primary" type="submit" disabled={sending}>
                Отправить
              </button>
            </form>
          </div>
        )}

        {tab === "test" && isTabLocked("test") && <p>⚠ {tabLockReason("test")}</p>}
        {tab === "test" && !isTabLocked("test") && (
          <TestPanel
            questions={topic.questions}
            lastAttempt={topic.last_attempt}
            session={isMySession ? session : null}
            onStart={async () => {
              const s = await startTestSession(employee.id_employee, {
                idProgramCompletion: Number(completionId),
                idTopic: Number(topicId),
                isFinalTest: false,
              });
              setSession(s);
              await reload();
            }}
            onSubmit={async (answers) => {
              const outcome = await submitTopicTest(completionId, topicId, employee.id_employee, answers);
              setSession(null);
              await reload();
              return outcome;
            }}
            onAskExplanation={(questionText) =>
              askAssistant(
                employee.id_employee,
                Number(topicId),
                `Объясни, пожалуйста, правильный ответ на вопрос: ${questionText}`
              ).then((r) => r.answer)
            }
            onComplain={(questionId, text) => createComplaint(questionId, text)}
          />
        )}
      </div>
    </div>
  );
}
