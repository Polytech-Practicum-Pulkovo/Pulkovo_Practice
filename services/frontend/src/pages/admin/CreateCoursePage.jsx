import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { addLiterature, addTopicManual, addTopicsAi, createProgram, deleteTopic } from "../../api/courseManagement";
import Modal from "../../components/Modal";

const STEPS = ["program", "topics", "materials", "literature"];

export default function CreateCoursePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [confirmLeave, setConfirmLeave] = useState(false);

  const [fileName, setFileName] = useState("");
  const [name, setName] = useState("");
  const [programCode, setProgramCode] = useState("");
  const [timeToComplete, setTimeToComplete] = useState("");
  const [programId, setProgramId] = useState(null);

  const [topics, setTopics] = useState([]);
  const [newTopicName, setNewTopicName] = useState("");

  const [materialNames, setMaterialNames] = useState({});

  const [literature, setLiterature] = useState([]);
  const [litName, setLitName] = useState("");
  const [litLink, setLitLink] = useState("");

  async function handleCreateProgram(e) {
    e.preventDefault();
    const { id_program } = await createProgram({
      name,
      program_code: programCode,
      time_to_complete: timeToComplete ? Number(timeToComplete) : null,
    });
    setProgramId(id_program);
    setStep(1);
  }

  async function handleAddTopicManual() {
    if (!newTopicName.trim()) return;
    const created = await addTopicManual(programId, newTopicName.trim());
    setTopics((prev) => [...prev, created]);
    setNewTopicName("");
  }

  async function handleAiTopics() {
    try {
      const { topics: created } = await addTopicsAi(programId, ["Тема 1", "Тема 2", "Тема 3"]);
      setTopics((prev) => [...prev, ...created]);
    } catch {
      window.alert("ИИ-генерация тем временно недоступна. Добавьте темы вручную.");
    }
  }

  async function handleRemoveTopic(topicId) {
    await deleteTopic(topicId);
    setTopics((prev) => prev.filter((t) => t.id_topic !== topicId));
  }

  function handleMaterialFile(topicId, file) {
    setMaterialNames((prev) => ({ ...prev, [topicId]: file?.name || "" }));
  }

  async function handleAddLiterature() {
    if (!litName.trim()) return;
    const { id_literature } = await addLiterature(programId, litName.trim(), litLink.trim() || null);
    setLiterature((prev) => [...prev, { id_literature, name: litName.trim(), material_link: litLink.trim() }]);
    setLitName("");
    setLitLink("");
  }

  return (
    <div>
      <div className="row-between mb-16">
        <button className="link-button" onClick={() => setConfirmLeave(true)}>
          ‹ Назад к управлению курсами
        </button>
      </div>
      <h1>Создание нового курса</h1>

      <div className="panel" style={{ padding: 20 }}>
        {STEPS[step] === "program" && (
          <form onSubmit={handleCreateProgram}>
            <p>Загрузите программу обучения в формате xlsx</p>
            <input
              type="file"
              accept=".xlsx"
              onChange={(e) => setFileName(e.target.files?.[0]?.name || "")}
              className="mb-16"
            />
            {fileName && <p>📊 {fileName}</p>}

            <div className="field">
              <label>Название программы</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label>Номер программы</label>
              <input value={programCode} onChange={(e) => setProgramCode(e.target.value)} required />
            </div>
            <div className="field">
              <label>Время на выполнение (в минутах)</label>
              <input
                type="number"
                min="0"
                placeholder="600"
                value={timeToComplete}
                onChange={(e) => setTimeToComplete(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" type="submit">
              Перейти к распределению по темам
            </button>
          </form>
        )}

        {STEPS[step] === "topics" && (
          <div>
            <div className="row-between mb-16">
              <h3>Распределение по темам</h3>
              <button className="btn btn-secondary" onClick={handleAiTopics}>
                ✨ ИИ-генерация
              </button>
            </div>
            {topics.map((t) => (
              <div key={t.id_topic} className="row-between mb-16">
                <span>{t.name}</span>
                <button className="link-button" onClick={() => handleRemoveTopic(t.id_topic)}>
                  ✕
                </button>
              </div>
            ))}
            <div className="row mb-16">
              <input
                placeholder="Добавить тему"
                value={newTopicName}
                onChange={(e) => setNewTopicName(e.target.value)}
              />
              <button className="btn btn-secondary" onClick={handleAddTopicManual}>
                +
              </button>
            </div>
            <button className="btn btn-primary" disabled={topics.length === 0} onClick={() => setStep(2)}>
              Подтвердить распределение
            </button>
          </div>
        )}

        {STEPS[step] === "materials" && (
          <div>
            <h3>Материалы по темам</h3>
            {topics.map((t) => (
              <div key={t.id_topic} className="row-between mb-16">
                <span>{t.name}</span>
                <div>
                  <input type="file" onChange={(e) => handleMaterialFile(t.id_topic, e.target.files?.[0])} />
                  {materialNames[t.id_topic] && <div>📄 {materialNames[t.id_topic]}</div>}
                </div>
              </div>
            ))}
            <button className="btn btn-primary" onClick={() => setStep(3)}>
              Далее
            </button>
          </div>
        )}

        {STEPS[step] === "literature" && (
          <div>
            <h3>Список литературы к курсу</h3>
            {literature.map((l) => (
              <div key={l.id_literature} className="row-between mb-16">
                <span>{l.name}</span>
                <span>{l.material_link}</span>
              </div>
            ))}
            <div className="field">
              <label>Название*</label>
              <input value={litName} onChange={(e) => setLitName(e.target.value)} />
            </div>
            <div className="field">
              <label>Ссылка</label>
              <input value={litLink} onChange={(e) => setLitLink(e.target.value)} />
            </div>
            <button className="btn btn-secondary mb-16" onClick={handleAddLiterature}>
              Добавить источник +
            </button>
            <br />
            <button className="btn btn-primary" onClick={() => navigate("/app/admin/courses")}>
              Сохранить
            </button>
          </div>
        )}
      </div>

      {confirmLeave && (
        <Modal onClose={() => setConfirmLeave(false)}>
          <h3>Прервать создание нового курса?</h3>
          <p>Все несохранённые изменения на текущем шаге будут потеряны.</p>
          <div className="row">
            <button className="btn btn-secondary" onClick={() => setConfirmLeave(false)}>
              Назад
            </button>
            <Link className="btn btn-danger" to="/app/admin/courses">
              Всё равно продолжить
            </Link>
          </div>
        </Modal>
      )}
    </div>
  );
}
