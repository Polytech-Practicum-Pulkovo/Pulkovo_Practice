import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  bulkAssign,
  bulkUnassign,
  deleteProgram,
  listAssignments,
  listPositions,
  listPrograms,
} from "../../api/courseManagement";
import Modal from "../../components/Modal";

function EditPositionsModal({ program, onClose, onChanged }) {
  const [assignments, setAssignments] = useState([]);
  const [positions, setPositions] = useState([]);
  const [addingPositionId, setAddingPositionId] = useState("");

  function reload() {
    return listAssignments(program.id_program).then(setAssignments);
  }

  useEffect(() => {
    reload();
    listPositions().then(setPositions);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRemove(idPosition) {
    await bulkUnassign(program.id_program, idPosition);
    await reload();
    onChanged();
  }

  async function handleAdd() {
    if (!addingPositionId) return;
    await bulkAssign(program.id_program, Number(addingPositionId));
    setAddingPositionId("");
    await reload();
    onChanged();
  }

  const availablePositions = positions.filter(
    (p) => !assignments.some((a) => a.id_position === p.id_position)
  );

  return (
    <Modal onClose={onClose} width={560}>
      <h3>Редактирование должностей</h3>
      <p>Курс «{program.name}»</p>
      <table className="table">
        <thead>
          <tr>
            <th>Подразделение</th>
            <th>Должность</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((a) => (
            <tr key={a.id_position}>
              <td>{a.department || "—"}</td>
              <td>{a.position}</td>
              <td>
                <button className="link-button" onClick={() => handleRemove(a.id_position)}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="row mt-16">
        <select value={addingPositionId} onChange={(e) => setAddingPositionId(e.target.value)}>
          <option value="">Добавить должность…</option>
          {availablePositions.map((p) => (
            <option key={p.id_position} value={p.id_position}>
              {p.name}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={handleAdd}>
          +
        </button>
      </div>
    </Modal>
  );
}

export default function CourseManagementPage() {
  const [programs, setPrograms] = useState([]);
  const [confirmingDelete, setConfirmingDelete] = useState(null);
  const [editingProgram, setEditingProgram] = useState(null);

  function reload() {
    return listPrograms().then(setPrograms);
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleDelete(programId) {
    await deleteProgram(programId);
    setConfirmingDelete(null);
    reload();
  }

  return (
    <div>
      <div className="row-between mb-16">
        <h1>Управление курсами</h1>
        <Link className="btn btn-primary" to="/app/admin/courses/new">
          Создать новый курс
        </Link>
      </div>

      {programs.map((p) => (
        <div key={p.id_program} className="panel mb-16" style={{ padding: 16 }}>
          <div className="row-between">
            <div>
              <strong>{p.name}</strong>
              <div>Номер: {p.program_code}</div>
              <div>Время на выполнение: {p.time_to_complete ? `${p.time_to_complete} ч` : "—"}</div>
              <div>Тем в курсе: {p.topic_count}</div>
            </div>
            <div className="row" style={{ flexDirection: "column" }}>
              <button className="btn btn-danger" onClick={() => setConfirmingDelete(p)}>
                Удалить
              </button>
              <button className="btn btn-secondary" onClick={() => setEditingProgram(p)}>
                Редактировать должности
              </button>
            </div>
          </div>
        </div>
      ))}
      {programs.length === 0 && <div className="empty-state">Курсов пока нет</div>}

      {confirmingDelete && (
        <Modal onClose={() => setConfirmingDelete(null)}>
          <h3>Удалить курс?</h3>
          <p>Курс «{confirmingDelete.name}» будет удалён.</p>
          <div className="row">
            <button className="btn btn-secondary" onClick={() => setConfirmingDelete(null)}>
              Назад
            </button>
            <button className="btn btn-danger" onClick={() => handleDelete(confirmingDelete.id_program)}>
              Удалить
            </button>
          </div>
        </Modal>
      )}

      {editingProgram && (
        <EditPositionsModal
          program={editingProgram}
          onClose={() => setEditingProgram(null)}
          onChanged={reload}
        />
      )}
    </div>
  );
}
