'use client';

import { create } from 'zustand';
import type { UploadItem } from '@/components/uploads/types';
import { uid } from '@/lib/id';
import { extractHorario, type HorarioTemporalOut } from '@/lib/api/docencia/horarios';

export type HorarioUploadItem = UploadItem & {
  progress: number;
  confirmed?: boolean;
  backendId?: number;
  horarioTemporal?: HorarioTemporalOut;
};

type State = {
  items: HorarioUploadItem[];
};

type Actions = {
  addFiles: (files: File[]) => void;
  remove: (id: string) => void;
 
  startAnalyze: () => Promise<void>;
  setProgress: (id: string, value: number) => void;
  setDone: (id: string) => void;
  setError: (id: string, msg: string) => void;
 
  confirm: (id: string) => void;
  updateHorario: (id: string, data: HorarioTemporalOut) => void;
  
  clear: () => void;
};

export const useHorariosUploadsStore = create<State & Actions>((set, get) => ({
  items: [],

  addFiles: (files) => {
    if (!files?.length) return;

    const newItems: HorarioUploadItem[] = files.map((file) => ({
      id: uid('horario-upload'),
      file,
      status: 'pending',
      result: undefined,
      errorMessage: undefined,
      progress: 0,
      confirmed: false,
      backendId: undefined,
      horarioTemporal: undefined,
    }));

    set((state) => ({
      items: [...state.items, ...newItems],
    }));
  },

  remove: (id) =>
    set((state) => ({
      items: state.items.filter((i) => i.id !== id),
    })),

  startAnalyze: async () => {
    const { items } = get();

    for (const item of items) {
      if (item.status !== 'pending') continue;

      const id = item.id;

      set((state) => ({
        items: state.items.map((i) =>
          i.id === id
            ? { ...i, status: 'uploading', progress: 0, errorMessage: undefined }
            : i,
        ),
      }));

      try {
        // 1. Llamada API (Ya devuelve HorarioTemporalOut directamente)
        const result = await extractHorario(item.file);

        // 2. Validación de seguridad básica
        if (!result || !result.horarios) {
            throw new Error("La respuesta del servidor no contiene tablas de horarios.");
        }

        // 3. Asignación directa (Eliminamos la lógica de normalización antigua)
        set((state) => ({
          items: state.items.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: 'done',
                  progress: 100,
                  errorMessage: undefined,
                  horarioTemporal: result, // <--- DIRECTO
                }
              : i,
          ),
        }));
      } catch (error: unknown) {
        console.error("Error en análisis:", error);
        const message =
          error instanceof Error
            ? error.message
            : 'Error al procesar el horario.';

        set((state) => ({
          items: state.items.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: 'error',
                  progress: 0,
                  errorMessage: message,
                }
              : i,
          ),
        }));
      }
    }
  },

  setProgress: (id, value) =>
    set((state) => ({
      items: state.items.map((i) =>
        i.id === id ? { ...i, progress: value } : i
      ),
    })),

  setDone: (id) =>
    set((state) => ({
      items: state.items.map((i) =>
        i.id === id ? { ...i, status: 'done', progress: 100 } : i
      ),
    })),

  setError: (id, msg) =>
    set((state) => ({
      items: state.items.map((i) =>
        i.id === id ? { ...i, status: 'error', errorMessage: msg } : i
      ),
    })),

  confirm: (id) =>
    set((state) => ({
      items: state.items.map((i) =>
        i.id === id ? { ...i, confirmed: true } : i
      ),
    })),

  updateHorario: (id, data) => 
    set((state) => ({
      items: state.items.map((i) => 
        i.id === id ? { ...i, horarioTemporal: data } : i
      )
    })),

  clear: () => set({ items: [] }),
}));