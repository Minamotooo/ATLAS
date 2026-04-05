import { Link, useLocation } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { Menu, X, Globe } from 'lucide-react';
import { useState } from 'react';

export default function Navbar({ variant = 'default' }) {
  const { t, lang, toggleLang } = useLanguage();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <nav className="sticky top-0 z-50 bg-atlas-700 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <img src="/logo.png" alt="ATLAS" className="h-9 w-auto" />
            <span className="font-display font-bold text-xl text-white">
              ATLAS
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === '/'
                  ? 'text-white bg-white/15'
                  : 'text-atlas-200 hover:text-white hover:bg-white/10'
              }`}
            >
              {t('nav.home')}
            </Link>
            <Link
              to="/courses"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname.startsWith('/courses')
                  ? 'text-white bg-white/15'
                  : 'text-atlas-200 hover:text-white hover:bg-white/10'
              }`}
            >
              {t('nav.courses')}
            </Link>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Language Toggle */}
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-atlas-200 hover:text-white hover:bg-white/10 transition-colors"
              title={lang === 'en' ? 'বাংলায় পরিবর্তন করুন' : 'Switch to English'}
            >
              <Globe size={16} />
              <span className="hidden sm:inline">{lang === 'en' ? 'বাং' : 'EN'}</span>
            </button>

            {/* Auth Buttons — desktop */}
            <div className="hidden md:flex items-center gap-2">
              {user ? (
                <>
                  <span className="px-4 py-2 rounded-lg text-sm font-medium text-white/90 bg-white/10">
                    {t('nav.hello')}, {user.user_name}
                  </span>
                  <button
                    onClick={signOut}
                    className="px-4 py-2 text-sm font-semibold text-atlas-700 bg-white rounded-xl hover:bg-atlas-100 transition-all shadow-md hover:shadow-lg"
                  >
                    {t('nav.logout')}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="px-4 py-2 text-sm font-medium text-atlas-200 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
                  >
                    {t('nav.login')}
                  </Link>
                  <Link
                    to="/signup"
                    className="px-4 py-2 text-sm font-semibold text-atlas-700 bg-white rounded-xl hover:bg-atlas-100 transition-all shadow-md hover:shadow-lg"
                  >
                    {t('nav.signup')}
                  </Link>
                </>
              )}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg text-atlas-200 hover:bg-white/10 transition-colors"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 bg-atlas-700 animate-fade-in">
          <div className="px-4 py-3 space-y-1">
            <Link
              to="/"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 hover:text-white transition-colors"
            >
              {t('nav.home')}
            </Link>
            <Link
              to="/courses"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 hover:text-white transition-colors"
            >
              {t('nav.courses')}
            </Link>
            <hr className="my-2 border-white/10" />
            {user ? (
              <>
                <span className="block px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 bg-white/10">
                  {t('nav.hello')}, {user.user_name}
                </span>
                <button
                  onClick={() => {
                    signOut();
                    setMobileOpen(false);
                  }}
                  className="w-full text-left px-4 py-3 rounded-xl text-sm font-semibold text-atlas-700 bg-white"
                >
                  {t('nav.logout')}
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="block w-full text-left px-4 py-3 rounded-xl text-sm font-medium text-atlas-200 hover:bg-white/10 transition-colors"
                >
                  {t('nav.login')}
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileOpen(false)}
                  className="block w-full px-4 py-3 text-sm font-semibold text-atlas-700 bg-white rounded-xl"
                >
                  {t('nav.signup')}
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
