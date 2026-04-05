import { useParams, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { lessonsData } from '../data/courseData';
import {
  ArrowLeft, CheckCircle2, BookOpen, Lock,
  Clock, HelpCircle, ArrowRight, BarChart3, Play
} from 'lucide-react';

export default function LessonsPage() {
  const { courseId } = useParams();
  const { t, lang } = useLanguage();

  const data = (lessonsData[lang] || lessonsData.en)?.[courseId];

  if (!data) {
    return (
      <div className="min-h-screen bg-atlas-50/50 flex items-center justify-center">
        <div className="card p-12 text-center">
          <BookOpen size={48} className="mx-auto text-gray-300 mb-4" />
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Coming Soon</h2>
          <p className="text-gray-500 mb-6">Lessons for this course are being prepared.</p>
          <Link to="/courses" className="btn-secondary">
            <ArrowLeft size={16} /> {t('lessons.backToCourses')}
          </Link>
        </div>
      </div>
    );
  }

  const completedCount = data.lessons.filter(l => l.status === 'completed').length;
  const currentLesson = data.lessons.find(l => l.status === 'in-progress');

  const statusConfig = {
    completed: { icon: <CheckCircle2 size={18} />, color: 'text-emerald-500', bg: 'bg-emerald-50 border-emerald-200', badge: 'bg-emerald-100 text-emerald-700' },
    'in-progress': { icon: <Play size={18} />, color: 'text-atlas-500', bg: 'bg-atlas-50 border-atlas-200', badge: 'bg-atlas-100 text-atlas-700' },
    available: { icon: <BookOpen size={18} />, color: 'text-gray-400', bg: 'bg-white border-gray-200', badge: 'bg-gray-100 text-gray-600' },
    locked: { icon: <Lock size={18} />, color: 'text-gray-300', bg: 'bg-gray-50 border-gray-150', badge: 'bg-gray-100 text-gray-400' },
  };

  return (
    <div className="min-h-screen bg-atlas-50/50">
      {/* Course Header */}
      <div className={`bg-gradient-to-r ${data.courseColor} text-white relative overflow-hidden`}>
        <div className="absolute inset-0 bg-black/10" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/3" />
        <img src="/8.png" alt="" className="absolute right-8 bottom-4 w-36 h-36 object-contain opacity-20 hidden lg:block" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <Link to="/courses" className="inline-flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-4 transition-colors">
            <ArrowLeft size={16} />
            {t('lessons.backToCourses')}
          </Link>

          <div className="flex items-center gap-4 mb-6">
            <div className="text-4xl">{data.courseIcon}</div>
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold">{data.courseName}</h1>
            </div>
          </div>

          {/* Progress bar */}
          <div className="max-w-md">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-white/80">{t('lessons.courseProgress')}</span>
              <span className="font-semibold">{data.progress}%</span>
            </div>
            <div className="w-full h-3 bg-white/20 rounded-full overflow-hidden">
              <div
                className="h-full bg-white rounded-full transition-all duration-700"
                style={{ width: `${data.progress}%` }}
              />
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-6 mt-6">
            <div className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-2.5 border border-white/10">
              <div className="text-xs text-white/70">{t('lessons.overallMastery')}</div>
              <div className="text-lg font-bold">{data.progress}%</div>
            </div>
            <div className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-2.5 border border-white/10">
              <div className="text-xs text-white/70">{t('lessons.totalLessons')}</div>
              <div className="text-lg font-bold">{data.lessons.length}</div>
            </div>
            <div className="bg-white/15 backdrop-blur-sm rounded-xl px-4 py-2.5 border border-white/10">
              <div className="text-xs text-white/70">{t('lessons.completed')}</div>
              <div className="text-lg font-bold">{completedCount}/{data.lessons.length}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Continue Card */}
        {currentLesson && (
          <div className="card mb-8 overflow-hidden">
            <div className="bg-gradient-to-r from-atlas-50 to-atlas-100 p-6 border-b border-atlas-200">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <span className="text-xs font-semibold text-atlas-600 uppercase tracking-wider">{t('lessons.continueLesson')}</span>
                  <h3 className="font-display text-lg font-bold text-gray-900 mt-1">
                    {currentLesson.number} — {currentLesson.title}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">{currentLesson.description}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1"><Clock size={12} /> {currentLesson.time} {t('lessons.mins')}</span>
                    <span className="flex items-center gap-1"><HelpCircle size={12} /> {currentLesson.questions} {t('lessons.questions')}</span>
                    <span className="flex items-center gap-1"><BarChart3 size={12} /> {currentLesson.mastery}% {t('courses.mastery')}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <img src="/13.png" alt="" className="w-14 h-14 object-contain hidden sm:block opacity-60" />
                  <Link
                    to={`/courses/${courseId}/lessons/${currentLesson.id}/practice`}
                    className="btn-primary shrink-0"
                  >
                    {t('lessons.continuePractice')}
                    <ArrowRight size={16} />
                  </Link>
                </div>
              </div>
              {/* Progress */}
              <div className="mt-4">
                <div className="w-full h-2 bg-atlas-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-atlas-500 to-atlas-600 rounded-full"
                    style={{ width: `${currentLesson.mastery}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Lesson Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.lessons.map((lesson) => {
            const config = statusConfig[lesson.status];
            const isClickable = lesson.status !== 'locked';
            const isActive = lesson.status === 'in-progress';

            return (
              <div
                key={lesson.id}
                className={`card flex flex-col border ${config.bg} ${
                  lesson.status === 'locked' ? 'opacity-60' : 'hover:shadow-lg hover:-translate-y-0.5'
                } transition-all`}
              >
                <div className="p-5 flex flex-col flex-1">
                  {/* Header row */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className={config.color}>{config.icon}</span>
                      <span className="text-xs font-mono text-gray-400">{lesson.number}</span>
                    </div>
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${config.badge}`}>
                      {t(`lessons.${lesson.status === 'in-progress' ? 'inProgress' : lesson.status}`)}
                    </span>
                  </div>

                  <h3 className={`font-semibold mb-1 ${lesson.status === 'locked' ? 'text-gray-400' : 'text-gray-900'}`}>
                    {lesson.title}
                  </h3>
                  <p className={`text-sm mb-3 flex-1 ${lesson.status === 'locked' ? 'text-gray-300' : 'text-gray-500'}`}>
                    {lesson.description}
                  </p>

                  {/* Meta */}
                  <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                    <span className="flex items-center gap-1"><Clock size={11} /> {lesson.time} {t('lessons.mins')}</span>
                    <span className="flex items-center gap-1"><HelpCircle size={11} /> {lesson.questions} {t('lessons.questions')}</span>
                  </div>

                  {/* Mastery bar */}
                  {lesson.mastery > 0 && (
                    <div className="mb-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-500">{t('courses.mastery')}</span>
                        <span className="font-semibold text-atlas-600">{lesson.mastery}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            lesson.mastery >= 90 ? 'bg-emerald-400' : 'bg-atlas-400'
                          }`}
                          style={{ width: `${lesson.mastery}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Action */}
                  {isClickable && (
                    <Link
                      to={
                        lesson.id === 'math-symbols'
                          ? `/courses/${courseId}/lessons/${lesson.id}/practice`
                          : '#'
                      }
                      onClick={(e) => lesson.id !== 'math-symbols' && e.preventDefault()}
                      className={`inline-flex items-center justify-center gap-1.5 text-sm font-semibold py-2.5 rounded-xl transition-all ${
                        isActive
                          ? 'bg-atlas-600 text-white hover:bg-atlas-700'
                          : lesson.status === 'completed'
                          ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {isActive ? t('lessons.resume') : lesson.status === 'completed' ? t('lessons.completed') : t('lessons.startLesson')}
                      {isActive && <ArrowRight size={14} />}
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
