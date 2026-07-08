import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import RequireAuth from "./auth/RequireAuth";
import RequireRole from "./auth/RequireRole";
import Layout from "./components/Layout";

import LoginPage from "./pages/auth/LoginPage";
import ForgotPasswordPage from "./pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "./pages/auth/ResetPasswordPage";

import ProfilePage from "./pages/profile/ProfilePage";
import ChangePasswordPage from "./pages/profile/ChangePasswordPage";

import CoursesListPage from "./pages/employee/CoursesListPage";
import CourseDetailPage from "./pages/employee/CourseDetailPage";
import TopicPage from "./pages/employee/TopicPage";
import FinalTestPage from "./pages/employee/FinalTestPage";
import NotificationsPage from "./pages/employee/NotificationsPage";

import QuestionBankPage from "./pages/specialist/QuestionBankPage";
import ResultsPage from "./pages/specialist/ResultsPage";

import CourseManagementPage from "./pages/admin/CourseManagementPage";
import CreateCoursePage from "./pages/admin/CreateCoursePage";

const HOME_BY_ROLE = {
  employee: "/app/courses",
  specialist: "/app/questions",
  admin: "/app/admin/courses",
};

function AppHome() {
  const { role } = useAuth();
  return <Navigate to={HOME_BY_ROLE[role]} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          <Route element={<RequireAuth />}>
            <Route path="/app" element={<Layout />}>
              <Route index element={<AppHome />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="profile/change-password" element={<ChangePasswordPage />} />

              <Route element={<RequireRole roles={["employee"]} />}>
                <Route path="courses" element={<CoursesListPage />} />
                <Route path="courses/:completionId" element={<CourseDetailPage />} />
                <Route path="courses/:completionId/final-test" element={<FinalTestPage />} />
                <Route path="courses/:completionId/topics/:topicId" element={<TopicPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
              </Route>

              <Route element={<RequireRole roles={["specialist"]} />}>
                <Route path="questions" element={<QuestionBankPage />} />
                <Route path="results" element={<ResultsPage />} />
              </Route>

              <Route element={<RequireRole roles={["admin"]} />}>
                <Route path="admin/courses" element={<CourseManagementPage />} />
                <Route path="admin/courses/new" element={<CreateCoursePage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
