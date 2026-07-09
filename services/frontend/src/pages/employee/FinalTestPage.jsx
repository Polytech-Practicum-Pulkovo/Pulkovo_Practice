import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  askAssistant,
  createComplaint,
  getFinalTest,
  getTestSession,
  startTestSession,
  submitFinalTest,
} from "../../api/courseProgress";
import { useAuth } from "../../auth/AuthContext";
import TestPanel from "../../components/TestPanel";

const SESSION_POLL_MS = 20000;

export default function FinalTestPage() {
  const { completionId } = useParams();
  const { employee } = useAuth();
  const [data, setData] = useState(null);
  const [session, setSession] = useState(null);

  function reload() {
    return getFinalTest(completionId).then(setData);
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
  }, [completionId]);

  if (!data) return <p>Загрузка…</p>;

  const isMySession =
    session && session.is_final_test && session.id_program_completion === Number(completionId);
  const lockedByOtherSession = session && !isMySession;

  return (
    <div>
      <Link to={`/app/courses/${completionId}`}>‹ К просмотру курса</Link>
      <h1>Итоговый тест</h1>

      <div className="panel" style={{ padding: 20 }}>
        {lockedByOtherSession ? (
          <p>⚠ Сначала завершите тест, который уже начат в другом месте.</p>
        ) : (
          <TestPanel
            questions={data.questions}
            lastAttempt={data.last_attempt}
            session={isMySession ? session : null}
            onStart={async () => {
              const s = await startTestSession(employee.id_employee, {
                idProgramCompletion: Number(completionId),
                idTopic: null,
                isFinalTest: true,
              });
              setSession(s);
            }}
            onSubmit={async (answers) => {
              const outcome = await submitFinalTest(completionId, employee.id_employee, answers);
              setSession(null);
              await reload();
              return outcome;
            }}
            onAskExplanation={(questionText) =>
              askAssistant(
                employee.id_employee,
                null,
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
