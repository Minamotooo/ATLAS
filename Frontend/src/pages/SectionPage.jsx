import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { useAuth, buildApiUrl } from "../context/AuthContext";
import MathText from "../components/MathText";
import {
  ArrowLeft,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Lock,
  Play,
  RotateCcw,
  Send,
} from "lucide-react";

export default function SectionPage() {
  const { courseId, sectionId } = useParams();
  const { lang } = useLanguage();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [section, setSection] = useState(null);
  const [sectionState, setSectionState] = useState(null);

  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [loadingSectionState, setLoadingSectionState] = useState(false);
  const [startingDiagnostic, setStartingDiagnostic] = useState(false);
  const [retakingDiagnostic, setRetakingDiagnostic] = useState(false);
  const [submittingAnswer, setSubmittingAnswer] = useState(false);
  const [loadingNextQuestion, setLoadingNextQuestion] = useState(false);
  const [startError, setStartError] = useState("");
  const [answerError, setAnswerError] = useState("");
  const [retakeError, setRetakeError] = useState("");

  const [diagnosticRun, setDiagnosticRun] = useState(null);
  const [selectedOptionLabel, setSelectedOptionLabel] = useState("");
  const [answerFeedback, setAnswerFeedback] = useState(null);
  const [awaitingNextQuestion, setAwaitingNextQuestion] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate("/login");
    }
  }, [loading, user, navigate]);

  useEffect(() => {
    if (!user) {
      return;
    }

    let ignore = false;

    async function loadData() {
      setPageLoading(true);
      setPageError("");
      setDiagnosticRun(null);
      setSelectedOptionLabel("");
      setAnswerFeedback(null);
      setAwaitingNextQuestion(false);
      setStartError("");
      setAnswerError("");
      setRetakeError("");

      try {
        const catalogResponse = await fetch(buildApiUrl("/catalog"));
        if (!catalogResponse.ok) {
          throw new Error(`Catalog request failed (${catalogResponse.status})`);
        }
        const catalogPayload = await catalogResponse.json();
        const courses = Array.isArray(catalogPayload?.courses)
          ? catalogPayload.courses
          : [];
        const foundCourse =
          courses.find((item) => item.id === courseId) || null;
        const foundSection =
          foundCourse?.sections?.find((item) => item.id === sectionId) || null;

        if (!foundCourse || !foundSection) {
          throw new Error("Section not found in the current catalog.");
        }

        let statePayload = null;
        if (foundSection.enabled) {
          const stateResponse = await fetch(
            buildApiUrl(
              `/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/state`,
            ),
          );
          if (!stateResponse.ok) {
            throw new Error(
              `Section state request failed (${stateResponse.status})`,
            );
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
          setPageError(error.message || "Failed to load section");
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

  async function refreshSectionState() {
    if (!user || !section?.enabled) {
      return;
    }

    setLoadingSectionState(true);
    try {
      const response = await fetch(
        buildApiUrl(
          `/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(sectionId)}/state`,
        ),
      );
      if (!response.ok) {
        throw new Error(`Section state request failed (${response.status})`);
      }
      const payload = await response.json();
      setSectionState(payload);
    } catch (error) {
      setPageError(error.message || "Failed to refresh section state");
    } finally {
      setLoadingSectionState(false);
    }
  }

  const sectionTitle = useMemo(() => {
    if (!section) {
      return "";
    }
    return lang === "bn" && section.title_bn ? section.title_bn : section.title;
  }, [section, lang]);

  function setRunFromStartPayload(payload) {
    setDiagnosticRun({
      sessionId: payload.session_id,
      totalQuestions: payload.total_questions,
      answeredCount: 0,
      question: payload.question,
      completed: false,
    });
    setSelectedOptionLabel("");
    setAnswerFeedback(null);
    setAwaitingNextQuestion(false);
    setStartError("");
    setAnswerError("");
  }

  async function handleStartDiagnostic() {
    if (!user || !section || startingDiagnostic) {
      return;
    }

    setStartingDiagnostic(true);
    setStartError("");
    setAnswerError("");
    setRetakeError("");

    try {
      const response = await fetch(buildApiUrl("/diagnostic/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          section_id: section.id,
        }),
      });

      if (!response.ok) {
        let detail = `Diagnostic start failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (
            typeof errorPayload?.detail === "string" &&
            errorPayload.detail.trim()
          ) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setRunFromStartPayload(payload);
      setSectionState((prev) => ({
        ...(prev || {}),
        active_diagnostic_session_id: payload.session_id,
        diagnostic_answered_count: 0,
        diagnostic_total_questions: payload.total_questions,
        diagnostic_required: true,
        mastery_locked: true,
      }));
    } catch (error) {
      const isNetworkError =
        error instanceof TypeError && /fetch/i.test(error.message || "");
      setStartError(
        isNetworkError
          ? "Could not reach backend server. Check API URL and backend status."
          : error.message || "Failed to start diagnostic",
      );
    } finally {
      setStartingDiagnostic(false);
    }
  }

  async function handleRetakeDiagnostic() {
    if (!user || !section || retakingDiagnostic || startingDiagnostic) {
      return;
    }

    const confirmed = window.confirm(
      "This will reset your mastery data for this section and restart diagnostic from question 1. Continue?",
    );
    if (!confirmed) {
      return;
    }

    setRetakingDiagnostic(true);
    setRetakeError("");
    setStartError("");
    setAnswerError("");

    try {
      const response = await fetch(
        buildApiUrl(
          `/users/${encodeURIComponent(user.user_id)}/sections/${encodeURIComponent(section.id)}/diagnostic/retake`,
        ),
        { method: "POST" },
      );

      if (!response.ok) {
        let detail = `Retake reset failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (
            typeof errorPayload?.detail === "string" &&
            errorPayload.detail.trim()
          ) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      if (payload?.state) {
        setSectionState(payload.state);
      }

      setDiagnosticRun(null);
      setSelectedOptionLabel("");
      setAnswerFeedback(null);
      setAwaitingNextQuestion(false);

      await handleStartDiagnostic();
    } catch (error) {
      const isNetworkError =
        error instanceof TypeError && /fetch/i.test(error.message || "");
      setRetakeError(
        isNetworkError
          ? "Could not reach backend server. Check API URL and backend status."
          : error.message || "Failed to reset and retake diagnostic",
      );
    } finally {
      setRetakingDiagnostic(false);
    }
  }

  async function handleSubmitDiagnosticAnswer() {
    if (
      !diagnosticRun?.sessionId ||
      !diagnosticRun?.question ||
      !selectedOptionLabel ||
      submittingAnswer
    ) {
      return;
    }

    setSubmittingAnswer(true);
    setAnswerError("");

    try {
      const response = await fetch(
        buildApiUrl(
          `/diagnostic/${encodeURIComponent(diagnosticRun.sessionId)}/answer`,
        ),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_option_label: selectedOptionLabel,
          }),
        },
      );

      if (!response.ok) {
        let detail = `Answer submission failed (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (
            typeof errorPayload?.detail === "string" &&
            errorPayload.detail.trim()
          ) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      setAnswerFeedback({
        isCorrect: !!payload.is_correct,
        explanation: payload.selected_option_explanation || "",
        masteryNotifications: Array.isArray(payload.mastery_notifications)
          ? payload.mastery_notifications
          : [],
        answeredCount: payload.answered_count,
      });

      setDiagnosticRun((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          answeredCount: payload.completed
            ? (payload.answered_count ?? prev.answeredCount)
            : prev.answeredCount,
          completed: !!payload.completed,
          question: payload.completed ? null : prev.question,
        };
      });

      if (payload.completed) {
        setAwaitingNextQuestion(false);
        setSectionState((prev) => ({
          ...(prev || {}),
          mastery_locked: false,
          diagnostic_completed: true,
          diagnostic_answered_count: payload.total_questions,
          active_diagnostic_session_id: null,
        }));
      } else {
        setAwaitingNextQuestion(true);
      }
    } catch (error) {
      const isNetworkError =
        error instanceof TypeError && /fetch/i.test(error.message || "");
      setAnswerError(
        isNetworkError
          ? "Could not reach backend server. Check API URL and backend status."
          : error.message || "Failed to submit answer",
      );
    } finally {
      setSubmittingAnswer(false);
    }
  }

  async function handleNextQuestion() {
    if (
      !diagnosticRun?.sessionId ||
      !awaitingNextQuestion ||
      loadingNextQuestion
    ) {
      return;
    }

    setLoadingNextQuestion(true);
    setAnswerError("");

    try {
      const response = await fetch(
        buildApiUrl(
          `/diagnostic/${encodeURIComponent(diagnosticRun.sessionId)}/next`,
        ),
      );
      if (!response.ok) {
        let detail = `Failed to fetch next question (${response.status})`;
        try {
          const errorPayload = await response.json();
          if (
            typeof errorPayload?.detail === "string" &&
            errorPayload.detail.trim()
          ) {
            detail = errorPayload.detail;
          }
        } catch {
          // Ignore parse failures and keep HTTP status-based message.
        }
        throw new Error(detail);
      }

      const payload = await response.json();
      if (payload.completed) {
        setDiagnosticRun((prev) => {
          if (!prev) {
            return prev;
          }
          return {
            ...prev,
            completed: true,
            question: null,
            answeredCount: payload.answered_count ?? prev.answeredCount,
          };
        });
        setSectionState((prev) => ({
          ...(prev || {}),
          mastery_locked: false,
          diagnostic_completed: true,
          diagnostic_answered_count:
            payload.total_questions ||
            sectionState?.diagnostic_total_questions ||
            30,
          active_diagnostic_session_id: null,
        }));
      } else {
        setDiagnosticRun((prev) => {
          if (!prev) {
            return prev;
          }
          return {
            ...prev,
            question: payload.question,
            answeredCount: payload.answered_count ?? prev.answeredCount,
          };
        });
      }

      setSelectedOptionLabel("");
      setAnswerFeedback(null);
      setAwaitingNextQuestion(false);
      setAnswerError("");
    } catch (error) {
      const isNetworkError =
        error instanceof TypeError && /fetch/i.test(error.message || "");
      setAnswerError(
        isNetworkError
          ? "Could not reach backend server. Check API URL and backend status."
          : error.message || "Failed to load next question",
      );
    } finally {
      setLoadingNextQuestion(false);
    }
  }

  function handleCloseCompletedDiagnostic() {
    setDiagnosticRun(null);
    setSelectedOptionLabel("");
    setAnswerFeedback(null);
    setAwaitingNextQuestion(false);
    setAnswerError("");
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
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Section unavailable
          </h2>
          <p className="text-gray-600 mb-6">
            {pageError || "This section could not be loaded."}
          </p>
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
  const showDiagnosticPanel =
    enabled &&
    (masteryLocked ||
      !!diagnosticRun?.question ||
      !!diagnosticRun?.completed ||
      !!sectionState?.active_diagnostic_session_id);
  const question = diagnosticRun?.question;
  const options = Array.isArray(question?.options) ? question.options : [];
  const diagnosticTotalQuestions =
    sectionState?.diagnostic_total_questions ||
    diagnosticRun?.totalQuestions ||
    30;
  const currentQuestionNumber = diagnosticRun
    ? Math.min(diagnosticRun.answeredCount + 1, diagnosticRun.totalQuestions)
    : 0;

  return (
    <div className="min-h-screen bg-atlas-50/50">
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <Link
            to={`/courses/${courseId}`}
            className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft size={16} />
            Back to sections
          </Link>
          <h1 className="font-display text-2xl sm:text-3xl font-bold">
            {sectionTitle}
          </h1>
          <p className="text-white/80 mt-2 text-sm">
            {enabled
              ? "Section is live. Complete diagnostic to unlock mastery visualizations."
              : "This section is planned but not enabled yet."}
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
                const title =
                  lang === "bn" && topic.title_bn
                    ? topic.title_bn
                    : topic.title;
                return (
                  <div
                    key={topic.id}
                    className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 flex items-center justify-between gap-3"
                  >
                    <span>{title}</span>
                    {enabled && !masteryLocked && topic.skill_topic_code ? (
                      <Link
                        to={`/courses/${courseId}/sections/${sectionId}/topics/${encodeURIComponent(topic.skill_topic_code)}/practice`}
                        className="btn-secondary whitespace-nowrap"
                      >
                        Practice Topic
                      </Link>
                    ) : (
                      <span className="text-xs text-gray-500 whitespace-nowrap">
                        Unlock after diagnostic
                      </span>
                    )}
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
                <p className="text-sm text-gray-500 mt-1">
                  This section is disabled in catalog metadata right now.
                </p>
              </div>
            </div>
          </div>
        )}

        {showDiagnosticPanel && (
          <div className="card p-6 border border-amber-200 bg-amber-50">
            <div className="flex items-start gap-3">
              <Lock size={20} className="text-amber-600 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-amber-900">
                  Diagnostic required
                </h3>
                <p className="text-sm text-amber-800 mt-1">
                  You need to complete {diagnosticTotalQuestions} diagnostic
                  questions before mastery map/table is unlocked.
                </p>
                {!diagnosticRun?.question &&
                  !diagnosticRun?.completed &&
                  masteryLocked && (
                    <div className="flex flex-wrap gap-3 mt-4">
                      <button
                        type="button"
                        onClick={handleStartDiagnostic}
                        disabled={startingDiagnostic}
                        className="btn-primary"
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

                      {sectionState?.active_diagnostic_session_id && (
                        <button
                          type="button"
                          onClick={handleStartDiagnostic}
                          disabled={startingDiagnostic}
                          className="btn-secondary"
                        >
                          <RotateCcw size={16} />
                          Start Fresh Diagnostic
                        </button>
                      )}
                    </div>
                  )}
              </div>
            </div>

            {startError && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {startError}
              </div>
            )}

            {answerError && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {answerError}
              </div>
            )}

            {diagnosticRun?.question && (
              <div className="mt-5 rounded-xl border border-atlas-200 bg-white p-4 sm:p-5">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <p className="text-xs font-semibold tracking-wide uppercase text-atlas-700">
                    Question {currentQuestionNumber} of{" "}
                    {diagnosticRun.totalQuestions}
                  </p>
                  <p className="text-xs text-gray-500">
                    Session: {diagnosticRun.sessionId}
                  </p>
                </div>

                <div className="mb-4 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-xs text-gray-600">
                  <span className="font-semibold text-gray-700">Skill:</span>{" "}
                  {question.skill_id} |{" "}
                  <span className="font-semibold text-gray-700">Bloom:</span>{" "}
                  {question.bloom_level} |{" "}
                  <span className="font-semibold text-gray-700">Topic:</span>{" "}
                  {question.topic}
                </div>

                <h4 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">
                  <MathText text={question.question_stem} />
                </h4>

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
                            ? "border-atlas-500 bg-atlas-50 text-atlas-900"
                            : "border-gray-200 bg-white hover:border-atlas-300"
                        } ${answerFeedback ? "cursor-default" : ""}`}
                      >
                        <span className="font-semibold mr-2">
                          {option.label}.
                        </span>
                        <MathText text={option.text} />
                      </button>
                    );
                  })}
                </div>

                {!answerFeedback && (
                  <button
                    type="button"
                    onClick={handleSubmitDiagnosticAnswer}
                    disabled={!selectedOptionLabel || submittingAnswer}
                    className="btn-primary mt-4"
                  >
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
                  <div
                    className={`mt-4 rounded-xl border px-4 py-3 text-sm ${answerFeedback.isCorrect ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-red-200 bg-red-50 text-red-900"}`}
                  >
                    <p className="font-semibold">
                      {answerFeedback.isCorrect
                        ? "Correct answer"
                        : "Incorrect answer"}
                    </p>
                    {answerFeedback.explanation && (
                      <p className="mt-1">
                        <MathText text={answerFeedback.explanation} />
                      </p>
                    )}
                    {answerFeedback.masteryNotifications.length > 0 && (
                      <p className="mt-2 text-xs">
                        Mastery threshold crossed:{" "}
                        {answerFeedback.masteryNotifications.join(", ")}
                      </p>
                    )}
                  </div>
                )}

                {awaitingNextQuestion && (
                  <button
                    type="button"
                    onClick={handleNextQuestion}
                    className="btn-primary mt-4"
                    disabled={loadingNextQuestion}
                  >
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

            {diagnosticRun?.completed && (
              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:p-5 text-emerald-900">
                <p className="font-semibold text-base">Diagnostic complete</p>
                <p className="text-sm mt-1">
                  You finished {diagnosticRun.answeredCount}/
                  {diagnosticRun.totalQuestions} questions. Mastery views should
                  now unlock.
                </p>
                <div className="flex flex-wrap gap-3 mt-4">
                  <button
                    type="button"
                    onClick={refreshSectionState}
                    className="btn-primary"
                    disabled={loadingSectionState}
                  >
                    {loadingSectionState ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Refreshing...
                      </>
                    ) : (
                      "Refresh Section State"
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseCompletedDiagnostic}
                    className="btn-secondary"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {sectionState?.active_diagnostic_session_id && !diagnosticRun && (
              <div className="mt-4 rounded-xl border border-atlas-200 bg-white px-4 py-3 text-sm text-gray-700">
                <p className="font-semibold text-atlas-700">
                  Active diagnostic session detected
                </p>
                <p className="mt-1">
                  Session ID: {sectionState.active_diagnostic_session_id}
                </p>
                <p>
                  Click Start Fresh Diagnostic to continue from a new one-by-one
                  run in this browser session.
                </p>
              </div>
            )}
          </div>
        )}

        {enabled && !masteryLocked && (
          <div className="card p-6 border border-emerald-200 bg-emerald-50">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="text-emerald-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-emerald-900">
                  Mastery unlocked
                </h3>
                <p className="text-sm text-emerald-800 mt-1">
                  Diagnostic is complete for this section. You can now open
                  mastery table and dependency map.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    to={`/courses/${courseId}/sections/${sectionId}/mastery`}
                    className="btn-primary inline-flex"
                  >
                    Open Mastery View
                    <ArrowRight size={16} />
                  </Link>
                  <button
                    type="button"
                    onClick={handleRetakeDiagnostic}
                    disabled={retakingDiagnostic || startingDiagnostic}
                    className="btn-secondary"
                  >
                    {retakingDiagnostic ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Resetting...
                      </>
                    ) : (
                      <>
                        <RotateCcw size={16} />
                        Retake Diagnostic (Reset Progress)
                      </>
                    )}
                  </button>
                </div>
                {retakeError && (
                  <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {retakeError}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
