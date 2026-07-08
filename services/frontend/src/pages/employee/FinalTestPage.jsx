import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { askAssistant, createComplaint, getFinalTest, submitFinalTest } from "../../api/courseProgress";
import { useAuth } from "../../auth/AuthContext";
import TestPanel from "../../components/TestPanel";

export default function FinalTestPage() {
  const { completionId } = useParams();
  const { employee } = useAuth();
  const [data, setData] = useState(null);

  function reload() {
    return getFinalTest(completionId).then(setData);
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completionId]);

  if (!data) return <p>Загрузка…</p>;

  return (
    <div>
      <Link to={`/app/courses/${completionId}`}>‹ К просмотру курса</Link>
      <h1>Итоговый тест</h1>

      <div className="panel" style={{ padding: 20 }}>
        <TestPanel
          questions={data.questions}
          lastAttempt={data.last_attempt}
          onSubmit={async (answers) => {
            const outcome = await submitFinalTest(completionId, employee.id_employee, answers);
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
      </div>
    </div>
  );
}
