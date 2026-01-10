import { api } from '@/lib/api/config';
import { ScheduleSummary } from '@/components/schedules/data';

// DTO para los filtros (opcional, pero buena práctica)
export type DashboardFiltros = {
  programa_id?: number;
  curso?: number;
};

// Obtener el resumen (lista de tarjetas)
export async function getDashboardResumen(params?: DashboardFiltros): Promise<ScheduleSummary[]> {
  // axios serializa automáticamente el objeto params a query string
  return api.get('/v0/docencia/dashboard/resumen', { params });
}