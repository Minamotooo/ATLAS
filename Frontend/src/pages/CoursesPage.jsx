import { useEffect, useState, useMemo } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { coursesData } from '../data/courseData';
import {
  Search, BookOpen, TrendingUp, Clock, ArrowRight,
  BarChart3
} from 'lucide-react';

export default function CoursesPage() {
  const { t, lang } = useLanguage();
  const { user, loading, signOut } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [user, loading, navigate]);

  const courses = coursesData[lang] || coursesData.en;

  const filters = [
    { key: 'All', label: t('courses.allSubjects') },
    { key: 'Mathematics', label: t('courses.mathematics') },
    { key: 'Science', label: t('courses.science') },
    { key: 'English', label: t('courses.english') },
  ];

  // Map filter keys to all possible subject values (en + bn)
  const subjectMap = {
    Mathematics: ['Mathematics', 'গণিত'],
    Science: ['Science', 'বিজ্ঞান'],
    English: ['English', 'ইংরেজি'],
    Physics: ['Physics', 'পদার্থবিজ্ঞান'],
    Chemistry: ['Chemistry', 'রসায়ন'],
  };

  const filteredCourses = useMemo(() => {
    return courses.filter((c) => {
      const matchesSearch = c.title.toLowerCase().includes(search.toLowerCase()) ||
        c.description.toLowerCase().includes(search.toLowerCase());
      const matchesFilter = activeFilter === 'All' ||
        (subjectMap[activeFilter] && subjectMap[activeFilter].includes(c.subject));
      return matchesSearch && matchesFilter;
    });
  }, [courses, search, activeFilter]);

  const activeCourseCount = courses.filter(c => c.status === 'in-progress').length;
  const avgMastery = Math.round(
    courses.filter(c => c.mastery > 0).reduce((sum, c) => sum + c.mastery, 0) /
    (courses.filter(c => c.mastery > 0).length || 1)
  );

  const inProgressCourses = filteredCourses.filter(c => c.status === 'in-progress');
  const otherCourses = filteredCourses.filter(c => c.status !== 'in-progress');

  return (
    <div className="min-h-screen bg-atlas-50/50">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-atlas-700 via-atlas-800 to-atlas-900 text-white relative overflow-hidden">
        <img src="/7.png" alt="" className="absolute right-6 top-1/2 -translate-y-1/2 w-48 h-48 object-contain opacity-15 hidden lg:block" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-10 relative">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold mb-1">
                {t('courses.welcome')}, {user?.user_name || t('courses.studentName')}! 👋
              </h1>
              <p className="text-atlas-200 text-sm sm:text-base">
                {t('courses.dashboardSubtitle')}
              </p>
            </div>
            <button
              onClick={() => {
                signOut();
                navigate('/login');
              }}
              className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-atlas-700 shadow-sm hover:bg-atlas-50 transition"
            >
              {t('nav.logout')}
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 sm:gap-4 mt-6">
            {[
              { label: t('courses.activeCourses'), value: activeCourseCount, icon: <BookOpen size={18} /> },
              { label: t('courses.avgMastery'), value: `${avgMastery}%`, icon: <BarChart3 size={18} /> },
              { label: t('courses.weeklyTime'), value: `4.5 ${t('courses.hours')}`, icon: <Clock size={18} /> },
            ].map((stat) => (
              <div key={stat.label} className="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/10">
                <div className="flex items-center gap-2 text-atlas-200 mb-1">
                  {stat.icon}
                  <span className="text-xs font-medium truncate">{stat.label}</span>
                </div>
                <div className="text-xl sm:text-2xl font-bold">{stat.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Search & Filter */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('courses.searchCourses')}
              className="input-field pl-10"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-hide">
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setActiveFilter(f.key)}
                className={`px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                  activeFilter === f.key
                    ? 'bg-atlas-600 text-white shadow-md'
                    : 'bg-white text-gray-600 border border-gray-200 hover:border-atlas-300 hover:text-atlas-600'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Continue Learning */}
        {inProgressCourses.length > 0 && (
          <div className="mb-8">
            <h2 className="font-display text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-atlas-500" />
              {t('courses.continueLearning')}
              <img src="/14.png" alt="" className="w-8 h-8 object-contain ml-auto opacity-50 hidden sm:block" />
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {inProgressCourses.map((course) => (
                <CourseCard key={course.id} course={course} t={t} highlight />
              ))}
            </div>
          </div>
        )}

        {/* All Courses */}
        <div>
          <h2 className="font-display text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <BookOpen size={20} className="text-gray-400" />
            {t('courses.allCourses')}
          </h2>
          {filteredCourses.length === 0 ? (
            <div className="card p-12 text-center">
              <Search size={40} className="mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">{t('courses.noResults')}</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {(otherCourses.length > 0 ? otherCourses : filteredCourses).map((course) => (
                <CourseCard key={course.id} course={course} t={t} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CourseCard({ course, t, highlight }) {
  const hasLessons = course.id === 'class3-math'; // only class3-math has lessons data

  return (
    <Link
      to={hasLessons ? `/courses/${course.id}` : '#'}
      className={`card-hover flex flex-col ${!hasLessons ? 'cursor-default' : ''}`}
      onClick={(e) => !hasLessons && e.preventDefault()}
    >
      {/* Color header */}
      <div className={`h-2 bg-gradient-to-r ${course.color}`} />
      <div className="p-5 flex flex-col flex-1">
        {/* Icon + title */}
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${course.color} flex items-center justify-center text-2xl shrink-0 shadow-sm`}>
            {course.icon}
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 leading-snug line-clamp-2">{course.title}</h3>
            <span className="text-xs text-gray-400 font-mono">{course.code}</span>
          </div>
        </div>

        <p className="text-sm text-gray-500 mb-4 line-clamp-2 flex-1">{course.description}</p>

        {/* Progress */}
        <div className="mt-auto">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-gray-500">{course.totalLessons} {t('courses.lessons')}</span>
            {course.mastery > 0 ? (
              <span className="font-semibold text-atlas-600">{course.mastery}% {t('courses.mastery')}</span>
            ) : (
              <span className="text-gray-400">{t('courses.notStarted')}</span>
            )}
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${course.color} transition-all duration-500`}
              style={{ width: `${course.mastery}%` }}
            />
          </div>
        </div>

        {/* Action */}
        <div className="mt-4">
          {hasLessons ? (
            <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-atlas-600 group-hover:text-atlas-700">
              {course.status === 'in-progress' ? t('courses.continueBtn') : course.status === 'not-started' ? t('courses.startCourse') : t('courses.viewCourse')}
              <ArrowRight size={14} />
            </span>
          ) : (
            <span className="text-sm text-gray-400">{t('courses.startCourse')}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
