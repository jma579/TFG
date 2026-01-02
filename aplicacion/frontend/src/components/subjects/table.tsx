'use client';

import * as React from 'react';
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  FilterFn,
} from '@tanstack/react-table';
import {
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Search,
  ArrowUpDown,
  X
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { SubjectRow } from '@/components/subjects/data';
import { SubjectDetailView } from '@/components/subjects/subject-detail-view';
import type { ProgramaOut } from '@/lib/api/catalogo/programas';

// ------- Filtros personalizados -------

const multiColumnFilterFn: FilterFn<SubjectRow> = (row, columnId, filterValue) => {
  const searchValue = filterValue.toLowerCase();
  const nombre = row.original.nombre.toLowerCase();
  const codigo = row.original.codigo_plan.toLowerCase();
  return nombre.includes(searchValue) || codigo.includes(searchValue);
};

// ------- UI helpers -------

function PeriodBadge({ row }: { row: SubjectRow }) {
  const label =
    row.periodo === 'ANUAL'
      ? 'Anual'
      : row.periodo === 'primer_cuatrimestre'
      ? '1º Cuatri'
      : row.periodo === 'segundo_cuatrimestre'
      ? '2º Cuatri'
      : row.periodo;

  const variant = row.periodo === 'ANUAL' ? 'default' : 'outline';

  return (
    <Badge variant={variant} className="font-normal whitespace-nowrap">
      {label}
    </Badge>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${active ? 'bg-green-500' : 'bg-slate-300'}`} />
      <span className="text-sm text-muted-foreground">{active ? 'Activa' : 'Inactiva'}</span>
    </div>
  );
}

// ------- Tabla Principal -------

// 👇 TIPO CORREGIDO: Estructura estricta para onDataUpdate
export type SubjectsTableProps = {
  data: SubjectRow[];
  onEdit: (row: SubjectRow) => void;
  onDelete: (row: SubjectRow) => void;
  onDataUpdate: (
    id: string, 
    data: { 
      profesores: { nombre: string; apellidos: string }[]; 
      titulaciones: { titulacion: string; tipo_asignatura: string; curso: string }[] 
    }
  ) => void;
  titulacionesDisponibles?: ProgramaOut[];
};

export function SubjectsTable({ data, onEdit, onDelete, onDataUpdate, titulacionesDisponibles = [] }: SubjectsTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'codigo_plan', desc: false } // Orden inicial por código
  ]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([
    { id: 'activo', value: 'active' } // Filtro inicial: solo activas
  ]);
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState({});
  const [expanded, setExpanded] = React.useState({});
  const [globalFilter, setGlobalFilter] = React.useState('');

  const columns = React.useMemo<ColumnDef<SubjectRow>[]>(
    () => [
      {
        id: 'expander',
        header: () => null,
        cell: ({ row }) => {
          return (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 p-0"
              onClick={() => row.toggleExpanded()}
            >
              {row.getIsExpanded() ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          );
        },
      },
      {
        accessorKey: 'codigo_plan',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Código
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => (
          <span className="font-mono text-sm font-medium text-muted-foreground">
            {row.original.codigo_plan}
          </span>
        ),
      },
      {
        accessorKey: 'nombre',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Asignatura
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-medium">{row.original.nombre}</span>
            <span className="text-xs text-muted-foreground md:hidden">
              {row.original.codigo_plan}
            </span>
          </div>
        ),
        filterFn: multiColumnFilterFn,
      },
      {
        accessorKey: 'periodo',
        header: 'Periodo',
        cell: ({ row }) => <PeriodBadge row={row.original} />,
        filterFn: (row, id, value) => {
          return value === 'all' ? true : row.getValue(id) === value;
        },
      },
      {
        accessorKey: 'ects',
        header: 'ECTS',
        cell: ({ row }) => <span className="text-sm">{row.original.ects}</span>,
      },
      {
        accessorKey: 'modalidad',
        header: 'Modalidad',
        cell: ({ row }) => <span className="capitalize text-sm">{row.original.modalidad}</span>,
      },
      {
        id: 'contadores',
        header: 'Info',
        cell: ({ row }) => (
          <div className="flex gap-3 text-xs text-muted-foreground">
            <span title="Profesores asignados">
              Prof: <span className="font-medium text-foreground">{row.original.profesores?.length || row.original.num_profesores || 0}</span>
            </span>
            <span title="Titulaciones vinculadas">
              Tit: <span className="font-medium text-foreground">{row.original.titulaciones?.length || row.original.num_titulaciones || 0}</span>
            </span>
          </div>
        ),
      },
      {
        accessorKey: 'activo',
        header: 'Estado',
        cell: ({ row }) => <StatusBadge active={row.original.activo} />,
        filterFn: (row, id, value) => {
          if (value === 'all') return true;
          if (value === 'active') return row.original.activo === true;
          if (value === 'inactive') return row.original.activo === false;
          return true;
        },
      },
      {
        id: 'titulacionFilter',
        accessorFn: (row) => row.titulaciones?.map(t => t.titulacion).join(' '),
        header: 'Titulación',
        enableHiding: true,
        filterFn: (row, id, value) => {
          if (!value) return true;
          const titulaciones = row.original.titulaciones || [];
          return titulaciones.some(t => 
            t.titulacion.toLowerCase().includes(value.toLowerCase())
          );
        },
      },
      {
        id: 'actions',
        enableHiding: false,
        cell: ({ row }) => {
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 p-0">
                  <span className="sr-only">Abrir menú</span>
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                <DropdownMenuItem onClick={() => onEdit(row.original)}>
                  Editar asignatura
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete(row.original)}
                >
                  {row.original.activo ? 'Desactivar (Eliminar)' : 'Eliminar definitivamente'}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [onEdit, onDelete]
  );

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onExpandedChange: setExpanded,
    getRowCanExpand: () => true,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      expanded,
      globalFilter,
    },
  });

  React.useEffect(() => {
    table.getColumn('titulacionFilter')?.toggleVisibility(false);
  }, [table]);

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center">
          <div className="relative w-full md:max-w-xs">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar asignatura o código..."
              value={globalFilter ?? ''}
              onChange={(event) => setGlobalFilter(event.target.value)}
              className="pl-8 h-9"
            />
          </div>

          <Select
            value={(table.getColumn('periodo')?.getFilterValue() as string) ?? 'all'}
            onValueChange={(value) => table.getColumn('periodo')?.setFilterValue(value)}
          >
            <SelectTrigger className="h-9 w-full md:w-[180px]">
              <SelectValue placeholder="Periodo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los periodos</SelectItem>
              <SelectItem value="primer_cuatrimestre">1º Cuatrimestre</SelectItem>
              <SelectItem value="segundo_cuatrimestre">2º Cuatrimestre</SelectItem>
              <SelectItem value="ANUAL">Anual</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={(table.getColumn('activo')?.getFilterValue() as string) ?? 'active'}
            onValueChange={(value) => table.getColumn('activo')?.setFilterValue(value)}
          >
            <SelectTrigger className="h-9 w-full md:w-[150px]">
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activas</SelectItem>
              <SelectItem value="inactive">Inactivas</SelectItem>
            </SelectContent>
          </Select>

           <Select
            value={(table.getColumn('titulacionFilter')?.getFilterValue() as string) ?? 'all'}
            onValueChange={(value) => table.getColumn('titulacionFilter')?.setFilterValue(value === 'all' ? '' : value)}
          >
            <SelectTrigger className="h-9 w-full md:w-[200px]">
              <SelectValue placeholder="Filtrar titulación" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las titulaciones</SelectItem>
              {titulacionesDisponibles.map((prog) => (
                <SelectItem key={prog.id} value={prog.nombre}>
                  {prog.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {(globalFilter || columnFilters.length > 1) && (
            <Button
              variant="ghost"
              onClick={() => {
                setGlobalFilter('');
                setColumnFilters([{ id: 'activo', value: 'active' }]);
                table.resetSorting();
              }}
              className="h-9 px-2 lg:px-3"
            >
              Limpiar
              <X className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="rounded-md border h-[600px] overflow-auto relative">
        <table className="w-full caption-bottom text-sm">
          <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="bg-muted/50 hover:bg-muted/50">
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <React.Fragment key={row.id}>
                  <TableRow
                    data-state={row.getIsSelected() && 'selected'}
                    className={row.getIsExpanded() ? 'bg-muted/20 border-b-0' : ''}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                  {row.getIsExpanded() && (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="p-0">
                        <div className="p-4 bg-muted/10 border-t shadow-inner">
                           <SubjectDetailView 
                              asignaturaId={Number(row.original.id)} 
                              onDataLoaded={(data) => onDataUpdate(row.original.id, data)}
                           />
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  No se encontraron resultados.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </table>
      </div>
      
      <div className="flex items-center justify-end space-x-2 py-4">
        <div className="flex-1 text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} asignaturas.
        </div>
      </div>
    </div>
  );
}