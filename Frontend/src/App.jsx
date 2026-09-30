import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import CoursesPage from './pages/CoursesPage';
import LessonsPage from './pages/LessonsPage';
import SectionPage from './pages/SectionPage';
import TopicPracticePage from './pages/TopicPracticePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

// The graph-heavy pages pull in Cytoscape; load them only when visited.
const SectionMasteryPage = lazy(() => import('./pages/SectionMasteryPage'));
const MasteryPage = lazy(() => import('./pages/MasteryPage'));
const AdminOntologyPage = lazy(() => import('./pages/admin/AdminOntologyPage'));
const AdminStatsPage = lazy(() => import('./pages/admin/AdminStatsPage'));

function RouteFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <span className="h-10 w-10 animate-spin rounded-full border-4 border-atlas-100 border-t-atlas-600" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/courses" element={<CoursesPage />} />
                <Route path="/mastery" element={<MasteryPage />} />
                <Route path="/courses/:courseId" element={<LessonsPage />} />
                <Route path="/courses/:courseId/sections/:sectionId" element={<SectionPage />} />
                <Route path="/courses/:courseId/sections/:sectionId/mastery" element={<SectionMasteryPage />} />
                <Route path="/courses/:courseId/sections/:sectionId/topics/:topicCode/practice" element={<TopicPracticePage />} />
                <Route path="/admin/ontology" element={<AdminOntologyPage />} />
                <Route path="/admin/stats" element={<AdminStatsPage />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  );
}
