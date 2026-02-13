import { ScheduleSummary } from '@/components/schedules/data';
import { api } from '@/lib/api/config';

export type DashboardFiltros = {
  programa_id?: number;
  curso?: number;
};

export async function getDashboardResumen(params?: DashboardFiltros): Promise<ScheduleSummary[]> {
  return api.get('/v0/docencia/dashboard/resumen', { params });
}