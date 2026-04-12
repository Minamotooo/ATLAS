import { useEffect, useMemo, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth, buildApiUrl } from '../context/AuthContext';
import {
  ArrowLeft,
  BookOpen,
  Lock,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Play,
} from 'lucide-react';

export default function LessonsPage() {
  const { courseId } = useParams();
  const { t, lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [courseLoading, setCourseLoading] = useState(true);
  const [courseError, setCourseError] = useState('');

  const [sectionStates, setSectionStates] = useState({});
  const [statesLoading, setStatesLoading] = useState(false);
  const [statesError, setStatesError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [loading, user, navigate]);

  useEffect(() => {
    let ignore = false;

    async function loadCourse() {
      setCourseLoading(true);
      setCourseError('');

      try {
        const response = await fetch(buildApiUrl('/catalog'));
        if (!response.ok) {
          throw new Error(`Catalog request failed (${response.status})`);
        }

        const payload = await response.json();
        const courses = Array.isArray(payload?.courses) ? payload.courses : [];
        const foundCourse = courses.find((item) => item.id === courseId) || null;

        if (!ignore) {
          setCourse(foundCourse);
          if (!foundCourse) {
            setCourseError('Course not found in current catalog.');
          }
        }
      } catch (error) {
        if (!ignore) {
          setCourseError(error.message || 'Failed to load course');
          setCourse(null);
        }
      } finally {
        if (!ignore) {
          setCourseLoading(false);
        }
      }
    }

    loadCourse();

    return () => {
      ignore = true;
    };
  }, [courseId]);

  useEffect(() => {
    if (!course || !user) {
      setSectionStates({});
      setStatesLoading(false);
      setStatesError('');
      return;
    }

    let ignore = false;

    async function loadSectionStates() {
      const enabledSections = (course.sections || []).filter((section) => section.enabled);
      if (enabledSections.length === 0) {
        setSectionStates({});
        setStatesLoading(false);
        setStatesError('');
        return;
      }

      setStatesLoading(true);
      setStatesError('');

      const entries = await Promise.all(
        enabledSections.map(async (section) => {
          try {
            const response = await fetch(
              buildApiUrl(`/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(section.id)}/state`)
            );
            if (!response.ok) {
              throw new Error(`State request failed (${response.status})`);
            }
            const payload = await response.json();
            return [section.id, payload];
          } catch (error) {
            return [section.id, { __error: error.message || 'Failed to load section state' }];
          }
        })
      );

      if (!ignore) {
        const nextStates = Object.fromEntries(entries);
        setSectionStates(nextStates);

        const hasAnyError = Object.values(nextStates).some((state) => state.__error);
        if (hasAnyError) {
          setStatesError('Some section states could not be loaded.');
        }

        setStatesLoading(false);
      }
    }

    loadSectionStates();

    return () => {
      ignore = true;
    };
  }, [course, user]);

  const sections = course?.sections || [];

  const summary = useMemo(() => {
    const enabledSections = sections.filter((section) => section.enabled);
    const completedCount = enabledSections.filter((section) => {
      const state = sectionStates[section.id];
      return state && !state.__error && state.diagnostic_completed;
    }).length;

    const progress = enabledSections.length > 0
      ? Math.round((completedCount / enabledSections.length) * 100)
      : 0;

    const nextSection = enabledSections.find((section) => {
      const state = sectionStates[section.id];
      if (!state || state.__error) {
        return true;
      }
      return state.mastery_locked;
    }) || enabledSections[0] || null;

    return {
      enabledCount: enabledSections.length,
      completedCount,
      progress,
      nextSection,
    };
  }, [sections, sectionStates]);

  if (courseLoading) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-10 text-center text-gray-600 flex items-center gap-2">
          <Loader2 size={18} className="animate-spin" />
          Loading course sections...
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-12 text-center max-w-lg">
          <BookOpen size={48} className="mx-auto text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Course unavailable</h2>
          <p className="text-gray-500 mb-6">{courseError || 'This course could not be found.'}</p>
          <Link to="/courses" className="btn-secondary">
            <ArrowLeft size={16} /> {t('lessons.backToCourses')}
          </Link>
        </div>
      </div>
    );
  }

  const courseName = lang === 'bn' && course.title_bn ? course.title_bn : course.title;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-black/10" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <Link to="/courses" className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors">
            <ArrowLeft size={16} />
            {t('lessons.backToCourses')}
          </Link>

          <div className="flex items-center gap-4 mb-5">
            <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center text-2xl">∑</div>
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold">{courseName}</h1>
              <p className="text-white/80 text-sm mt-1">Section-based progression with diagnostic gating</p>
            </div>
          </div>

          <div className="max-w-md">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-white/80">Section Progress</span>
              <span className="font-semibold">{summary.progress}%</span>
            </div>
            <div className="w-full h-3 bg-white/20 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full transition-all duration-700" style={{ width: `${summary.progress}%` }} />
            </div>
          </div>

          <div className="flex gap-4 mt-6">
            <div className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-2.5 border border-white/10">
              <div className="text-xs text-white/70">Enabled sections</div>
              <div className="text-lg font-bold">{summary.enabledCount}</div>
            </div>
            <div className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-2.5 border border-white/10">
              <div className="text-xs text-white/70">Diagnostics completed</div>
              <div className="text-lg font-bold">{summary.completedCount}/{summary.enabledCount}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {statesError && (
          <div className="card p-4 mb-5 border border-amber-200 bg-amber-50 text-amber-800 flex gap-2 items-start">
            <AlertCircle size={18} className="mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Section status partially available</p>
              <p className="text-sm opacity-90">{statesError}</p>
            </div>
          </div>
        )}

        {summary.nextSection && (
          <div className="card mb-6 overflow-hidden">
            <div className="bg-gradient-to-r from-atlas-50 to-atlas-100 p-6 border-b border-atlas-200">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <span className="text-xs font-semibold text-atlas-700 uppercase tracking-wider">Recommended next section</span>
                  <h3 className="font-display text-lg font-bold text-gray-900 mt-1">
                    {lang === 'bn' && summary.nextSection.title_bn ? summary.nextSection.title_bn : summary.nextSection.title}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Start this section to unlock mastery map and table for its skills.
                  </p>
                </div>
                <Link to={`/courses/${courseId}/sections/${summary.nextSection.id}`} className="btn-primary">
                  Open Section
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          </div>
        )}

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.map((section) => {
            const state = sectionStates[section.id];
            const sectionName = lang === 'bn' && section.title_bn ? section.title_bn : section.title;
            const topicCount = Array.isArray(section.topics) ? section.topics.length : 0;

            let badgeLabel = section.enabled ? 'Available' : 'Locked';
            let badgeClass = section.enabled ? 'bg-atlas-100 text-atlas-700' : 'bg-gray-100 text-gray-500';
            let statusIcon = section.enabled ? <Play size={16} /> : <Lock size={16} />;

            if (section.enabled && state && !state.__error && !state.mastery_locked) {
              badgeLabel = 'Unlocked';
              badgeClass = 'bg-emerald-100 text-emerald-700';
              statusIcon = <CheckCircle2 size={16} />;
            } else if (section.enabled && state && !state.__error && state.mastery_locked) {
              badgeLabel = 'Diagnostic Required';
              badgeClass = 'bg-amber-100 text-amber-700';
              statusIcon = <Lock size={16} />;
            }

            return (
              <div
                key={section.id}
                className={`card border ${section.enabled ? 'border-atlas-100' : 'border-gray-200 bg-gray-50/70 opacity-80'} flex flex-col`}
              >
                <div className="p-5 flex flex-col flex-1">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${badgeClass}`}>
                      {statusIcon}
                      {badgeLabel}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">{section.id}</span>
                  </div>

                  <h3 className={`font-semibold mb-1 ${section.enabled ? 'text-gray-900' : 'text-gray-500'}`}>{sectionName}</h3>
                  <p className={`text-sm mb-3 ${section.enabled ? 'text-gray-600' : 'text-gray-400'}`}>
                    {topicCount > 0 ? `${topicCount} tracked topics in this section.` : 'Content is not published yet.'}
                  </p>

                  {section.enabled && !state?.__error && (
                    <div className="text-xs text-gray-500 bg-gray-50 rounded-lg p-3 mb-4">
                      Diagnostic progress: {state?.diagnostic_answered_count || 0}/{state?.diagnostic_total_questions || 30}
                    </div>
                  )}

                  {section.enabled ? (
                    <Link to={`/courses/${courseId}/sections/${section.id}`} className="mt-auto inline-flex items-center justify-center gap-1.5 text-sm font-semibold py-2.5 rounded-xl bg-atlas-600 text-white hover:bg-atlas-700 transition-all">
                      Open Section
                      <ArrowRight size={14} />
                    </Link>
                  ) : (
                    <span className="mt-auto inline-flex items-center justify-center gap-1.5 text-sm font-semibold py-2.5 rounded-xl bg-gray-100 text-gray-500">
                      Coming Soon
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {statesLoading && (
          <div className="text-sm text-gray-500 mt-5 flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            Updating section state...
          </div>
        )}
      </div>
    </div>
  );
}
