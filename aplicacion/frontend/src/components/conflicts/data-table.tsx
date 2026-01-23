'use client';

import * as React from 'react';
import {
  Column, // <--- 1. IMPORTANTE: Añadir este import
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  useReactTable,
} from '@tanstack/react-table';

import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { 
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator 
} from '@/components/ui/command';
import { CheckIcon, PlusCircledIcon, Cross2Icon } from '@radix-ui/react-icons';
import { cn } from '@/lib/utils';
import { ConflictoOut, SesionResumen } from '@/lib/api/conflictos';
import { Clock, GraduationCap, Users } from 'lucide-react';

// --- COMPONENTES AUXILIARES ---

function SessionCard({ title, data, isConflictSource }: { title: string, data?: SesionResumen | null, isConflictSource?: boolean }) {
  if (!data) return null;

  return (
    <div className={cn(
      "p-3 rounded-md border text-sm flex flex-col gap-2",
      isConflictSource ? "bg-red-50 border-red-100" : "bg-white border-gray-100"
    )}>
      <div className="flex justify-between items-center mb-1">
        <span className="font-semibold text-xs text-muted-foreground uppercase tracking-wider">{title}</span>
        <Badge variant="outline" className="text-[10px] h-5 bg-white">ID: {data.id}</Badge>
      </div>
      
      <div className="font-medium text-base text-gray-900 leading-tight">
        {data.asignatura}
      </div>
      
      <div className="grid grid-cols-2 gap-2 mt-1">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock className="w-3.5 h-3.5" />
          <span>{data.horario}</span>
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Users className="w-3.5 h-3.5" />
          <span>{data.grupo}</span>
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground col-span-2">
          <GraduationCap className="w-3.5 h-3.5" />
          <span>Curso: {data.curso}</span>
        </div>
      </div>
    </div>
  );
}

