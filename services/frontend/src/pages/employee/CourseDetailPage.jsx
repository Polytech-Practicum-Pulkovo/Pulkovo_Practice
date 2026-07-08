import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCourse } from "../../api/courseProgress";
import { getProgram } from "../../api/courseManagement";
import Modal from "../../components/Modal";

const STATUS_LABEL = {
  passed: "Пройдена",
  in_progress: "В процессе",
  not_started: "Не начата",
};

export default function CourseDetailPage() {
  const { completionId } = useParams();
  const [course, setCourse] = useState(null);
  const [literature, setLiterature] = useState([]);
  const [showLiterature, setShowLiterature] = useState(false);

  useEffect(() => {
    let alive = true;
    getCourse(completionId).then((data) => {
      if (!alive) return;
      setCourse(data);
      getProgram(data.id_program).then((program) => alive && setLiterature(program.literature || []));
    });
    return () => {
      alive = false;
    };
  }, [completionId]);

  if (!course) return <p>Загрузка…</p>;

  const allPassed = course.topics.every((t) => t.status === "passed");
  const avgProgress = course.topics.length
    ? Math.round(course.topics.reduce((sum, t) => sum + t.progress_percent, 0) / course.topics.length)
    : 0;

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
              <div className="progress-bar-fill" style={{ width: `${avgProgress}%` }} />
            </div>
            <span>{avgProgress}%</span>
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
            {course.topics.map((topic) => (
              <tr key={topic.id_topic}>
                <td>
                  <Link to={`/app/courses/${completionId}/topics/${topic.id_topic}`}>{topic.name}</Link>
                </td>
                <td>{topic.progress_percent}%</td>
                <td>{STATUS_LABEL[topic.status]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row-between mt-16">
        {allPassed ? (
          <Link className="btn btn-primary" to={`/app/courses/${completionId}/final-test`}>
            Перейти к итоговому тесту
          </Link>
        ) : (
          <button className="btn btn-primary" disabled title="Пройдите все промежуточные тесты">
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
