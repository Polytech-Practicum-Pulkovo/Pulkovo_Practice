export const API = {
  personalData: import.meta.env.VITE_PERSONAL_DATA_URL || "http://localhost:8001",
  progressLoader: import.meta.env.VITE_PROGRESS_LOADER_URL || "http://localhost:8002",
  notifications: import.meta.env.VITE_NOTIFICATIONS_URL || "http://localhost:8003",
  aiGeneration: import.meta.env.VITE_AI_GENERATION_URL || "http://localhost:8004",
  courseProgress: import.meta.env.VITE_COURSE_PROGRESS_URL || "http://localhost:8005",
  courseManagement: import.meta.env.VITE_COURSE_MANAGEMENT_URL || "http://localhost:8006",
};
