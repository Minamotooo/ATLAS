import { useLanguage } from '../context/LanguageContext';
import { Link } from 'react-router-dom';
import { Mail, Phone, ArrowUpRight } from 'lucide-react';

// Contact details as published in the ATLAS brochure.
const EMAIL = 'atlas.learning26@gmail.com';
const PHONE_DISPLAY = '+880 1715-097720';
const PHONE_HREF = 'tel:+8801715097720';

export default function Footer() {
  const { t } = useLanguage();

  const linkClass =
    'group inline-flex items-center gap-1.5 text-sm font-medium text-white/75 transition-colors hover:text-gold-300';

  return (
    <footer className="hero-band mt-0 rounded-t-[2.5rem]">
      <div className="container-wide py-14 sm:py-20">
        <div className="grid gap-10 md:grid-cols-12">
          {/* Brand */}
          <div className="md:col-span-5">
            <p className="font-display text-display-md font-bold leading-none">
              ATLAS<span className="text-gold-300">.</span>
            </p>
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-white/80">{t('landing.footerAbout')}</p>
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-gold-300">
              {t('landing.footerProject')}
            </p>
          </div>

          {/* Platform */}
          <nav aria-label={t('landing.footerPlatform')} className="md:col-span-2">
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.16em] text-white">{t('landing.footerPlatform')}</h2>
            <ul className="space-y-3">
              <li><Link to="/courses" className={linkClass}>{t('nav.courses')}</Link></li>
              <li><Link to="/signup" className={linkClass}>{t('nav.signup')}</Link></li>
              <li><Link to="/login" className={linkClass}>{t('nav.login')}</Link></li>
            </ul>
          </nav>

          {/* Explore (in-page) */}
          <nav aria-label={t('landing.footerResources')} className="md:col-span-2">
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.16em] text-white">{t('landing.footerResources')}</h2>
            <ul className="space-y-3">
              <li><a href="#story" className={linkClass}>{t('landing.storyEyebrow')}</a></li>
              <li><a href="#features" className={linkClass}>{t('landing.footerFeatures')}</a></li>
              <li><a href="#workflow" className={linkClass}>{t('landing.footerHow')}</a></li>
            </ul>
          </nav>

          {/* Contact */}
          <div className="md:col-span-3">
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.16em] text-white">{t('landing.footerContact')}</h2>
            <ul className="space-y-3">
              <li>
                <a href={`mailto:${EMAIL}`} className={`${linkClass} break-all`}>
                  <Mail size={15} aria-hidden="true" className="shrink-0" />
                  {EMAIL}
                  <ArrowUpRight size={14} aria-hidden="true" className="opacity-0 transition-opacity group-hover:opacity-100" />
                </a>
              </li>
              <li>
                <a href={PHONE_HREF} className={linkClass}>
                  <Phone size={15} aria-hidden="true" className="shrink-0" />
                  {PHONE_DISPLAY}
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-2 border-t border-white/15 pt-6 text-sm text-white/65 sm:flex-row sm:items-center sm:justify-between">
          <span>{t('landing.footerRights')}</span>
          <span>Bangladesh University of Engineering and Technology</span>
        </div>
      </div>
    </footer>
  );
}
