import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProgramCompletions } from "../../api/progressLoader";
import { useAuth } from "../../auth/AuthContext";
import { formatDate } from "../../utils/format";

const TABS = [
  { key: "all", label: "Все курсы" },
  { key: "started", label: "Начатые" },
  { key: "done", label: "Завершённые" },
];

function statusLabel(course) {
  if (course.end_date) return "Завершён";
  if (course.progress_percent > 0) return "В процессе";
  return "Не начат";
}

export default function CoursesListPage() {
  const { employee } = useAuth();
  const [courses, setCourses] = useState([]);
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    listProgramCompletions(employee.id_employee, true)
      .then((data) => alive && setCourses(data))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [employee.id_employee]);

  const filtered = courses.filter((course) => {
    if (tab === "started") return !course.end_date && course.progress_percent > 0;
    if (tab === "done") return Boolean(course.end_date);
    return true;
  });

  return (
    <div>
      <h1>Мои курсы</h1>
      <div className="tabs mb-16">
        {TABS.map((t) => (
          <div key={t.key} className={`tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </div>
        ))}
      </div>

      {loading && <p>Загрузка…</p>}

      {!loading && filtered.length === 0 && <div className="empty-state">Курсов не найдено</div>}

      <div className="course-grid">
        {filtered.map((course) => (
          <Link
            key={course.id_program_completion}
            to={`/app/courses/${course.id_program_completion}`}
            className="course-card"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="thumb">📘</div>
            <div className="body">
              <h3>«{course.program_name}»</h3>
              <div>Статус: {statusLabel(course)}</div>
              {!course.end_date && (
                <div className="row mt-16">
                  <div className="progress-bar">
                    <div className="progress-bar-fill" style={{ width: `${course.progress_percent}%` }} />
                  </div>
                  <span>{course.progress_percent}%</span>
                </div>
              )}
              <div className="mt-16" style={{ fontSize: 13, color: "var(--text-muted)" }}>
                Начало: {formatDate(course.start_date)}
                <br />
                Конец: {formatDate(course.end_date)}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
