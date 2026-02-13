'use client';

import * as React from 'react';

import { cn } from '@/lib/cn';

type Props = {
  onFiles: (files: File[]) => void;
  accept?: string; 
};

export function DropzoneHorarios({ onFiles, accept = 'application/pdf' }: Props) {
  const [over, setOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setOver(false);
    const files = Array.from(e.dataTransfer.files).filter(f => !accept || f.type === accept);
    if (files.length) onFiles(files);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        'cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition',
        over ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:bg-muted/30'
      )}
      aria-label="Subir horarios (PDF) mediante arrastrar y soltar o pulsando"
    >
      <p className="text-sm">Arrastra aquí tus <b>horarios (PDF)</b> o haz clic para seleccionarlas</p>
      <p className="mt-1 text-xs text-muted-foreground">Formatos: PDF · Tamaño máx. sugerido: 20 MB</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        hidden
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length) onFiles(files);
        }}
      />
    </div>
  );
}
