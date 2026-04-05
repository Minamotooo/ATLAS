import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import CoursesPage from './pages/CoursesPage';
import LessonsPage from './pages/LessonsPage';
import SectionPage from './pages/SectionPage';
import SectionMasteryPage from './pages/SectionMasteryPage';
import TopicPracticePage from './pages/TopicPracticePage';
import PracticePage from './pages/PracticePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/courses" element={<CoursesPage />} />
              <Route path="/courses/:courseId" element={<LessonsPage />} />
              <Route path="/courses/:courseId/sections/:sectionId" element={<SectionPage />} />
              <Route path="/courses/:courseId/sections/:sectionId/mastery" element={<SectionMasteryPage />} />
              <Route path="/courses/:courseId/sections/:sectionId/topics/:topicCode/practice" element={<TopicPracticePage />} />
              <Route path="/courses/:courseId/lessons/:lessonId/practice" element={<PracticePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  );
}
