import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { UserPlus, ArrowRight } from 'lucide-react';
import AuthShell from '../components/AuthShell';

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
    <AuthShell
      badgeIcon={UserPlus}
      badge={t('auth.signupTitle')}
      title={t('auth.signupHeadline')}
      subtitle={t('auth.signupSubtitle')}
      benefits={[
        { title: t('auth.signupBenefit1Title'), desc: t('auth.signupBenefit1Desc') },
        { title: t('auth.signupBenefit2Title'), desc: t('auth.signupBenefit2Desc') },
      ]}
    >
      <div className="mb-8">
        <p className="eyebrow">{t('auth.signupLabel')}</p>
        <h2 className="mt-3 font-display text-3xl font-bold text-ink">{t('auth.usernameLabel')}</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <label className="block text-sm font-semibold text-ink-soft" htmlFor="signup-username">
          {t('auth.usernameLabel')}
        </label>
        <input
          id="signup-username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          type="text"
          placeholder={t('auth.usernamePlaceholder')}
          className="input-field !mt-2"
          autoComplete="username"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? 'signup-error' : undefined}
        />

        <div aria-live="polite">
          {error && (
            <div id="signup-error" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
              {error}
            </div>
          )}
          {message && (
            <div className="rounded-2xl border border-mint-200 bg-mint-50 px-4 py-3 text-sm font-medium text-mint-600">
              {message}
            </div>
          )}
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full py-3.5" data-magnetic="0.15">
          {loading ? t('auth.signupButtonLoading') : t('auth.signupButton')}
          {!loading && <ArrowRight size={17} aria-hidden="true" />}
        </button>
      </form>

      <div className="mt-7 border-t border-ink/10 pt-6 text-sm text-ink-muted">
        <p>
          {t('auth.loginLink')}{' '}
          <Link to="/login" className="font-bold text-atlas-700 hover:text-ink">
            {t('nav.login')} <ArrowRight size={14} className="inline-block align-middle" aria-hidden="true" />
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
