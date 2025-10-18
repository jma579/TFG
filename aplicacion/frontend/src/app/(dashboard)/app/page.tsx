import { DashboardQuickActions } from '@/components/dashboard/quick-actions';
/*
import { DashboardStatusHorarios } from '@/components/dashboard/status-horarios';
import { DashboardStatusFichas } from '@/components/dashboard/status-fichas';
import { DashboardActivity } from '@/components/dashboard/activity';
import { DashboardNextStep } from '@/components/dashboard/next-step';
*/

type AppState = 'noData' | 'extractionPending' | 'extractionReady' | 'confirmed' | 'conflictsOpen';
const APP_STATE: AppState = 'noData';

export default function DashboardHomePage() {
  // ya no necesitamos canGoHorario
  const canGoConflictos =
    APP_STATE === 'confirmed' || APP_STATE === 'conflictsOpen';

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <DashboardQuickActions
        canGoConflictos={canGoConflictos}
      />
    </div>
  );
}
