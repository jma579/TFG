'use client';

import { create } from 'zustand';
import type { UploadItem } from '@/components/uploads/types';
import { uid } from '@/lib/id';

export type HorarioUploadItem = UploadItem & {
  confirmed?: boolean; // marcado al confirmar horario tras la revisión
};

type State = {
  items: HorarioUploadItem[];
};

type Actions = {
  addFiles: (files: File[]) => void;
  remove: (id: string) => void;

  // Simulación de análisis
  startAnalyze: () => void;
  setProgress: (id: string, value: number) => void;
  setDone: (id: string) => void;
  setError: (id: string, msg: string) => void;

  confirm: (id: string) => void;
  clear: () => void;
};

export const useHorariosUploadsStore = create<State & Actions>((set, get) => ({
  items: [],

  addFiles: (files) =>
    set((s) => ({
      items: [
        ...s.items,
        ...files.map<HorarioUploadItem>((f) => ({
          id: uid('hor'),
          file: f,
          status: 'pending',
          progress: 0,
        })),
      ],
    })),

  remove: (id) => set((s) => ({ items: s.items.filter((i) => i.id !== id) })),

  startAnalyze: () => {
    const items = get().items;
    // set all to uploading
    set({
      items: items.map((i) =>
        i.status === 'pending' ? { ...i, status: 'uploading', progress: 5 } : i
      ),
    });

    const steps = 10;
    items.forEach((it) => {
      if (it.status !== 'pending') return;
      const totalMs = 2000 + Math.floor(Math.random() * 2000);

      for (let k = 1; k <= steps; k++) {
        setTimeout(() => {
          get().setProgress(it.id, Math.min(100, Math.round((k / steps) * 100)));
        }, (totalMs / steps) * k);
      }

      setTimeout(() => {
        // En este flujo, todos pasan a "Listo para revisión"
        get().setDone(it.id);
      }, totalMs + 60);
    });
  },

  setProgress: (id, value) =>
    set((s) => ({
      items: s.items.map((i) => (i.id === id ? { ...i, progress: value } : i)),
    })),

  setDone: (id) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, status: 'done', progress: 100 } : i
      ),
    })),

  setError: (id, msg) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, status: 'error', errorMessage: msg } : i
      ),
    })),

  confirm: (id) =>
    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, confirmed: true } : i
      ),
    })),

    clear: () => set({ items: [] }),
}));
