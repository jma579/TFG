'use client';

import * as React from 'react';
import {
  Column,
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
import { 
  Clock, 
  Users, 
  Building2, 
  BookOpen, 
  CalendarDays, 
  Bookmark,
  LucideIcon 
} from 'lucide-react';

// --- COMPONENTES VISUALES ---

function MetadataBadge({ icon: Icon, text }: { icon: LucideIcon, text?: string }) {
  if (!text) return null;
  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-medium border border-slate-200">
      <Icon className="w-3 h-3" />
      <span className="truncate max-w-[150px]" title={text}>{text}</span>
    </div>
  );
}

function SessionCard({ data, isConflictSource }: { data?: SesionResumen | null, isConflictSource?: boolean }) {
  if (!data) return null;

  return (
    <div className={cn(
      "p-4 rounded-lg border text-sm flex flex-col gap-3 transition-all hover:shadow-sm",
      isConflictSource 
        ? "bg-red-50/50 border-red-100 hover:border-red-200" 
        : "bg-white border-slate-200 hover:border-slate-300"
    )}>
      <div className="font-semibold text-base text-slate-900 leading-tight">
        {data.asignatura}
      </div>
      
      <div className="flex flex-wrap gap-2">
        <MetadataBadge icon={BookOpen} text={data.titulacion} />
        <MetadataBadge icon={CalendarDays} text={data.periodo} />
        <MetadataBadge icon={Bookmark} text={data.mencion} />
      </div>

      <Separator className={isConflictSource ? "bg-red-100" : "bg-slate-100"} />

      <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-slate-600">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-400" />
          <span className="font-medium text-slate-700">{data.horario}</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-slate-400" />
          <span title="Aula">{data.aula || "Sin aula"}</span>
        </div>

        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-slate-400" />
          <span title="Grupo">{data.grupo}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400 border px-1 rounded">CURSO</span>
          <span>{data.curso}</span>
        </div>
      </div>
    </div>
  );
}

function ExpandedConflictDetails({ conflicto }: { conflicto: ConflictoOut }) {
  const s1 = conflicto.sesion_1_detalle;
  const s2 = conflicto.sesion_2_detalle;

  return (
    <div className="p-4 bg-slate-50/50 border-t border-b border-slate-100 animate-in slide-in-from-top-2 duration-200">
      
      {!s2 ? (
        // CASO 1: Conflicto de una sola sesión
        <div className="max-w-2xl mx-auto">
           <SessionCard data={s1} />
        </div>
      ) : (
        // CASO 2: Conflicto entre dos sesiones
        // Se muestran en grid simple, SIN elementos intermedios
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <div className="flex flex-col gap-2">
            <SessionCard data={s1} />
          </div>

          <div className="flex flex-col gap-2">
            <SessionCard data={s2} isConflictSource />
          </div>
        </div>
      )}
    </div>
  );
}

// --- FILTRO FACETADO ---

interface DataTableFacetedFilterProps<TData, TValue> {
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