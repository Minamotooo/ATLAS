import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { questionData } from '../data/courseData';
import {
  ArrowLeft, Lightbulb, Lock, ChevronDown, ChevronUp,
  CheckCircle2, XCircle, Send, Sparkles, HelpCircle,
  Brain, BookOpen, ArrowRight, RotateCcw, Zap, Target
} from 'lucide-react';

// ── BKT Parameters ──────────────────────────────────────
const BKT = {
  pLearn: 0.3,
  pGuess: 0.2,
  pSlip: 0.1,
  masteryThreshold: 0.85,
};

function bktUpdate(pMastery, isCorrect) {
  const pCorrectMastered = 1 - BKT.pSlip;
  const pCorrectNotMastered = BKT.pGuess;
  const pCorrect = pMastery * pCorrectMastered + (1 - pMastery) * pCorrectNotMastered;
  const pIncorrect = 1 - pCorrect;

  let posterior;
  if (isCorrect) {
    posterior = (pMastery * pCorrectMastered) / pCorrect;
  } else {
    posterior = (pMastery * BKT.pSlip) / pIncorrect;
  }
  return Math.max(0, Math.min(1, posterior + (1 - posterior) * BKT.pLearn));
}

// ── Main Component ──────────────────────────────────────
export default function PracticePage() {
  const { courseId, lessonId } = useParams();
  const { t, lang } = useLanguage();

  const lessonData = (questionData[lang] || questionData.en)?.[lessonId];

  const [qIdx, setQIdx] = useState(0);
  const [pMastery, setPMastery] = useState((lessonData?.initialMastery || 35) / 100);
  const [wrongCount, setWrongCount] = useState(0);

  // phase: question → diagnosis → subLesson → retry → (next question or complete)
  const [phase, setPhase] = useState('question');

  const [answer, setAnswer] = useState('');
  const [answerFB, setAnswerFB] = useState(null);

  const [unlockedHints, setUnlockedHints] = useState(0);
  const [expandedHint, setExpandedHint] = useState(null);
  const [scaffoldAnswers, setScaffoldAnswers] = useState({});
  const [scaffoldFB, setScaffoldFB] = useState({});

  const [subStep, setSubStep] = useState(0);
  const [subAnswer, setSubAnswer] = useState('');
  const [subFB, setSubFB] = useState(null);
  const [subDone, setSubDone] = useState(false);

  const [completed, setCompleted] = useState([]);
  const [bktLog, setBktLog] = useState([]);

  // ── Guards ──
  if (!lessonData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="card p-12 text-center">
          <HelpCircle size={48} className="mx-auto text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">No Question Data</h2>
          <Link to={`/courses/${courseId}`} className="btn-secondary mt-4">
            <ArrowLeft size={16} /> {t('practice.backToLesson')}
          </Link>
        </div>
      </div>
    );
  }

  const questions = lessonData.questions;
  const q = questions[qIdx];
  const total = questions.length;
  const norm = (s) => s.trim().toLowerCase().replace(/\s+/g, ' ');
  const mp = Math.round(pMastery * 100);

  const log = (event, detail) =>
    setBktLog((p) => [...p, { event, detail, mastery: mp }]);

  // ── Handlers ──
  const checkMain = () => {
    const ok = q.correctAnswers.some((a) => norm(answer) === norm(a));
    setAnswerFB(ok ? 'correct' : 'incorrect');
    const np = bktUpdate(pMastery, ok);
    setPMastery(np);

    if (ok) {
      log('correct', `P(mastery) → ${Math.round(np * 100)}%`);
      setCompleted((p) => [...p, qIdx]);
    } else {
      const nw = wrongCount + 1;
      setWrongCount(nw);
      log('incorrect', `P(mastery) → ${Math.round(np * 100)}%`);
      if (nw >= 2 && phase === 'question') {
        setTimeout(() => {
          setPhase('diagnosis');
          log('diagnosis', `Gap: ${q.prerequisite.skill}`);
        }, 1200);
      }
    }
  };

  const checkScaff = (hid, ca) => {
    const ok = ca.some((a) => norm(scaffoldAnswers[hid] || '') === norm(a));
    setScaffoldFB((p) => ({ ...p, [hid]: ok ? 'correct' : 'incorrect' }));
    if (ok) setPMastery((p) => bktUpdate(p, true));
  };

  const unlockHint = () => {
    if (unlockedHints < q.hints.length) {
      setUnlockedHints((p) => p + 1);
      setExpandedHint(unlockedHints + 1);
    }
  };

  const startSub = () => {
    setPhase('subLesson');
    setSubStep(0);
    setSubAnswer('');
    setSubFB(null);
    setSubDone(false);
    log('subLesson', 'Started prerequisite mini-lesson');
  };

  const checkSub = () => {
    const cur = q.subLesson.practiceQuestions[subStep];
    const ok = cur.correctAnswers.some((a) => norm(subAnswer) === norm(a));
    setSubFB(ok ? 'correct' : 'incorrect');
    if (ok) {
      const np = bktUpdate(pMastery, true);
      setPMastery(np);
      log('subLesson_correct', `Sub-Q ${subStep + 1} correct → ${Math.round(np * 100)}%`);
    }
  };

  const nextSub = () => {
    if (subStep < q.subLesson.practiceQuestions.length - 1) {
      setSubStep((p) => p + 1);
      setSubAnswer('');
      setSubFB(null);
    } else {
      setSubDone(true);
      log('subLesson_done', 'Mini-lesson completed');
    }
  };

  const doRetry = () => {
    setPhase('retry');
    setAnswer('');
    setAnswerFB(null);
    setWrongCount(0);
    log('retry', 'Retrying with new understanding');
  };

  const nextQ = () => {
    if (qIdx < total - 1) {
      setQIdx((p) => p + 1);
      resetQ();
    } else {
      setPhase('complete');
    }
  };

  const resetQ = () => {
    setAnswer('');
    setAnswerFB(null);
    setWrongCount(0);
    setPhase('question');
    setUnlockedHints(0);
    setExpandedHint(null);
    setScaffoldAnswers({});
    setScaffoldFB({});
    setSubStep(0);
    setSubAnswer('');
    setSubFB(null);
    setSubDone(false);
  };

  // ── Complete Screen ──
  if (phase === 'complete') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="card p-8 sm:p-12 text-center max-w-lg w-full">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mx-auto mb-6">
            <Sparkles size={36} className="text-white" />
          </div>
          <img src="/12.png" alt="" className="w-24 h-24 object-contain mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {t('practice.lessonComplete') || 'Lesson Complete!'}
          </h2>
          <p className="text-gray-500 mb-6">
            {t('practice.greatJob') || "Great job! You've completed all questions."}
          </p>

          <div className="bg-atlas-50 rounded-2xl p-6 mb-6 border border-atlas-100">
            <div className="text-sm text-atlas-600 font-medium mb-1">
              {t('practice.finalMastery') || 'Final Mastery'}
            </div>
            <div className="text-4xl font-bold text-atlas-700">{mp}%</div>
            <div className="w-full h-3 bg-atlas-100 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-atlas-500 to-atlas-600 rounded-full transition-all duration-700"
                style={{ width: `${mp}%` }}
              />
            </div>
          </div>

          {/* BKT Trace Log */}
          <div className="bg-gray-50 rounded-xl p-4 text-left mb-6 max-h-48 overflow-y-auto border border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2 flex items-center gap-1.5">
              <Brain size={12} /> BKT Trace
            </h4>
            {bktLog.map((e, i) => (
              <div key={i} className="text-xs text-gray-500 flex items-start gap-2 mb-1">
                <span
                  className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                    e.event.includes('correct')
                      ? 'bg-emerald-400'
                      : e.event.includes('incorrect')
                      ? 'bg-red-400'
                      : 'bg-atlas-400'
                  }`}
                />
                <span>{e.detail}</span>
              </div>
            ))}
          </div>

          <Link to={`/courses/${courseId}`} className="btn-primary w-full">
            <ArrowLeft size={16} /> {t('practice.backToLesson')}
          </Link>
        </div>
      </div>
    );
  }

  // ── Main Render ──
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* ── Top Bar ── */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link
            to={`/courses/${courseId}`}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-atlas-600 transition-colors"
          >
            <ArrowLeft size={16} />
            <span className="hidden sm:inline">{t('practice.backToLesson')}</span>
          </Link>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500 font-medium">
              {t('practice.question')} {qIdx + 1} {t('practice.of')} {total}
            </span>
            <div className="hidden sm:flex gap-1.5">
              {Array.from({ length: total }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2.5 h-2.5 rounded-full transition-colors ${
                    completed.includes(i)
                      ? 'bg-emerald-400'
                      : i === qIdx
                      ? 'bg-atlas-500'
                      : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Brain size={16} className="text-atlas-500" />
            <div className="flex items-center gap-2">
              <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
                <div
                  className="h-full bg-gradient-to-r from-atlas-500 to-atlas-600 rounded-full transition-all duration-500"
                  style={{ width: `${mp}%` }}
                />
              </div>
              <span
                className={`text-sm font-bold transition-colors duration-300 ${
                  mp >= 70 ? 'text-emerald-500' : mp >= 40 ? 'text-atlas-600' : 'text-warm-500'
                }`}
              >
                {mp}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Left Panel 3/5 */}
          <div className="lg:col-span-3 space-y-5">
            {/* Phase badges */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-3 py-1 bg-atlas-50 text-atlas-700 rounded-full text-xs font-semibold">
                {lessonData.lessonTitle}
              </span>
              {phase === 'diagnosis' && (
                <span className="px-3 py-1 bg-warm-50 text-warm-700 rounded-full text-xs font-semibold animate-fade-in flex items-center gap-1">
                  <Brain size={12} /> {t('practice.bktDiagnosis') || 'Skill Gap Detected'}
                </span>
              )}
              {phase === 'subLesson' && (
                <span className="px-3 py-1 bg-violet-50 text-violet-700 rounded-full text-xs font-semibold animate-fade-in flex items-center gap-1">
                  <BookOpen size={12} /> {t('practice.bktSubLesson') || 'Mini-Lesson'}
                </span>
              )}
              {phase === 'retry' && (
                <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-semibold animate-fade-in flex items-center gap-1">
                  <RotateCcw size={12} /> {t('practice.bktRetry') || 'Retry'}
                </span>
              )}
            </div>

            {/* ══════════ DIAGNOSIS ══════════ */}
            {phase === 'diagnosis' && (
              <div className="card p-6 sm:p-8 border-2 border-warm-200 animate-fade-in">
                <div className="flex items-start gap-4 mb-6">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-warm-400 to-warm-500 flex items-center justify-center shrink-0">
                    <Brain size={24} className="text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-gray-900 mb-1">
                      {t('practice.bktDiagnosisTitle') || 'BKT Analysis: Knowledge Gap Found'}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {t('practice.bktDiagnosisDesc') ||
                        'Based on your responses, ATLAS identified a prerequisite skill that needs strengthening.'}
                    </p>
                  </div>
                  <img src="/10.png" alt="" className="w-16 h-16 object-contain hidden sm:block opacity-80" />
                </div>

                <div className="bg-warm-50 rounded-2xl p-5 border border-warm-100 mb-6">
                  <div className="text-xs uppercase tracking-wider text-warm-500 font-semibold mb-2">
                    {t('practice.prerequisiteSkill') || 'Prerequisite Skill'}
                  </div>
                  <div className="text-lg font-bold text-gray-900 mb-2">{q.prerequisite.skill}</div>
                  <p className="text-sm text-gray-600">{q.prerequisite.description}</p>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-6">
                  <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
                    <div className="text-lg font-bold text-red-500">{wrongCount}</div>
                    <div className="text-xs text-gray-500">{t('practice.wrongAttempts') || 'Wrong'}</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
                    <div className="text-lg font-bold text-atlas-600">{mp}%</div>
                    <div className="text-xs text-gray-500">P(Mastery)</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3 text-center border border-gray-100">
                    <div className="text-lg font-bold text-warm-500">
                      {Math.round(BKT.pLearn * 100)}%
                    </div>
                    <div className="text-xs text-gray-500">P(Learn)</div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button onClick={startSub} className="btn-primary flex-1">
                    <BookOpen size={16} />
                    {t('practice.startSubLesson') || 'Start Mini-Lesson'}
                  </button>
                  <button onClick={doRetry} className="btn-secondary flex-1">
                    <RotateCcw size={16} />
                    {t('practice.skipToRetry') || 'Skip & Retry'}
                  </button>
                </div>
              </div>
            )}

            {/* ══════════ SUB-LESSON ══════════ */}
            {phase === 'subLesson' && (
              <div className="card p-6 sm:p-8 border-2 border-violet-200 animate-fade-in">
                <div className="flex items-start gap-4 mb-6">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
                    <BookOpen size={24} className="text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-gray-900 mb-1">{q.subLesson.title}</h3>
                    <p className="text-sm text-gray-500">
                      {t('practice.subLessonDesc') ||
                        'Practice these prerequisite questions before retrying.'}
                    </p>
                  </div>
                  <img src="/5.png" alt="" className="w-14 h-14 object-contain hidden sm:block opacity-80" />
                </div>

                <div className="bg-violet-50 rounded-2xl p-5 border border-violet-100 mb-6">
                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                    {q.subLesson.explanation}
                  </p>
                </div>

                {/* Progress bar */}
                <div className="flex items-center gap-2 mb-4">
                  {q.subLesson.practiceQuestions.map((_, i) => (
                    <div
                      key={i}
                      className={`flex-1 h-2 rounded-full transition-colors ${
                        i < subStep
                          ? 'bg-emerald-400'
                          : i === subStep && !subDone
                          ? 'bg-violet-400'
                          : subDone
                          ? 'bg-emerald-400'
                          : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>

                {!subDone ? (
                  <>
                    <div className="bg-white rounded-2xl p-5 border border-gray-200 mb-4">
                      <div className="text-xs text-violet-500 font-semibold mb-2">
                        {t('practice.practiceQuestion') || 'Practice Question'}{' '}
                        {subStep + 1}/{q.subLesson.practiceQuestions.length}
                      </div>
                      <p className="text-xl font-bold text-gray-900 text-center py-3">
                        {q.subLesson.practiceQuestions[subStep].question}
                      </p>
                    </div>

                    <div className="max-w-sm mx-auto">
                      <input
                        type="text"
                        value={subAnswer}
                        onChange={(e) => {
                          setSubAnswer(e.target.value);
                          setSubFB(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && subAnswer.trim()) {
                            subFB === 'correct' ? nextSub() : checkSub();
                          }
                        }}
                        placeholder={t('practice.yourAnswer')}
                        className={`input-field text-center text-lg font-semibold w-full ${
                          subFB === 'correct'
                            ? 'border-emerald-400 ring-2 ring-emerald-100'
                            : subFB === 'incorrect'
                            ? 'border-red-400 ring-2 ring-red-100'
                            : ''
                        }`}
                      />

                      {subFB && (
                        <div
                          className={`mt-3 flex items-center justify-center gap-2 text-sm font-semibold animate-fade-in ${
                            subFB === 'correct' ? 'text-emerald-600' : 'text-red-500'
                          }`}
                        >
                          {subFB === 'correct' ? (
                            <>
                              <CheckCircle2 size={18} /> {t('practice.correct')}
                              <span className="text-gray-400 font-normal ml-2">
                                {q.subLesson.practiceQuestions[subStep].explanation}
                              </span>
                            </>
                          ) : (
                            <>
                              <XCircle size={18} /> {t('practice.incorrect')}
                            </>
                          )}
                        </div>
                      )}

                      {subFB === 'correct' ? (
                        <button onClick={nextSub} className="btn-primary w-full mt-4">
                          <ArrowRight size={16} />
                          {subStep < q.subLesson.practiceQuestions.length - 1
                            ? t('practice.nextPractice') || 'Next Practice Question'
                            : t('practice.finishSubLesson') || 'Finish Mini-Lesson'}
                        </button>
                      ) : (
                        <button
                          onClick={checkSub}
                          disabled={!subAnswer.trim()}
                          className="btn-primary w-full mt-4 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <Send size={16} /> {t('practice.submitAnswer')}
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="text-center py-4">
                    <img src="/11.png" alt="" className="w-20 h-20 object-contain mx-auto mb-3" />
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 size={28} className="text-white" />
                    </div>
                    <h4 className="text-lg font-bold text-gray-900 mb-2">
                      {t('practice.subLessonDone') || 'Mini-Lesson Complete!'}
                    </h4>
                    <p className="text-sm text-gray-500 mb-6">
                      {t('practice.subLessonDoneDesc') ||
                        "You've strengthened the prerequisite skill. Now let's retry the original question."}
                    </p>
                    <button onClick={doRetry} className="btn-primary mx-auto">
                      <RotateCcw size={16} />
                      {t('practice.retryQuestion') || 'Retry Original Question'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ══════════ QUESTION / RETRY ══════════ */}
            {(phase === 'question' || phase === 'retry') && (
              <>
                {phase === 'retry' && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center gap-3 animate-fade-in">
                    <Zap size={20} className="text-emerald-500 shrink-0" />
                    <p className="text-sm text-emerald-700 font-medium">
                      {t('practice.retryBanner') ||
                        'Great! Now try the question again with your strengthened understanding.'}
                    </p>
                  </div>
                )}

                <div className="card p-6 sm:p-8">
                  <div className="text-sm text-gray-400 mb-3 font-medium">
                    {t('practice.question')} {qIdx + 1}
                  </div>
                  <div className="bg-gradient-to-r from-atlas-50 to-violet-50 rounded-2xl p-6 sm:p-8 border border-atlas-100 mb-6">
                    <p className="text-2xl sm:text-3xl font-bold text-gray-900 font-display text-center">
                      {q.question}
                    </p>
                  </div>
                  <p className="text-sm text-gray-500 text-center mb-6">{q.questionExplanation}</p>

                  <div className="max-w-md mx-auto">
                    <input
                      type="text"
                      value={answer}
                      onChange={(e) => {
                        setAnswer(e.target.value);
                        setAnswerFB(null);
                      }}
                      onKeyDown={(e) => e.key === 'Enter' && answer.trim() && checkMain()}
                      placeholder={t('practice.yourAnswer')}
                      className={`input-field text-center text-lg font-semibold w-full ${
                        answerFB === 'correct'
                          ? 'border-emerald-400 ring-2 ring-emerald-100'
                          : answerFB === 'incorrect'
                          ? 'border-red-400 ring-2 ring-red-100'
                          : ''
                      }`}
                    />

                    {answerFB && (
                      <div
                        className={`mt-3 flex items-center justify-center gap-2 text-sm font-semibold animate-fade-in ${
                          answerFB === 'correct' ? 'text-emerald-600' : 'text-red-500'
                        }`}
                      >
                        {answerFB === 'correct' ? (
                          <>
                            <CheckCircle2 size={18} /> {t('practice.correct')}
                          </>
                        ) : (
                          <>
                            <XCircle size={18} /> {t('practice.incorrect')}
                          </>
                        )}
                      </div>
                    )}

                    {answerFB === 'correct' ? (
                      <button onClick={nextQ} className="btn-primary w-full mt-4">
                        <ArrowRight size={16} />
                        {qIdx < total - 1
                          ? t('practice.nextQuestion') || 'Next Question'
                          : t('practice.finishLesson') || 'Finish Lesson'}
                      </button>
                    ) : (
                      <button
                        onClick={checkMain}
                        disabled={!answer.trim()}
                        className="btn-primary w-full mt-4 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Send size={16} /> {t('practice.submitAnswer')}
                      </button>
                    )}
                  </div>
                </div>

                {/* Mobile hints */}
                <div className="lg:hidden">
                  <button
                    onClick={unlockHint}
                    disabled={unlockedHints >= q.hints.length}
                    className="btn-accent w-full disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Lightbulb size={16} />
                    {unlockedHints >= q.hints.length
                      ? `${t('practice.hints')} (${q.hints.length}/${q.hints.length})`
                      : `${t('practice.getHint')} (${unlockedHints}/${q.hints.length})`}
                  </button>

                  {unlockedHints > 0 && (
                    <div className="mt-4 space-y-3">
                      {q.hints.map((h, idx) => (
                        <HintCard
                          key={h.id}
                          hint={h}
                          index={idx}
                          unlocked={idx < unlockedHints}
                          expanded={expandedHint === idx + 1}
                          onToggle={() =>
                            setExpandedHint(expandedHint === idx + 1 ? null : idx + 1)
                          }
                          scaffoldAnswer={scaffoldAnswers[h.id] || ''}
                          onScaffoldChange={(v) =>
                            setScaffoldAnswers((p) => ({ ...p, [h.id]: v }))
                          }
                          scaffoldFeedback={scaffoldFB[h.id]}
                          onScaffoldSubmit={() => checkScaff(h.id, h.correctAnswers)}
                          t={t}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* ── Right Sidebar (desktop) ── */}
          <div className="hidden lg:block lg:col-span-2">
            <div className="sticky top-20 space-y-4">
              {/* Hint panel */}
              {(phase === 'question' || phase === 'retry') && (
                <div className="card overflow-visible">
                  <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                      <Lightbulb size={18} className="text-warm-500" />
                      {t('practice.hintPanel')}
                    </h3>
                    <span className="text-xs font-medium text-gray-400">
                      {unlockedHints}/{q.hints.length}
                    </span>
                  </div>

                  <div className="p-4">
                    <button
                      onClick={unlockHint}
                      disabled={unlockedHints >= q.hints.length}
                      className="btn-accent w-full mb-4 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Lightbulb size={15} />
                      {unlockedHints >= q.hints.length
                        ? `All ${t('practice.hints')} Unlocked`
                        : `${t('practice.getHint')} ${unlockedHints + 1}`}
                    </button>

                    {unlockedHints === 0 && (
                      <p className="text-sm text-gray-400 text-center py-4">
                        {t('practice.tryAnswering')}
                      </p>
                    )}

                    <div className="space-y-2.5 max-h-[40vh] overflow-y-auto pr-1">
                      {q.hints.map((h, idx) => (
                        <HintCard
                          key={h.id}
                          hint={h}
                          index={idx}
                          unlocked={idx < unlockedHints}
                          expanded={expandedHint === idx + 1}
                          onToggle={() =>
                            setExpandedHint(expandedHint === idx + 1 ? null : idx + 1)
                          }
                          scaffoldAnswer={scaffoldAnswers[h.id] || ''}
                          onScaffoldChange={(v) =>
                            setScaffoldAnswers((p) => ({ ...p, [h.id]: v }))
                          }
                          scaffoldFeedback={scaffoldFB[h.id]}
                          onScaffoldSubmit={() => checkScaff(h.id, h.correctAnswers)}
                          t={t}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* BKT Trace panel */}
              <div className="card overflow-visible">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                    <Brain size={18} className="text-atlas-500" />
                    {t('practice.bktTrace') || 'BKT Trace'}
                  </h3>
                </div>
                <div className="p-4">
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    <div className="bg-atlas-50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">P(Mastery)</div>
                      <div
                        className={`text-sm font-bold ${
                          mp >= 85 ? 'text-emerald-600' : 'text-atlas-600'
                        }`}
                      >
                        {mp}%
                      </div>
                    </div>
                    <div className="bg-atlas-50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">P(Learn)</div>
                      <div className="text-sm font-bold text-atlas-600">
                        {Math.round(BKT.pLearn * 100)}%
                      </div>
                    </div>
                    <div className="bg-atlas-50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">P(Guess)</div>
                      <div className="text-sm font-bold text-atlas-600">
                        {Math.round(BKT.pGuess * 100)}%
                      </div>
                    </div>
                    <div className="bg-atlas-50 rounded-lg p-2 text-center">
                      <div className="text-xs text-gray-500">P(Slip)</div>
                      <div className="text-sm font-bold text-atlas-600">
                        {Math.round(BKT.pSlip * 100)}%
                      </div>
                    </div>
                  </div>

                  {/* Mastery bar with threshold */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                      <span>{t('practice.mastery') || 'Mastery'}</span>
                      <span className="flex items-center gap-1">
                        <Target size={10} /> {Math.round(BKT.masteryThreshold * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          mp >= 85
                            ? 'bg-gradient-to-r from-emerald-400 to-emerald-500'
                            : 'bg-gradient-to-r from-atlas-400 to-atlas-600'
                        }`}
                        style={{ width: `${mp}%` }}
                      />
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-gray-400"
                        style={{ left: `${BKT.masteryThreshold * 100}%` }}
                      />
                    </div>
                  </div>

                  {bktLog.length > 0 ? (
                    <div className="max-h-36 overflow-y-auto space-y-1">
                      {bktLog
                        .slice()
                        .reverse()
                        .map((e, i) => (
                          <div
                            key={i}
                            className="text-xs text-gray-500 flex items-start gap-2"
                          >
                            <span
                              className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${
                                e.event.includes('correct')
                                  ? 'bg-emerald-400'
                                  : e.event.includes('incorrect')
                                  ? 'bg-red-400'
                                  : e.event === 'diagnosis'
                                  ? 'bg-warm-400'
                                  : 'bg-atlas-400'
                              }`}
                            />
                            <span>{e.detail}</span>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 text-center py-2">
                      {t('practice.bktNoEvents') || 'Answer questions to see BKT updates'}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Hint Card ───────────────────────────────────────────
function HintCard({
  hint,
  index,
  unlocked,
  expanded,
  onToggle,
  scaffoldAnswer,
  onScaffoldChange,
  scaffoldFeedback,
  onScaffoldSubmit,
  t,
}) {
  if (!unlocked) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 border border-gray-150 opacity-60">
        <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center shrink-0">
          <Lock size={14} className="text-gray-400" />
        </div>
        <span className="text-sm text-gray-400 font-medium">
          {t('practice.hint')} {index + 1} — {t('practice.locked')}
        </span>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-atlas-100 overflow-hidden bg-white animate-fade-in">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-atlas-50/50 transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-atlas-500 to-atlas-600 flex items-center justify-center shrink-0">
          <span className="text-white text-xs font-bold">{index + 1}</span>
        </div>
        <span className="text-sm font-semibold text-gray-800 flex-1">{hint.title}</span>
        {expanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 animate-fade-in">
          <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line mb-3">
            {hint.content}
          </p>

          {hint.type === 'scaffolding' && (
            <div className="bg-atlas-50 rounded-xl p-4 border border-atlas-100">
              <p className="text-sm font-medium text-atlas-700 mb-3">{hint.prompt}</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={scaffoldAnswer}
                  onChange={(e) => onScaffoldChange(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && scaffoldAnswer.trim() && onScaffoldSubmit()
                  }
                  placeholder={t('practice.scaffoldingPrompt')}
                  className={`input-field text-sm flex-1 ${
                    scaffoldFeedback === 'correct'
                      ? 'border-emerald-400 ring-1 ring-emerald-100'
                      : scaffoldFeedback === 'incorrect'
                      ? 'border-red-400 ring-1 ring-red-100'
                      : ''
                  }`}
                />
                <button
                  onClick={onScaffoldSubmit}
                  disabled={!scaffoldAnswer.trim()}
                  className="px-4 py-2 bg-atlas-600 text-white rounded-xl text-sm font-semibold hover:bg-atlas-700 transition-colors disabled:opacity-40"
                >
                  {t('practice.submitStep')}
                </button>
              </div>
              {scaffoldFeedback && (
                <div
                  className={`mt-2 flex items-center gap-1.5 text-xs font-semibold ${
                    scaffoldFeedback === 'correct' ? 'text-emerald-600' : 'text-red-500'
                  }`}
                >
                  {scaffoldFeedback === 'correct' ? (
                    <>
                      <CheckCircle2 size={14} /> {t('practice.correct')}
                    </>
                  ) : (
                    <>
                      <XCircle size={14} /> {t('practice.incorrect')}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
