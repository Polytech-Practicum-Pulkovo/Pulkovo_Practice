import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCourse, getFinalTest, getTestSession } from "../../api/courseProgress";
import { getProgram } from "../../api/courseManagement";
import { useAuth } from "../../auth/AuthContext";
import Modal from "../../components/Modal";

const SESSION_POLL_MS = 20000;

const STATUS_LABEL = {
  passed: "Пройдена",
  in_progress: "В процессе",
  not_started: "Не начата",
};

export default function CourseDetailPage() {
  const { completionId } = useParams();
  const { employee } = useAuth();
  const [course, setCourse] = useState(null);
  const [finalTest, setFinalTest] = useState(null);
  const [literature, setLiterature] = useState([]);
  const [showLiterature, setShowLiterature] = useState(false);
  const [session, setSession] = useState(null);

  useEffect(() => {
    let alive = true;
    getCourse(completionId).then((data) => {
      if (!alive) return;
      setCourse(data);
      getProgram(data.id_program).then((program) => alive && setLiterature(program.literature || []));
    });
    getFinalTest(completionId).then((data) => alive && setFinalTest(data));
    return () => {
      alive = false;
    };
  }, [completionId]);

  useEffect(() => {
    function reloadSession() {
      getTestSession(employee.id_employee).then((s) => setSession(s.active ? s : null));
    }
    reloadSession();
    const interval = setInterval(reloadSession, SESSION_POLL_MS);
    return () => clearInterval(interval);
  }, [employee.id_employee]);

  if (!course) return <p>Загрузка…</p>;

  const allPassed = course.topics.every((t) => t.status === "passed");
  const isMyFinalTestSession =
    session && session.is_final_test && session.id_program_completion === Number(completionId);
  const lockedByOtherSession = Boolean(session) && !isMyFinalTestSession;

  function isTopicLocked(topicId) {
    if (!session) return false;
    return !(
      !session.is_final_test &&
      session.id_topic === topicId &&
      session.id_program_completion === Number(completionId)
    );
  }

  // Процент прохождения = доля успешно пройденных тестов (темы + итоговый),
  // изучение материалов на него не влияет.
  const totalTests = course.topics.length + 1;
  const passedTopics = course.topics.filter((t) => t.status === "passed").length;
  const passedFinal = finalTest?.last_attempt?.passed ? 1 : 0;
  const overallPercent = Math.round((100 * (passedTopics + passedFinal)) / totalTests);

  return (
    <div>
      <Link to="/app/courses">‹ Назад к курсам</Link>
      <div className="row-between mt-16">
        <h1>«{course.program_name}»</h1>
      </div>
      <div className="row-between mb-16">
        <div>
          Статус: {course.end_date ? "Завершён" : "В процессе"}
          <div className="row mt-16">
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${overallPercent}%` }} />
            </div>
            <span>{overallPercent}%</span>
          </div>
        </div>
      </div>

      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Тема</th>
              <th>Прогресс</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {course.topics.map((topic) => {
              const locked = isTopicLocked(topic.id_topic);
              return (
                <tr key={topic.id_topic}>
                  <td>
                    {locked ? (
                      <span
                        style={{ color: "var(--text-muted)", cursor: "not-allowed" }}
                        title="Сначала завершите тест, который уже начат в другом месте"
                      >
                        {topic.name}
                      </span>
                    ) : (
                      <Link to={`/app/courses/${completionId}/topics/${topic.id_topic}`}>{topic.name}</Link>
                    )}
                  </td>
                  <td>{topic.progress_percent}%</td>
                  <td>{STATUS_LABEL[topic.status]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="row-between mt-16">
        {allPassed && !lockedByOtherSession ? (
          <Link className="btn btn-primary" to={`/app/courses/${completionId}/final-test`}>
            Перейти к итоговому тесту
          </Link>
        ) : (
          <button
            className="btn btn-primary"
            disabled
            title={
              lockedByOtherSession
                ? "Сначала завершите тест, который уже начат в другом месте"
                : "Пройдите все промежуточные тесты"
            }
          >
            Перейти к итоговому тесту
          </button>
        )}
        <button className="link-button" onClick={() => setShowLiterature(true)}>
          Список литературы
        </button>
      </div>

      {showLiterature && (
        <Modal onClose={() => setShowLiterature(false)}>
          <h3>Список литературы</h3>
          <ol>
            {literature.map((item) => (
              <li key={item.id_literature}>
                {item.name}
                {item.material_link ? (
                  <>
                    {" — "}
                    <a href={item.material_link} target="_blank" rel="noreferrer">
                      ссылка
                    </a>
                  </>
                ) : null}
              </li>
            ))}
            {literature.length === 0 && <li>Список литературы пока не заполнен</li>}
          </ol>
        </Modal>
      )}
    </div>
  );
}
