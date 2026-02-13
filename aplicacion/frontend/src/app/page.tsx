import type { Metadata } from 'next';

import { MarketingFeatures } from '@/components/marketing/features';
import { MarketingFooter } from '@/components/marketing/footer';
import { MarketingHeader } from '@/components/marketing/header';
import { MarketingHero } from '@/components/marketing/hero';

export const metadata: Metadata = {
  title: 'Detector de Conflictos — Inicio',
  description:
    'Sube fichas y horarios, confirma la extracción y resuelve conflictos de forma interactiva.',
};

export default function HomePage() {
  return (
    <>
      <MarketingHeader />
      <main>
        <MarketingHero />
        <MarketingFeatures />
      </main>
      <MarketingFooter />
    </>
  );
}
