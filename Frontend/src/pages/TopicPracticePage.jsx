import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth, buildApiUrl } from '../context/AuthContext';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Lock,
  Play,
  Send,
  Sparkles,
} from 'lucide-react';

export default function TopicPracticePage() {
  const { courseId, sectionId, topicCode } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [section, setSection] = useState(null);
  const [topic, setTopic] = useState(null);
  const [sectionState, setSectionState] = useState(null);

  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState('');

  const [startingRun, setStartingRun] = useState(false);
  const [submittingAnswer, setSubmittingAnswer] = useState(false);
  const [loadingNextQuestion, setLoadingNextQuestion] = useState(false);

  const [runError, setRunError] = useState('');
  const [practiceRun, setPracticeRun] = useState(null);
  const [selectedOptionLabel, setSelectedOptionLabel] = useState('');
  const [answerFeedback, setAnswerFeedback] = useState(null);
  const [awaitingNextQuestion, setAwaitingNextQuestion] = useState(false);
  const [showDebugPanel, setShowDebugPanel] = useState(true);

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

    async function loadPage() {
      setPageLoading(true);
      setPageError('');
      setRunError('');
      setPracticeRun(null);
      setSelectedOptionLabel('');
      setAnswerFeedback(null);
      setAwaitingNextQuestion(false);

      try {
        const catalogResponse = await fetch(buildApiUrl('/catalog'));
        if (!catalogResponse.ok) {
          throw new Error(`Catalog request failed (${catalogResponse.status})`);
        }
        const catalogPayload = await catalogResponse.json();
        const courses = Array.isArray(catalogPayload?.courses) ? catalogPayload.courses : [];
        const foundCourse = courses.find((item) => item.id === courseId) || null;
        const foundSection = foundCourse?.sections?.find((item) => item.id === sectionId) || null;

        if (!foundSection) {
          throw new Error('Section not found in catalog.');
        }

        const foundTopic = (foundSection.topics || []).find((item) => item.skill_topic_code === topicCode) || null;
        if (!foundTopic) {
          throw new Error('Topic is not available in this section.');
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
          setSection(foundSection);
          setTopic(foundTopic);
          setSectionState(statePayload);
        }
      } catch (error) {
        if (!ignore) {
          setPageError(error.message || 'Failed to load topic practice page');
          setSection(null);
          setTopic(null);
          setSectionState(null);
        }
      } finally {
        if (!ignore) {
          setPageLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      ignore = true;
    };
  }, [courseId, sectionId, topicCode, user]);

  const topicTitle = useMemo(() => {
    if (!topic) {
      return topicCode;
    }
    return lang === 'bn' && topic.title_bn ? topic.title_bn : topic.title;
  }, [topic, topicCode, lang]);

  function setRunFromPayload(payload) {
    setPracticeRun({
      sessionId: payload.session_id || null,
      topicDisplay: payload.topic_display || topicTitle,
      question: payload.question || null,
      answeredCount: payload.answered_count || 0,
      pendingSkillCount: payload.pending_skill_count ?? 0,
      spilloverActive: !!payload.spillover_active,
      spilloverRemaining: payload.spillover_remaining || 0,
      completed: !!payload.completed,
      completionReason: payload.completion_reason || '',
      debug: payload.debug || null,
    });
    setSelectedOptionLabel('');
    setAnswerFeedback(null);
    setAwaitingNextQuestion(false);
    setRunError('');
  }

  async function handleStartTopicPractice() {
    if (!user || !section || !topic || startingRun) {
      return;
    }

    setStartingRun(true);
    setRunError('');

    try {
      const response = await fetch(buildApiUrl('/topic-practice/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.user_id,
          section_id: section.id,
          topic_code: topic.skill_topic_code,
        }),
      });

      if (!response.ok) {
        let detail = `Topic practice start failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          // Keep status-derived message
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setRunFromPayload(payload);
    } catch (error) {
      const isNetworkError = error instanceof TypeError && /fetch/i.test(error.message || '');
      setRunError(isNetworkError ? 'Could not reach backend server.' : (error.message || 'Failed to start topic practice'));
    } finally {
      setStartingRun(false);
    }
  }

  async function handleSubmitAnswer() {
    if (!practiceRun?.sessionId || !practiceRun?.question || !selectedOptionLabel || submittingAnswer) {
      return;
    }

    setSubmittingAnswer(true);
    setRunError('');

    try {
      const response = await fetch(buildApiUrl(`/topic-practice/${encodeURIComponent(practiceRun.sessionId)}/answer`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_option_label: selectedOptionLabel }),
      });

      if (!response.ok) {
        let detail = `Answer submission failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          // Keep status-derived message
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setAnswerFeedback({
        isCorrect: !!payload.is_correct,
        explanation: payload.selected_option_explanation || '',
        spilloverActivated: payload.spillover_activated || null,
      });

      setPracticeRun((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          answeredCount: payload.answered_count ?? prev.answeredCount,
          pendingSkillCount: payload.pending_skill_count ?? prev.pendingSkillCount,
          spilloverActive: !!payload.spillover_active,
          spilloverRemaining: payload.spillover_remaining || 0,
          completed: !!payload.completed,
          completionReason: payload.completion_reason || prev.completionReason,
          debug: payload.debug || prev.debug,
          question: payload.completed ? null : prev.question,
        };
      });

      setAwaitingNextQuestion(!payload.completed);
    } catch (error) {
      const isNetworkError = error instanceof TypeError && /fetch/i.test(error.message || '');
      setRunError(isNetworkError ? 'Could not reach backend server.' : (error.message || 'Failed to submit answer'));
    } finally {
      setSubmittingAnswer(false);
    }
  }

  async function handleNextQuestion() {
    if (!practiceRun?.sessionId || !awaitingNextQuestion || loadingNextQuestion) {
      return;
    }

    setLoadingNextQuestion(true);
    setRunError('');

    try {
      const response = await fetch(buildApiUrl(`/topic-practice/${encodeURIComponent(practiceRun.sessionId)}/next`));
      if (!response.ok) {
        let detail = `Failed to fetch next question (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          // Keep status-derived message
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setRunFromPayload(payload);
    } catch (error) {
      const isNetworkError = error instanceof TypeError && /fetch/i.test(error.message || '');
      setRunError(isNetworkError ? 'Could not reach backend server.' : (error.message || 'Failed to load next question'));
    } finally {
      setLoadingNextQuestion(false);
    }
  }

  if (pageLoading) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-10 text-center text-gray-600 flex items-center gap-2">
          <Loader2 size={18} className="animate-spin" />
          Loading topic practice...
        </div>
      </div>
    );
  }

  if (!section || !topic) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center px-4">
        <div className="card p-10 max-w-xl text-center">
          <AlertCircle size={42} className="mx-auto text-red-400 mb-3" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Topic unavailable</h2>
          <p className="text-gray-600 mb-6">{pageError || 'This topic could not be loaded.'}</p>
          <Link to={`/courses/${courseId}/sections/${sectionId}`} className="btn-secondary">
            <ArrowLeft size={16} /> Back to section
          </Link>
        </div>
      </div>
    );
  }

  const masteryLocked = !sectionState?.diagnostic_completed;
  const question = practiceRun?.question;
  const options = Array.isArray(question?.options) ? question.options : [];
  const currentQuestionNumber = practiceRun ? practiceRun.answeredCount + 1 : 0;
  const debug = practiceRun?.debug || null;
  const rollingAccuracy =
    typeof debug?.rolling_accuracy_last_8 === 'number'
      ? `${Math.round(debug.rolling_accuracy_last_8 * 100)}%`
      : 'N/A';
  const missingPrereqCountsText =
    debug?.missing_prereq_counts_last_5 && Object.keys(debug.missing_prereq_counts_last_5).length > 0
      ? Object.entries(debug.missing_prereq_counts_last_5)
          .map(([skillId, count]) => `${skillId}: ${count}`)
          .join(', ')
      : 'None';

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <Link to={`/courses/${courseId}/sections/${sectionId}`} className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors">
            <ArrowLeft size={16} />
            Back to section
          </Link>
          <h1 className="font-display text-2xl sm:text-3xl font-bold">{topicTitle}</h1>
          <p className="text-white/80 mt-2 text-sm">Topic practice uses DAG traversal with conditional prerequisite spillover.</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
        {masteryLocked ? (
          <div className="card p-6 border border-amber-200 bg-amber-50">
            <div className="flex items-start gap-3">
              <Lock size={20} className="text-amber-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-900">Topic practice locked</h3>
                <p className="text-sm text-amber-800 mt-1">Complete the section diagnostic first to unlock topic tests.</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="card p-6 border border-atlas-200 bg-white">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <span className="inline-flex items-center gap-1 rounded-full bg-atlas-100 px-3 py-1 text-xs font-semibold text-atlas-700">
                <BookOpen size={14} />
                {topicTitle}
              </span>
              {practiceRun && (
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">
                  Pending skills: {practiceRun.pendingSkillCount}
                </span>
              )}
              {practiceRun?.spilloverActive && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                  <Sparkles size={14} />
                  Spillover active ({practiceRun.spilloverRemaining} left)
                </span>
              )}
            </div>

            {!practiceRun?.question && !awaitingNextQuestion && (
              <button type="button" onClick={handleStartTopicPractice} className="btn-primary" disabled={startingRun}>
                {startingRun ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    {practiceRun?.completed ? 'Start New Topic Run' : 'Start Topic Practice'}
                  </>
                )}
              </button>
            )}

            {question && (
              <div className="mt-5 rounded-xl border border-atlas-200 bg-white p-4 sm:p-5">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <p className="text-xs font-semibold tracking-wide uppercase text-atlas-700">
                    Question {currentQuestionNumber}
                  </p>
                  <p className="text-xs text-gray-500">Session: {practiceRun?.sessionId}</p>
                </div>

                <div className="mb-4 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-xs text-gray-600">
                  <span className="font-semibold text-gray-700">Mode:</span> {question.delivery_mode || 'topic'} | <span className="font-semibold text-gray-700">Skill:</span> {question.skill_id} | <span className="font-semibold text-gray-700">Bloom:</span> {question.bloom_level}
                </div>

                <h4 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">{question.question_stem}</h4>

                <div className="space-y-2">
                  {options.map((option) => {
                    const selected = selectedOptionLabel === option.label;
                    return (
                      <button
                        key={option.label}
                        type="button"
                        disabled={!!answerFeedback}
                        onClick={() => setSelectedOptionLabel(option.label)}
                        className={`w-full text-left rounded-xl border px-3.5 py-3 transition-all ${
                          selected
                            ? 'border-atlas-500 bg-atlas-50 text-atlas-900'
                            : 'border-gray-200 bg-white hover:border-atlas-300'
                        } ${answerFeedback ? 'cursor-default' : ''}`}
                      >
                        <span className="font-semibold mr-2">{option.label}.</span>
                        <span>{option.text}</span>
                      </button>
                    );
                  })}
                </div>

                {!answerFeedback && (
                  <button type="button" onClick={handleSubmitAnswer} disabled={!selectedOptionLabel || submittingAnswer} className="btn-primary mt-4">
                    {submittingAnswer ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Send size={16} />
                        Submit Answer
                      </>
                    )}
                  </button>
                )}

                {answerFeedback && (
                  <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${answerFeedback.isCorrect ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-red-200 bg-red-50 text-red-900'}`}>
                    <p className="font-semibold">{answerFeedback.isCorrect ? 'Correct answer' : 'Incorrect answer'}</p>
                    {answerFeedback.explanation && <p className="mt-1">{answerFeedback.explanation}</p>}
                    {answerFeedback.spilloverActivated && (
                      <p className="mt-2 text-xs">
                        Spillover activated for {answerFeedback.spilloverActivated.skill_id} ({answerFeedback.spilloverActivated.injected_question_count} questions).
                      </p>
                    )}
                  </div>
                )}

                {awaitingNextQuestion && (
                  <button type="button" onClick={handleNextQuestion} className="btn-primary mt-4" disabled={loadingNextQuestion}>
                    {loadingNextQuestion ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Loading Next Question...
                      </>
                    ) : (
                      <>
                        Next Question
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>
                )}
              </div>
            )}

            {practiceRun?.completed && (
              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:p-5 text-emerald-900">
                <p className="font-semibold text-base flex items-center gap-2">
                  <CheckCircle2 size={18} />
                  Topic practice complete
                </p>
                <p className="text-sm mt-1">
                  {practiceRun.completionReason || 'Topic run completed.'}
                </p>
              </div>
            )}

            {debug && (
              <div className="mt-5 rounded-xl border border-gray-200 bg-gray-50 p-4 sm:p-5 text-gray-800">
                <button
                  type="button"
                  onClick={() => setShowDebugPanel((prev) => !prev)}
                  className="w-full flex items-center justify-between text-left"
                >
                  <span className="font-semibold text-sm uppercase tracking-wide text-gray-700">Policy Debug Panel</span>
                  {showDebugPanel ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {showDebugPanel && (
                  <div className="mt-3 grid sm:grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                      <p className="font-semibold text-gray-700">Traversal pointer</p>
                      <p className="mt-1">{(debug.traversal_index ?? 0) + 1} / {debug.traversal_length ?? 0}</p>
                      <p className="mt-1">Next skill: {debug.next_traversal_skill_id || 'N/A'}</p>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                      <p className="font-semibold text-gray-700">Current and last mode</p>
                      <p className="mt-1">Current mode: {debug.current_question_mode || 'idle'}</p>
                      <p className="mt-1">Last delivery mode: {debug.last_delivery_mode || 'N/A'}</p>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                      <p className="font-semibold text-gray-700">Rolling accuracy (last 8)</p>
                      <p className="mt-1">Accuracy: {rollingAccuracy}</p>
                      <p className="mt-1">Window size: {debug.rolling_accuracy_window_size ?? 0}</p>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                      <p className="font-semibold text-gray-700">Repeated missing prerequisites (last 5)</p>
                      <p className="mt-1">Window size: {debug.missing_prereq_window_size ?? 0}</p>
                      <p className="mt-1">{missingPrereqCountsText}</p>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 sm:col-span-2">
                      <p className="font-semibold text-gray-700">Last spillover trigger</p>
                      <p className="mt-1">Reason: {debug.last_spillover_reason || 'Not triggered yet'}</p>
                      <p className="mt-1">Skill: {debug.last_spillover_skill_id || 'N/A'}</p>
                      <p className="mt-1">Triggered at answered count: {debug.last_spillover_trigger_answer_count ?? 'N/A'}</p>
                    </div>

                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 sm:col-span-2">
                      <p className="font-semibold text-gray-700">Exhausted topic skills</p>
                      <p className="mt-1">Count: {debug.exhausted_topic_skill_count ?? 0}</p>
                      <p className="mt-1 break-all">
                        {Array.isArray(debug.exhausted_topic_skill_ids) && debug.exhausted_topic_skill_ids.length > 0
                          ? debug.exhausted_topic_skill_ids.join(', ')
                          : 'None'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {runError && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {runError}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
