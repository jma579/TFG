'use client';

import * as React from 'react';
import { Check, ChevronsUpDown, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';

export type AutocompleteOption = {
  value: string | number;
  label: string;
  keywords?: string;
};

interface SimpleAutocompleteProps {
  options: AutocompleteOption[];
  value?: string | number | null;
  onChange: (value: string | number) => void;
  placeholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  initialValue?: string; // Prop clave para mantener el texto original
}

export function SimpleAutocomplete({
  options,
  value,
  onChange,
  placeholder = 'Escriba para buscar...',
  emptyText = 'No hay resultados.',
  disabled = false,
  className,
  initialValue = '',
}: SimpleAutocompleteProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  // Iniciamos el input con el valor de la etiqueta encontrada O el valor inicial textual
  const [query, setQuery] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Sincronización robusta del estado
  React.useEffect(() => {
    const selected = options.find((opt) => String(opt.value) === String(value));
    if (selected) {
      setQuery(selected.label);
    } else if (!value && initialValue) {
      // Si no hay ID match, pero tenemos texto original, lo mostramos
      setQuery(initialValue);
    } else if (!value && !initialValue) {
      setQuery('');
    }
  }, [value, options, initialValue]);

  const filteredOptions = React.useMemo(() => {
    if (!query) return options;
    
    // Si el texto en el input es igual a la opción seleccionada, mostrar todas
    const selectedLabel = options.find(o => String(o.value) === String(value))?.label;
    if (query === selectedLabel) return options;
    
    // Si el texto es igual al valor inicial (no tocado), mostrar todas
    if (query === initialValue) return options;

    const lowerQuery = query.toLowerCase();
    return options.filter((opt) => 
      opt.label.toLowerCase().includes(lowerQuery) || 
      (opt.keywords && opt.keywords.toLowerCase().includes(lowerQuery))
    );
  }, [options, query, value, initialValue]);

  // Cerrar al hacer clic fuera
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (option: AutocompleteOption) => {
    setQuery(option.label);
    onChange(option.value);
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setQuery('');
    onChange('');
    setIsOpen(true);
  };

  return (
    <div className={cn("relative w-full", className)} ref={containerRef}>
      <div className="relative">
        <Input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className="pr-8"
        />
        <div className="absolute right-2 top-2.5 text-muted-foreground">
          {query && !disabled ? (
            <X className="h-4 w-4 cursor-pointer hover:text-foreground" onClick={handleClear} />
          ) : (
            <ChevronsUpDown className="h-4 w-4 opacity-50" />
          )}
        </div>
      </div>

      {isOpen && !disabled && (
        <div className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border bg-popover py-1 text-popover-foreground shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
          {filteredOptions.length === 0 ? (
            <div className="relative cursor-default select-none px-4 py-2 text-muted-foreground">
              {emptyText}
            </div>
          ) : (
            filteredOptions.map((option) => (
              <div
                key={option.value}
                className={cn(
                  "relative cursor-pointer select-none py-2 pl-3 pr-9 hover:bg-accent hover:text-accent-foreground",
                  String(value) === String(option.value) ? "bg-accent/50" : ""
                )}
                onClick={() => handleSelect(option)}
              >
                <div className="flex flex-col">
                  <span className="block truncate font-medium">{option.label}</span>
                  {option.keywords && (
                    <span className="block truncate text-xs text-muted-foreground opacity-70">
                      {option.keywords}
                    </span>
                  )}
                </div>
                {String(value) === String(option.value) && (
                  <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-primary">
                    <Check className="h-4 w-4" aria-hidden="true" />
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}