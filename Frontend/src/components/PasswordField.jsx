/*
 * Password input with a show/hide toggle, shared by the log-in and sign-up forms.
 */
import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function PasswordField({ id, label, hint, ...inputProps }) {
  const { t } = useLanguage();
  const [visible, setVisible] = useState(false);
  const ToggleIcon = visible ? EyeOff : Eye;

  return (
    <div>
      <label className="block text-sm font-semibold text-ink-soft" htmlFor={id}>
        {label}
      </label>
      <div className="relative mt-2">
        <input id={id} type={visible ? 'text' : 'password'} className="input-field pr-12" {...inputProps} />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-ink-muted hover:text-ink"
          aria-label={visible ? t('auth.hidePassword') : t('auth.showPassword')}
          aria-pressed={visible}
        >
          <ToggleIcon size={18} aria-hidden="true" />
        </button>
      </div>
      {hint && <p className="mt-1.5 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}
