import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { UserPlus, ArrowRight } from 'lucide-react';

export default function SignupPage() {
  const { t } = useLanguage();
  const { signUp, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (user) {
      navigate('/courses');
    }
  }, [user, navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');

    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError(t('auth.loginErrorEmpty'));
      return;
    }

    setLoading(true);
    try {
      await signUp(trimmedUsername);
      setMessage(t('auth.signupSuccess'));
      window.setTimeout(() => navigate('/courses'), 600);
    } catch (err) {
      if (err.message === 'already_exists') {
        setError(t('auth.signupErrorExists'));
      } else {
        setError(t('auth.signupErrorServer'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-atlas-50 via-white to-atlas-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] items-center">
          <section className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full bg-atlas-100 px-4 py-2 text-sm font-semibold text-atlas-700 shadow-sm">
              <UserPlus size={18} />
              {t('auth.signupTitle')}
            </div>
            <div>
              <h1 className="font-display text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
                {t('auth.signupHeadline')}
              </h1>
              <p className="mt-4 max-w-xl text-gray-600 text-lg leading-8">
                {t('auth.signupSubtitle')}
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="card p-6">
                <h2 className="font-semibold text-lg text-gray-900 mb-3">{t('auth.signupBenefit1Title')}</h2>
                <p className="text-gray-500 text-sm leading-relaxed">{t('auth.signupBenefit1Desc')}</p>
              </div>
              <div className="card p-6 bg-gradient-to-br from-atlas-700 to-atlas-800 text-white">
                <h2 className="font-semibold text-lg mb-3">{t('auth.signupBenefit2Title')}</h2>
                <p className="text-gray-100 text-sm leading-relaxed">{t('auth.signupBenefit2Desc')}</p>
              </div>
            </div>
          </section>

          <section className="rounded-[2rem] border border-gray-200 bg-white/95 p-8 shadow-soft backdrop-blur-sm">
            <div className="mb-8">
              <p className="text-sm uppercase tracking-[0.24em] text-atlas-500 font-semibold">{t('auth.signupLabel')}</p>
              <h2 className="mt-3 text-3xl font-bold text-gray-900">{t('auth.usernameLabel')}</h2>
              <p className="mt-2 text-sm text-gray-500">{t('auth.signupSubtitle')}</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <label className="block text-sm font-medium text-gray-700">
                {t('auth.usernameLabel')}
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  type="text"
                  placeholder={t('auth.usernamePlaceholder')}
                  className="input-field mt-3"
                  autoComplete="username"
                />
              </label>

              {error && (
                <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              {message && (
                <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full justify-center py-3 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? t('auth.signupButtonLoading') : t('auth.signupButton')}
              </button>
            </form>

            <div className="mt-6 border-t border-gray-200 pt-6 text-sm text-gray-500">
              <p>
                {t('auth.loginLink')} {' '}
                <Link to="/login" className="font-semibold text-atlas-700 hover:text-atlas-900">
                  {t('nav.login')} <ArrowRight size={14} className="inline-block align-middle" />
                </Link>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
