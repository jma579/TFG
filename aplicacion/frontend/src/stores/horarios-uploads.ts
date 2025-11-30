'use client';

import { create } from 'zustand';
import type { UploadItem } from '@/components/uploads/types';
import { uid } from '@/lib/id';
import { extractHorario, type HorarioTemporalOut } from '@/lib/api/client';

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
      // campos específicos de horarios
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

    // Pr++ocesamos en serie para simplificar
    for (const item of items) {
      if (item.status !== 'pending') continue;

      const id = item.id;

      // Marcamos como "subiendo/procesando"
      set((state) => ({
        items: state.items.map((i) =>
          i.id === id
            ? { ...i, status: 'uploading', progress: 0, errorMessage: undefined }
            : i,
        ),
      }));

      try {
        const result = await extractHorario(item.file);

        // 🔍 Normalizamos el nodo que realmente contiene el horario temporal.
        // Ajusta esta lista de claves si tu backend usa otro nombre.
        const maybeWrapped = result as unknown as {
          horario?: HorarioTemporalOut;
          horario_temporal?: HorarioTemporalOut;
        };

        const horarioNode: HorarioTemporalOut =
          maybeWrapped.horario ??
          maybeWrapped.horario_temporal ??
          (result as HorarioTemporalOut);

        // Para depurar, puedes ver en consola qué llega realmente:
        // eslint-disable-next-line no-console
        console.log('Resultado extractHorario:', result);
        // eslint-disable-next-line no-console
        console.log('Nodo horarioTemporal usado:', horarioNode);

        set((state) => ({
          items: state.items.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: 'done',
                  progress: 100,
                  errorMessage: undefined,
                  // Si quieres seguir guardando también el wrapper completo, puedes añadir otra propiedad
                  // rawResult: result,
                  horarioTemporal: horarioNode,
                }
              : i,
          ),
        }));
      } catch (error: unknown) {
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

  clear: () => set({ items: [] }),
}));
