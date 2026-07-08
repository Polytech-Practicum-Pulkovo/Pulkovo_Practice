import { useEffect, useState } from "react";
import { listDepartments, listPositions, listPrograms } from "../../api/courseManagement";
import { getJournal, getStats } from "../../api/progressLoader";

function useFilterOptions() {
  const [programs, setPrograms] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    listPrograms().then(setPrograms);
    listDepartments().then(setDepartments);
    listPositions().then(setPositions);
  }, []);

  return { programs, departments, positions };
}

function FiltersBar({ filters, setFilters, options }) {
  function set(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="filters-grid">
      <select value={filters.id_program} onChange={(e) => set("id_program", e.target.value)}>
        <option value="">Курсы</option>
        {options.programs.map((p) => (
          <option key={p.id_program} value={p.id_program}>
            {p.name}
          </option>
        ))}
      </select>
      <select value={filters.id_department} onChange={(e) => set("id_department", e.target.value)}>
        <option value="">Подразделение</option>
        {options.departments.map((d) => (
          <option key={d.id_department} value={d.id_department}>
            {d.name}
          </option>
        ))}
      </select>
      <select value={filters.id_position} onChange={(e) => set("id_position", e.target.value)}>
        <option value="">Должность</option>
        {options.positions.map((p) => (
          <option key={p.id_position} value={p.id_position}>
            {p.name}
          </option>
        ))}
      </select>
      <input
        placeholder="Табельный номер"
        value={filters.employee_number}
        onChange={(e) => set("employee_number", e.target.value)}
      />
      <input placeholder="ФИО" value={filters.name} onChange={(e) => set("name", e.target.value)} />
      <input type="date" value={filters.date_from} onChange={(e) => set("date_from", e.target.value)} />
      <input type="date" value={filters.date_to} onChange={(e) => set("date_to", e.target.value)} />
    </div>
  );
}

function JournalTab({ filters }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    getJournal(filters).then(setRows);
  }, [filters]);

  return (
    <div className="panel">
      <table className="table">
        <thead>
          <tr>
            <th>Табельный номер</th>
            <th>ФИО</th>
            <th>Курс</th>
            <th>Процент прохождения</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id_program_completion}>
              <td>{row.employee_number}</td>
              <td>
                {row.last_name} {row.first_name} {row.middle_name}
              </td>
              <td>{row.program_name}</td>
              <td>
                <div className="row">
                  <div className="progress-bar">
                    <div className="progress-bar-fill" style={{ width: `${row.progress_percent}%` }} />
                  </div>
                  {row.progress_percent}%
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <div className="empty-state">Нет данных по выбранным фильтрам</div>}
    </div>
  );
}

function DashboardTab({ filters }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getStats(filters).then(setStats);
  }, [filters]);

  if (!stats) return <p>Загрузка…</p>;

  return (
    <div className="panel" style={{ padding: 20 }}>
      <div className="stats-row">
        <div className="stat-box">
          <div className="value">{stats.employees}</div>
          <div className="label">Работников</div>
        </div>
        <div className="stat-box">
          <div className="value">{stats.assigned_courses}</div>
          <div className="label">Назначенных курсов</div>
        </div>
        <div className="stat-box">
          <div className="value">{stats.passed}</div>
          <div className="label">Количество сдавших</div>
        </div>
        <div className="stat-box">
          <div className="value">{stats.in_progress}</div>
          <div className="label">Количество в процессе</div>
        </div>
        <div className="stat-box">
          <div className="value">{stats.not_started}</div>
          <div className="label">Количество не начавших</div>
        </div>
        <div className="stat-box">
          <div className="value">{stats.average_percent}%</div>
          <div className="label">Средний процент усвоения</div>
        </div>
      </div>

      <div className="leaders-grid mt-16">
        <div>
          <h3>Лидеры</h3>
          <ol>
            {stats.leaders.map((l) => (
              <li key={l.employee_number}>
                {l.employee_number} | {l.full_name} {l.progress_percent}%
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h3>Антилидеры</h3>
          <ol>
            {stats.laggards.map((l) => (
              <li key={l.employee_number}>
                {l.employee_number} | {l.full_name} {l.progress_percent}%
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

const EMPTY_FILTERS = {
  id_program: "",
  id_department: "",
  id_position: "",
  employee_number: "",
  name: "",
  date_from: "",
  date_to: "",
};

export default function ResultsPage() {
  const [tab, setTab] = useState("journal");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const options = useFilterOptions();

  return (
    <div>
      <h1>Результаты обучения</h1>
      <div className="tabs mb-16">
        <div className={`tab ${tab === "journal" ? "active" : ""}`} onClick={() => setTab("journal")}>
          Журнал прохождений
        </div>
        <div className={`tab ${tab === "dashboard" ? "active" : ""}`} onClick={() => setTab("dashboard")}>
          Просмотр дашборда
        </div>
      </div>

      <FiltersBar filters={filters} setFilters={setFilters} options={options} />

      {tab === "journal" ? <JournalTab filters={filters} /> : <DashboardTab filters={filters} />}
    </div>
  );
}
