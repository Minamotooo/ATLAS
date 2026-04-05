import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const { t } = useLanguage();
  const { signIn, user } = useAuth();
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
      await signIn(trimmedUsername);
      setMessage(t('auth.loginSuccess'));
      window.setTimeout(() => navigate('/courses'), 600);
    } catch (err) {
      if (err.message === 'not_found') {
        setError(t('auth.loginErrorNotFound'));
      } else {
        setError(t('auth.loginErrorServer'));
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
              <ShieldCheck size={18} />
              Secure login
            </div>
            <div>
              <h1 className="font-display text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
                {t('auth.loginTitle')}
              </h1>
              <p className="mt-4 max-w-xl text-gray-600 text-lg leading-8">
                {t('auth.loginSubtitle')}
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="card p-6">
                <h2 className="font-semibold text-lg text-gray-900 mb-3">Fast access</h2>
                <p className="text-gray-500 text-sm leading-relaxed">Use your registered username to sign in quickly and continue where you left off.</p>
              </div>
              <div className="card p-6 bg-gradient-to-br from-atlas-700 to-atlas-800 text-white">
                <h2 className="font-semibold text-lg mb-3">Adaptive progress</h2>
                <p className="text-gray-100 text-sm leading-relaxed">Your mastery, question history, and practice path stay in sync with the adaptive backend.</p>
              </div>
            </div>
          </section>

          <section className="rounded-[2rem] border border-gray-200 bg-white/95 p-8 shadow-soft backdrop-blur-sm">
            <div className="mb-8">
              <p className="text-sm uppercase tracking-[0.24em] text-atlas-500 font-semibold">Log in</p>
              <h2 className="mt-3 text-3xl font-bold text-gray-900">{t('auth.usernameLabel')}</h2>
              <p className="mt-2 text-sm text-gray-500">{t('auth.loginSubtitle')}</p>
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
                {loading ? t('auth.loginButtonLoading') : t('auth.loginButton')}
              </button>
            </form>

            <div className="mt-6 border-t border-gray-200 pt-6 text-sm text-gray-500">
              <p>
                {t('auth.signupLink')} {' '}
                <Link to="/signup" className="font-semibold text-atlas-700 hover:text-atlas-900">
                  {t('nav.signup')} <ArrowRight size={14} className="inline-block align-middle" />
                </Link>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
