import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth, buildApiUrl } from '../context/AuthContext';
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Lock,
  Play,
} from 'lucide-react';

export default function SectionPage() {
  const { courseId, sectionId } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [section, setSection] = useState(null);
  const [sectionState, setSectionState] = useState(null);

  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState('');

  const [startingDiagnostic, setStartingDiagnostic] = useState(false);
  const [startError, setStartError] = useState('');
  const [startedDiagnostic, setStartedDiagnostic] = useState(null);

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [loading, user, navigate]);

  useEffect(() => {
    if (!user) {
      return;
    }

    let ignore = false;

    async function loadData() {
      setPageLoading(true);
      setPageError('');
      setStartedDiagnostic(null);
      setStartError('');

      try {
        const catalogResponse = await fetch(buildApiUrl('/catalog'));
        if (!catalogResponse.ok) {
          throw new Error(`Catalog request failed (${catalogResponse.status})`);
        }
        const catalogPayload = await catalogResponse.json();
        const courses = Array.isArray(catalogPayload?.courses) ? catalogPayload.courses : [];
        const foundCourse = courses.find((item) => item.id === courseId) || null;
        const foundSection = foundCourse?.sections?.find((item) => item.id === sectionId) || null;

        if (!foundCourse || !foundSection) {
          throw new Error('Section not found in the current catalog.');
        }

        let statePayload = null;
        if (foundSection.enabled) {
          const stateResponse = await fetch(
            buildApiUrl(`/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/state`)
          );
          if (!stateResponse.ok) {
            throw new Error(`Section state request failed (${stateResponse.status})`);
          }
          statePayload = await stateResponse.json();
        }

        if (!ignore) {
          setCourse(foundCourse);
          setSection(foundSection);
          setSectionState(statePayload);
        }
      } catch (error) {
        if (!ignore) {
          setPageError(error.message || 'Failed to load section');
          setCourse(null);
          setSection(null);
          setSectionState(null);
        }
      } finally {
        if (!ignore) {
          setPageLoading(false);
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
    };
  }, [courseId, sectionId, user]);

  const sectionTitle = useMemo(() => {
    if (!section) {
      return '';
    }
    return lang === 'bn' && section.title_bn ? section.title_bn : section.title;
  }, [section, lang]);

  async function handleStartDiagnostic() {
    if (!user || !section || startingDiagnostic) {
      return;
    }

    setStartingDiagnostic(true);
    setStartError('');

    try {
      const response = await fetch(buildApiUrl('/diagnostic/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.user_id,
          section_id: section.id,
        }),
      });

      if (!response.ok) {
        let detail = `Diagnostic start failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setStartedDiagnostic(payload);
      setSectionState((prev) => ({
        ...(prev || {}),
        active_diagnostic_session_id: payload.session_id,
        diagnostic_answered_count: 0,
        diagnostic_total_questions: payload.total_questions,
        diagnostic_required: true,
        mastery_locked: true,
      }));
    } catch (error) {
      const isNetworkError = error instanceof TypeError && /fetch/i.test(error.message || '');
      setStartError(isNetworkError ? 'Could not reach backend server. Check API URL and backend status.' : (error.message || 'Failed to start diagnostic'));
    } finally {
      setStartingDiagnostic(false);
    }
  }

  if (pageLoading) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-10 text-center text-gray-600 flex items-center gap-2">
          <Loader2 size={18} className="animate-spin" />
          Loading section details...
        </div>
      </div>
    );
  }

  if (!section || !course) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center px-4">
        <div className="card p-10 max-w-xl text-center">
          <AlertCircle size={42} className="mx-auto text-red-400 mb-3" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Section unavailable</h2>
          <p className="text-gray-600 mb-6">{pageError || 'This section could not be loaded.'}</p>
          <Link to={`/courses/${courseId}`} className="btn-secondary">
            <ArrowLeft size={16} /> Back to sections
          </Link>
        </div>
      </div>
    );
  }

  const topics = Array.isArray(section.topics) ? section.topics : [];
  const enabled = !!section.enabled;
  const masteryLocked = enabled ? !!sectionState?.mastery_locked : true;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <Link to={`/courses/${courseId}`} className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors">
            <ArrowLeft size={16} />
            Back to sections
          </Link>
          <h1 className="font-display text-2xl sm:text-3xl font-bold">{sectionTitle}</h1>
          <p className="text-white/80 mt-2 text-sm">
            {enabled
              ? 'Section is live. Complete diagnostic to unlock mastery visualizations.'
              : 'This section is planned but not enabled yet.'}
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
        <div className="card p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Section Topics</h2>
          {topics.length === 0 ? (
            <p className="text-sm text-gray-500">No topics published yet.</p>
          ) : (
            <div className="grid sm:grid-cols-2 gap-2">
              {topics.map((topic) => {
                const title = lang === 'bn' && topic.title_bn ? topic.title_bn : topic.title;
                return (
                  <div key={topic.id} className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                    {title}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {!enabled && (
          <div className="card p-6 border border-gray-200 bg-gray-50">
            <div className="flex items-start gap-3">
              <Lock size={20} className="text-gray-400 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-700">Section locked</h3>
                <p className="text-sm text-gray-500 mt-1">This section is disabled in catalog metadata right now.</p>
              </div>
            </div>
          </div>
        )}

        {enabled && masteryLocked && (
          <div className="card p-6 border border-amber-200 bg-amber-50">
            <div className="flex items-start gap-3">
              <Lock size={20} className="text-amber-600 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-amber-900">Diagnostic required</h3>
                <p className="text-sm text-amber-800 mt-1">
                  You need to complete 30 diagnostic questions before mastery map/table is unlocked.
                </p>
                <p className="text-xs text-amber-800/90 mt-2">
                  Current progress: {sectionState?.diagnostic_answered_count || 0}/{sectionState?.diagnostic_total_questions || 30}
                </p>
                <button
                  type="button"
                  onClick={handleStartDiagnostic}
                  disabled={startingDiagnostic}
                  className="btn-primary mt-4"
                >
                  {startingDiagnostic ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      Start Diagnostic
                    </>
                  )}
                </button>
              </div>
            </div>

            {startError && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {startError}
              </div>
            )}

            {startedDiagnostic && (
              <div className="mt-4 rounded-xl border border-atlas-200 bg-white px-4 py-3 text-sm text-gray-700">
                <p className="font-semibold text-atlas-700">Diagnostic session created</p>
                <p className="mt-1">Session ID: {startedDiagnostic.session_id}</p>
                <p>First question is now ready. Next feature will render the full one-by-one diagnostic player in the UI.</p>
              </div>
            )}
          </div>
        )}

        {enabled && !masteryLocked && (
          <div className="card p-6 border border-emerald-200 bg-emerald-50">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="text-emerald-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-emerald-900">Mastery unlocked</h3>
                <p className="text-sm text-emerald-800 mt-1">
                  Diagnostic is complete for this section. Mastery map/table integration is next.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
