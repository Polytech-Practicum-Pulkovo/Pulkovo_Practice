import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { addLiterature, addTopicManual, createProgram, updateProgram, uploadMaterial } from "../../api/courseManagement";
import Modal from "../../components/Modal";

const STEPS = ["program", "distribution", "materials"];

let keySeq = 0;
function nextKey() {
  keySeq += 1;
  return `local-${keySeq}`;
}

export default function CreateCoursePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [confirmMethodOpen, setConfirmMethodOpen] = useState(false);

  // Ничего из введённого ниже не попадает в БД, пока пользователь не нажмёт
  // "Сохранить" на последнем шаге — при выходе из мастера раньше это время
  // всё просто отбрасывается.
  const [programFile, setProgramFile] = useState(null);
  const [name, setName] = useState("");
  const [programCode, setProgramCode] = useState("");
  const [programError, setProgramError] = useState("");

  const [topics, setTopics] = useState([]);
  const [hours, setHours] = useState("");
  const [distributionError, setDistributionError] = useState("");

  const [materials, setMaterials] = useState({}); // { [topicKey]: [{key, file}] }
  const [materialsError, setMaterialsError] = useState("");
  const [saving, setSaving] = useState(false);

  const [literature, setLiterature] = useState([]);
  const [litName, setLitName] = useState("");
  const [litLink, setLitLink] = useState("");

  function handleSubmitProgram(e) {
    e.preventDefault();
    if (!programFile) {
      setProgramError("Загрузите файл программы обучения перед тем, как продолжить");
      return;
    }
    setProgramError("");
    setConfirmMethodOpen(true);
  }

  function handleChooseMethod() {
    // ИИ-модуль ещё не подключён — обе кнопки пока ведут к одной и той же
    // форме ручного заполнения.
    setConfirmMethodOpen(false);
    setStep(1);
  }

  function addLocalTopic() {
    setTopics((prev) => [...prev, { key: nextKey(), name: "" }]);
  }

  function updateLocalTopicName(key, value) {
    setTopics((prev) => prev.map((t) => (t.key === key ? { ...t, name: value } : t)));
  }

  function removeLocalTopic(key) {
    setTopics((prev) => prev.filter((t) => t.key !== key));
    setMaterials((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  function handleAddLiterature() {
    if (!litName.trim()) return;
    setLiterature((prev) => [...prev, { key: nextKey(), name: litName.trim(), link: litLink.trim() }]);
    setLitName("");
    setLitLink("");
  }

  function handleRemoveLiterature(key) {
    setLiterature((prev) => prev.filter((l) => l.key !== key));
  }

  function handleConfirmDistribution() {
    const validTopics = topics.filter((t) => t.name.trim());

    if (validTopics.length === 0) {
      setDistributionError("Добавьте хотя бы одну тему");
      return;
    }
    if (!hours || Number(hours) <= 0) {
      setDistributionError("Укажите количество часов на выполнение курса");
      return;
    }

    setDistributionError("");
    setTopics(validTopics);
    setStep(2);
  }

  function handleMaterialFile(topicKey, file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pptx")) {
      window.alert("Допустимы только PPTX-файлы");
      return;
    }
    setMaterials((prev) => ({
      ...prev,
      [topicKey]: [...(prev[topicKey] || []), { key: nextKey(), file }],
    }));
  }

  function handleRemoveMaterial(topicKey, fileKey) {
    setMaterials((prev) => ({
      ...prev,
      [topicKey]: (prev[topicKey] || []).filter((m) => m.key !== fileKey),
    }));
  }

  async function handleSaveAll() {
    const topicsWithoutMaterial = topics.filter((t) => !(materials[t.key] || []).length);
    if (topicsWithoutMaterial.length > 0) {
      setMaterialsError(
        `Загрузите материал для темы «${topicsWithoutMaterial[0].name}» — материал обязателен для каждой темы`
      );
      return;
    }

    setMaterialsError("");
    setSaving(true);
    try {
      const { id_program } = await createProgram({ name, program_code: programCode });

      for (const topic of topics) {
        const { id_topic } = await addTopicManual(id_program, topic.name.trim());
        for (const material of materials[topic.key] || []) {
          await uploadMaterial(id_topic, material.file);
        }
      }

      await updateProgram(id_program, { time_to_complete: Number(hours) });

      for (const lit of literature) {
        await addLiterature(id_program, lit.name, lit.link || null);
      }

      navigate("/app/admin/courses");
    } catch {
      setMaterialsError("Не удалось сохранить курс. Попробуйте ещё раз.");
    } finally {
      setSaving(false);
    }
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
          <form onSubmit={handleSubmitProgram}>
            <p>Загрузите программу обучения в формате doc или docx</p>
            <input
              type="file"
              accept=".doc,.docx"
              onChange={(e) => setProgramFile(e.target.files?.[0] || null)}
              className="mb-16"
            />
            {programFile && <p>📄 {programFile.name}</p>}

            <div className="field">
              <label>Название программы</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label>Номер программы</label>
              <input value={programCode} onChange={(e) => setProgramCode(e.target.value)} required />
            </div>

            {programError && <div className="alert alert-error">⚠ {programError}</div>}

            <button className="btn btn-primary" type="submit">
              Перейти к распределению по темам
            </button>
          </form>
        )}

        {STEPS[step] === "distribution" && (
          <div>
            <h3>Распределение по темам</h3>
            {topics.map((t) => (
              <div key={t.key} className="row mb-16">
                <input
                  style={{ flex: 1 }}
                  placeholder="Название темы"
                  value={t.name}
                  onChange={(e) => updateLocalTopicName(t.key, e.target.value)}
                />
                <button className="icon-btn" onClick={() => removeLocalTopic(t.key)}>
                  ✕
                </button>
              </div>
            ))}
            <button className="icon-btn mb-16" onClick={addLocalTopic}>
              +
            </button>

            <h3>Список литературы к курсу</h3>
            {literature.map((l) => (
              <div key={l.key} className="row-between mb-16">
                <div>
                  <div>{l.name}</div>
                  {l.link && <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{l.link}</div>}
                </div>
                <button className="icon-btn" onClick={() => handleRemoveLiterature(l.key)}>
                  ✕
                </button>
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

            <div className="field" style={{ maxWidth: 240 }}>
              <label>Время на выполнение (в часах)</label>
              <input
                type="number"
                min="0"
                placeholder="10"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
              />
            </div>

            {distributionError && <div className="alert alert-error">⚠ {distributionError}</div>}

            <button className="btn btn-primary" onClick={handleConfirmDistribution}>
              Утвердить
            </button>
          </div>
        )}

        {STEPS[step] === "materials" && (
          <div>
            <h3>Материалы по темам</h3>
            <p>Загрузите файл в формате PPTX для каждой темы — без него курс сохранить нельзя.</p>
            {topics.map((t) => (
              <div key={t.key} className="row-between mb-16">
                <span>{t.name}</span>
                <div>
                  {(materials[t.key] || []).map((m) => (
                    <div key={m.key} className="row">
                      📊 {m.file.name}
                      <button className="link-button" onClick={() => handleRemoveMaterial(t.key, m.key)}>
                        ✕
                      </button>
                    </div>
                  ))}
                  <input
                    type="file"
                    accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    onChange={(e) => {
                      handleMaterialFile(t.key, e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                </div>
              </div>
            ))}

            {materialsError && <div className="alert alert-error">⚠ {materialsError}</div>}

            <button className="btn btn-primary" onClick={handleSaveAll} disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить"}
            </button>
          </div>
        )}
      </div>

      {confirmMethodOpen && (
        <Modal>
          <h3>Как определить темы, часы и литературу?</h3>
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
            ИИ-модуль ещё не подключён — обе кнопки пока приводят к одной и той же форме ручного заполнения.
          </p>
          <div className="row mt-16">
            <button className="btn btn-secondary" onClick={handleChooseMethod}>
              ✨ С помощью ИИ
            </button>
            <button className="btn btn-primary" onClick={handleChooseMethod}>
              Вручную
            </button>
          </div>
        </Modal>
      )}

      {confirmLeave && (
        <Modal onClose={() => setConfirmLeave(false)}>
          <h3>Прервать создание нового курса?</h3>
          <p>Курс не будет сохранён — все введённые данные будут потеряны.</p>
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
