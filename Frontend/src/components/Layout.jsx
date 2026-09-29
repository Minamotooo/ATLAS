import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import MotionProvider from '../motion/MotionProvider';
import PageTransition from '../motion/PageTransition';
import CustomCursor from '../motion/CustomCursor';

function OutletFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <span className="h-10 w-10 animate-spin rounded-full border-4 border-atlas-100 border-t-atlas-600" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export default function Layout() {
  return (
    <MotionProvider>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[120] focus:rounded-full focus:bg-ink focus:px-5 focus:py-3 focus:font-semibold focus:text-white"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen flex-col">
        <Navbar />
        <main id="main" className="flex-1">
          <PageTransition>
            <Suspense fallback={<OutletFallback />}>
              <Outlet />
            </Suspense>
          </PageTransition>
        </main>
      </div>
      <div className="grain-overlay" aria-hidden="true" />
      <CustomCursor />
    </MotionProvider>
  );
}