function ExpandedConflictDetails({ conflicto }: { conflicto: ConflictoOut }) {
  const s1 = conflicto.sesion_1_detalle;
  const s2 = conflicto.sesion_2_detalle;

  return (
    <div className="p-4 bg-muted/30 rounded-md border border-muted/50 animate-in fade-in zoom-in-95 duration-200">
      {!s2 && (
        <div className="mb-4 p-3 border border-blue-100 bg-blue-50 text-blue-800 rounded-md text-sm">
          ℹ️ Este es un conflicto de normativa interna (ej: conciliación). Solo implica una sesión.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SessionCard 
          title="Sesión Existente" 
          data={s1} 
        />
        
        {s2 ? (
          <SessionCard 
            title="Sesión Entrante / Solapada" 
            data={s2} 
            isConflictSource 
          />
        ) : (
          <div className="flex items-center justify-center p-4 border border-dashed rounded-md bg-muted/20 text-muted-foreground text-sm italic">
            No hay segunda sesión implicada.
          </div>
        )}
      </div>
    </div>
  );
}

// --- FILTRO FACETADO CORREGIDO ---

interface DataTableFacetedFilterProps<TData, TValue> {
  // 2. CORRECCIÓN: Usamos el tipo genérico Column en lugar de 'any'
  column?: Column<TData, TValue>; 
  title: string;
  options: { label: string; value: string; icon?: React.ComponentType<{ className?: string }> }[];
}

function DataTableFacetedFilter<TData, TValue>({ column, title, options }: DataTableFacetedFilterProps<TData, TValue>) {
  const facets = column?.getFacetedUniqueValues();
  const selectedValues = new Set(column?.getFilterValue() as string[]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 border-dashed">
          <PlusCircledIcon className="mr-2 h-4 w-4" />
          {title}
          {selectedValues.size > 0 && (
            <>
              <Separator orientation="vertical" className="mx-2 h-4" />
              <Badge variant="secondary" className="rounded-sm px-1 font-normal lg:hidden">{selectedValues.size}</Badge>
              <div className="hidden space-x-1 lg:flex">
                {selectedValues.size > 2 ? (
                  <Badge variant="secondary" className="rounded-sm px-1 font-normal">{selectedValues.size} selected</Badge>
                ) : (
                  options.filter((option) => selectedValues.has(option.value)).map((option) => (
                    <Badge variant="secondary" key={option.value} className="rounded-sm px-1 font-normal">{option.label}</Badge>
                  ))
                )}
              </div>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selectedValues.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => {
                      if (isSelected) selectedValues.delete(option.value);
                      else selectedValues.add(option.value);
                      const filterValues = Array.from(selectedValues);
                      column?.setFilterValue(filterValues.length ? filterValues : undefined);
                    }}
                  >
                    <div className={cn("mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary", isSelected ? "bg-primary text-primary-foreground" : "opacity-50 [&_svg]:invisible")}>
                      <CheckIcon className={cn("h-4 w-4")} />
                    </div>
                    {option.icon && <option.icon className="mr-2 h-4 w-4 text-muted-foreground" />}
                    <span>{option.label}</span>
                    {facets?.get(option.value) && <span className="ml-auto flex h-4 w-4 items-center justify-center font-mono text-xs">{facets.get(option.value)}</span>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem onSelect={() => column?.setFilterValue(undefined)} className="justify-center text-center">Clear filters</CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// --- TABLA PRINCIPAL ---

type DataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  emptyText?: string;
};

export function DataTable<TData, TValue>({
  columns,
  data,
  emptyText = 'Sin conflictos.',
}: DataTableProps<TData, TValue>) {
  
  const [rowSelection, setRowSelection] = React.useState({});
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [expanded, setExpanded] = React.useState({});

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility, rowSelection, columnFilters, expanded },
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    getExpandedRowModel: getExpandedRowModel(),
  });

  const isFiltered = table.getState().columnFilters.length > 0;

  return (
    <div className="space-y-4">
      {/* TOOLBAR */}
      <div className="flex items-center justify-between">
        <div className="flex flex-1 items-center space-x-2">
          <Input
            placeholder="Buscar en descripción..."
            value={(table.getColumn("descripcion")?.getFilterValue() as string) ?? ""}
            onChange={(event) => table.getColumn("descripcion")?.setFilterValue(event.target.value)}
            className="h-8 w-[150px] lg:w-[250px]"
          />
          {table.getColumn("tipo") && (
            <DataTableFacetedFilter
              column={table.getColumn("tipo")}
              title="Tipo"
              options={[
                { label: "Solape Aula", value: "SOLAPAMIENTO_AULA" },
                { label: "Solape Profesor", value: "SOLAPAMIENTO_PROFESOR" },
                { label: "Grupo/Plan", value: "SOLAPAMIENTO_GRUPO" },
                { label: "Conciliación", value: "INTERFERENCIA_CONCILIACION" },
              ]}
            />
          )}
          {table.getColumn("severidad") && (
            <DataTableFacetedFilter
              column={table.getColumn("severidad")}
              title="Severidad"
              options={[
                { label: "Crítico", value: "CRITICA" },
                { label: "Error", value: "ERROR" },
                { label: "Warning", value: "WARNING" },
                { label: "Info", value: "INFO" },
              ]}
            />
          )}
          {isFiltered && (
            <Button variant="ghost" onClick={() => table.resetColumnFilters()} className="h-8 px-2 lg:px-3">
              Resetear <Cross2Icon className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* TABLE */}
      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} colSpan={header.colSpan}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext()) as React.ReactNode}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <React.Fragment key={row.id}>
                  <TableRow
                    data-state={row.getIsSelected() && "selected"}
                    className={row.getIsExpanded() ? "border-b-0 bg-muted/20" : ""}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext()) as React.ReactNode}
                      </TableCell>
                    ))}
                  </TableRow>
                  {row.getIsExpanded() && (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="p-0 border-t-0">
                         <ExpandedConflictDetails conflicto={row.original as ConflictoOut} />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  {emptyText}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      <div className="flex items-center justify-end space-x-2 py-2">
        <div className="text-xs text-muted-foreground">
          Mostrando {table.getFilteredRowModel().rows.length} conflictos
        </div>
      </div>
    </div>
  );
}