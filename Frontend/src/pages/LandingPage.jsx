import { useLanguage } from '../context/LanguageContext';
import { Link } from 'react-router-dom';
import {
  Brain, MessageSquareText, Lightbulb, Globe,
  BookOpen, Sparkles, Send, TrendingUp, Target, CheckCircle2,
  ArrowRight, Users, GraduationCap, BarChart3
} from 'lucide-react';
import Footer from '../components/Footer';

/* ---- Illustrations ---- */

export default function LandingPage() {
  const { t } = useLanguage();

  const features = [
    {
      icon: <Brain size={28} />,
      title: t('landing.feature1Title'),
      desc: t('landing.feature1Desc'),
      gradient: 'from-atlas-500 to-atlas-700',
      illustration: <img src="/3.png" alt="Adaptive Learning" className="w-20 h-20 mb-2 object-contain" />,
    },
    {
      icon: <MessageSquareText size={28} />,
      title: t('landing.feature2Title'),
      desc: t('landing.feature2Desc'),
      gradient: 'from-warm-400 to-coral-500',
      illustration: <img src="/4.png" alt="Smart Feedback" className="w-20 h-20 mb-2 object-contain" />,
    },
    {
      icon: <Lightbulb size={28} />,
      title: t('landing.feature3Title'),
      desc: t('landing.feature3Desc'),
      gradient: 'from-mint-400 to-mint-500',
      illustration: <img src="/6.png" alt="Guided Hints" className="w-20 h-20 mb-2 object-contain" />,
    },
  ];

  const steps = [
    { icon: <BookOpen size={22} />, title: t('landing.step1'), desc: t('landing.step1Desc'), color: 'from-atlas-400 to-atlas-600' },
    { icon: <Sparkles size={22} />, title: t('landing.step2'), desc: t('landing.step2Desc'), color: 'from-atlas-500 to-atlas-700' },
    { icon: <Send size={22} />, title: t('landing.step3'), desc: t('landing.step3Desc'), color: 'from-emerald-400 to-teal-600' },
    { icon: <MessageSquareText size={22} />, title: t('landing.step4'), desc: t('landing.step4Desc'), color: 'from-warm-400 to-orange-500' },
    { icon: <TrendingUp size={22} />, title: t('landing.step5'), desc: t('landing.step5Desc'), color: 'from-pink-400 to-rose-600' },
    { icon: <Target size={22} />, title: t('landing.step6'), desc: t('landing.step6Desc'), color: 'from-cyan-400 to-blue-600' },
  ];

  return (
    <div className="min-h-screen">
      {/* ===== HERO ===== */}
      <section className="relative overflow-hidden bg-gradient-to-br from-atlas-900 via-atlas-800 to-atlas-700">
        {/* Decorative blobs */}
        <div className="absolute top-20 -left-32 w-96 h-96 bg-atlas-600/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-80 h-80 bg-atlas-500/15 rounded-full blur-3xl" />
        <div className="absolute top-40 right-20 w-20 h-20 bg-warm-300/20 rounded-full blur-2xl animate-float" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24 lg:py-28">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left */}
            <div className="animate-fade-in">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 text-atlas-200 rounded-full text-sm font-medium mb-6 border border-white/10">
                <Sparkles size={14} />
                AI-Powered Adaptive Learning
              </div>
              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-tight mb-6">
                {t('landing.heroTitle').split(',').map((part, i) => (
                  <span key={i}>
                    {i === 1 ? (
                      <span className="bg-gradient-to-r from-warm-300 to-warm-400 bg-clip-text text-transparent">
                        {part}
                      </span>
                    ) : part}
                    {i === 0 && ','}
                  </span>
                ))}
              </h1>
              <p className="text-lg text-atlas-200 leading-relaxed mb-8 max-w-xl">
                {t('landing.heroSubtitle')}
              </p>
              <div className="flex flex-wrap gap-3">
                <Link to="/courses" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-atlas-700 font-semibold rounded-xl shadow-lg hover:shadow-xl hover:bg-atlas-50 transition-all duration-200 active:scale-95 text-base">
                  {t('landing.heroCta')}
                  <ArrowRight size={18} />
                </Link>
                <a href="#workflow" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200 active:scale-95 text-base">
                  {t('landing.heroSecondaryCta')}
                </a>
              </div>
            </div>

            {/* Right — illustration */}
            <div className="animate-slide-up mt-8 lg:mt-0">
              <img src="/1.png" alt="Student learning with ATLAS" className="w-full h-auto max-w-xs sm:max-w-sm lg:max-w-md mx-auto drop-shadow-2xl" />
            </div>
          </div>
        </div>
      </section>

      {/* ===== STATS ===== */}
      <section className="bg-atlas-50 border-y border-atlas-100 relative overflow-hidden">
        <img src="/5.png" alt="" className="absolute right-8 top-1/2 -translate-y-1/2 w-28 h-28 object-contain opacity-10 hidden lg:block" />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <div className="grid grid-cols-3 gap-8 text-center">
            {[
              { value: '10,000+', label: t('landing.statsStudents'), icon: <Users size={20} className="text-atlas-500" /> },
              { value: '500+', label: t('landing.statsLessons'), icon: <BookOpen size={20} className="text-mint-500" /> },
              { value: '87%', label: t('landing.statsMastery'), icon: <BarChart3 size={20} className="text-warm-500" /> },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center">
                <div className="mb-2">{stat.icon}</div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900 font-display">{stat.value}</div>
                <div className="text-xs sm:text-sm text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== FEATURES ===== */}
      <section id="features" className="py-16 sm:py-24 bg-gradient-to-b from-atlas-50 to-atlas-100/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              {t('landing.featuresTitle')}
            </h2>
            <p className="text-gray-500 max-w-2xl mx-auto">
              {t('landing.featuresSubtitle')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feat, idx) => (
              <div key={idx} className="card-hover p-8 group text-center">
                <div className="flex justify-center">{feat.illustration}</div>
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feat.gradient} flex items-center justify-center text-white mx-auto mb-5 group-hover:scale-110 transition-transform`}>
                  {feat.icon}
                </div>
                <h3 className="font-display text-xl font-bold text-gray-900 mb-3">{feat.title}</h3>
                <p className="text-gray-500 leading-relaxed text-sm">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== BILINGUAL ===== */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="bg-gradient-to-r from-atlas-700 to-atlas-900 rounded-3xl p-8 sm:p-12 text-white relative overflow-hidden">
            <div className="absolute top-0 right-0 w-60 h-60 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-20 w-40 h-40 bg-white/5 rounded-full translate-y-1/2" />
            <div className="relative grid md:grid-cols-2 gap-8 items-center">
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Globe size={22} />
                  <span className="text-atlas-200 text-sm font-medium uppercase tracking-wider">Bilingual Platform</span>
                </div>
                <h2 className="font-display text-3xl sm:text-4xl font-bold mb-4">
                  {t('landing.bilingualTitle')}
                </h2>
                <p className="text-atlas-200 leading-relaxed">
                  {t('landing.bilingualDesc')}
                </p>
              </div>
              <div className="flex justify-center">
                <img src="/9.png" alt="Bilingual learning" className="w-48 h-48 object-contain hidden md:block absolute right-8 top-1/2 -translate-y-1/2 opacity-20" />
                <div className="space-y-3 w-full max-w-xs">
                  <div className="bg-white/15 backdrop-blur-sm rounded-2xl px-6 py-4 border border-white/20">
                    <div className="text-sm text-atlas-200 mb-1">Question</div>
                    <div className="font-semibold text-lg">__ × ৮ = ৭২</div>
                  </div>
                  <div className="bg-white/15 backdrop-blur-sm rounded-2xl px-6 py-4 border border-white/20">
                    <div className="text-sm text-atlas-200 mb-1">ইঙ্গিত (Hint)</div>
                    <div className="text-sm">ভাগ হলো গুণের উল্টো!</div>
                    <div className="text-sm text-atlas-300 mt-1">Division is the opposite of multiplication!</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== WORKFLOW ===== */}
      <section id="workflow" className="py-16 sm:py-24 bg-gradient-to-b from-atlas-100/30 via-atlas-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              {t('landing.workflowTitle')}
            </h2>
            <p className="text-gray-500">{t('landing.workflowSubtitle')}</p>
            <div className="flex justify-center gap-4 mt-6">
              <img src="/13.png" alt="" className="w-16 h-16 object-contain opacity-60 hidden sm:block" />
              <img src="/14.png" alt="" className="w-16 h-16 object-contain opacity-60 hidden sm:block" />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
            {steps.map((step, idx) => (
              <div key={idx} className="card p-6 text-center group hover:shadow-lg hover:-translate-y-1">
                <div className="relative mx-auto mb-4">
                  <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center text-white mx-auto group-hover:scale-110 transition-transform`}>
                    {step.icon}
                  </div>
                  <span className="absolute -top-2 -right-2 w-7 h-7 bg-white border-2 border-gray-200 rounded-full flex items-center justify-center text-xs font-bold text-gray-500">
                    {idx + 1}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">{step.title}</h3>
                <p className="text-sm text-gray-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="py-16 sm:py-24 bg-atlas-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <div className="bg-gradient-to-r from-atlas-100 to-atlas-50 rounded-3xl p-10 sm:p-14 border border-atlas-200 relative overflow-hidden">
            <img src="/2.png" alt="" className="absolute right-4 bottom-4 w-40 h-40 object-contain opacity-10 hidden sm:block" />
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-gray-900 mb-4 relative">
              {t('landing.ctaTitle')}
            </h2>
            <p className="text-gray-500 mb-8 max-w-xl mx-auto">
              {t('landing.ctaSubtitle')}
            </p>
            <Link to="/courses" className="btn-primary text-lg px-10 py-4">
              {t('landing.ctaButton')}
              <ArrowRight size={20} />
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
