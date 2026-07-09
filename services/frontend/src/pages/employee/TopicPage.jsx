import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  askAssistant,
  createComplaint,
  getTopic,
  markMaterialRead,
  materialFileUrl,
  submitTopicTest,
} from "../../api/courseProgress";
import { useAuth } from "../../auth/AuthContext";
import TestPanel from "../../components/TestPanel";

const TABS = ["materials", "chat", "test"];
const TAB_LABEL = { materials: "Материалы по теме", chat: "Чат с AI", test: "Контрольный тест" };

function materialDisplayName(fileLink) {
  return fileLink.replace(/^[0-9a-f]{32}_/, "");
}

export default function TopicPage() {
  const { completionId, topicId } = useParams();
  const { employee } = useAuth();
  const [topic, setTopic] = useState(null);
  const [tab, setTab] = useState("materials");
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);

  function reload() {
    return getTopic(completionId, topicId, employee.id_employee).then(setTopic);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completionId, topicId]);

  if (!topic) return <p>Загрузка…</p>;

  const allMaterialsRead = topic.materials.every((m) => m.is_read);

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
          const locked = key !== "materials" && !allMaterialsRead;
          return (
            <div
              key={key}
              className={`tab ${tab === key ? "active" : ""}`}
              style={locked ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
              onClick={() => !locked && setTab(key)}
              title={locked ? "Сначала изучите материалы темы" : ""}
            >
              {TAB_LABEL[key]}
            </div>
          );
        })}
      </div>

      <div className="panel" style={{ padding: 20 }}>
        {tab === "materials" && (
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

        {tab === "chat" && allMaterialsRead && (
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

        {tab === "test" && allMaterialsRead && (
          <TestPanel
            questions={topic.questions}
            lastAttempt={topic.last_attempt}
            onSubmit={async (answers) => {
              const outcome = await submitTopicTest(completionId, topicId, employee.id_employee, answers);
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
