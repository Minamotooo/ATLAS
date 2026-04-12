import { useLanguage } from '../context/LanguageContext';
import { Link } from 'react-router-dom';

export default function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="bg-atlas-900 text-atlas-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <img src="/logo.png" alt="ATLAS" className="h-9 w-auto brightness-0 invert" />
              <span className="font-display font-bold text-xl text-white">ATLAS</span>
            </div>
            <p className="text-sm text-atlas-300 leading-relaxed">
              {t('landing.footerAbout')}
            </p>
          </div>

          {/* Platform */}
          <div>
            <h4 className="font-semibold text-white mb-4 text-sm uppercase tracking-wider">
              {t('landing.footerPlatform')}
            </h4>
            <ul className="space-y-2.5">
              <li><Link to="/courses" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('nav.courses')}</Link></li>
              <li><a href="#features" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('landing.feature1Title')}</a></li>
              <li><a href="#features" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('landing.feature2Title')}</a></li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold text-white mb-4 text-sm uppercase tracking-wider">
              {t('landing.footerResources')}
            </h4>
            <ul className="space-y-2.5">
              <li><a href="#" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('nav.students')}</a></li>
              <li><a href="#" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('nav.teachers')}</a></li>
              <li><a href="#" className="text-sm text-atlas-300 hover:text-white transition-colors">{t('nav.institutions')}</a></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-white mb-4 text-sm uppercase tracking-wider">
              {t('landing.footerContact')}
            </h4>
            <ul className="space-y-2.5">
              <li><a href="mailto:hello@atlas.edu" className="text-sm text-atlas-300 hover:text-white transition-colors">hello@atlas.edu</a></li>
              <li><a href="#" className="text-sm text-atlas-300 hover:text-white transition-colors">Twitter / X</a></li>
              <li><a href="#" className="text-sm text-atlas-300 hover:text-white transition-colors">Facebook</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-atlas-800 text-center text-sm text-atlas-400">
          {t('landing.footerRights')}
        </div>
      </div>
    </footer>
  );
}
