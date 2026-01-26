'use client';

import * as React from 'react';
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import {
  ArrowUpDown,
  MoreHorizontal,
  Search,
  X
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableHead,
  TableHeader,
  TableRow,
  TableCell,
  TableBody,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { Professor } from './data';

type ProfessorsTableProps = {
  data: Professor[];
  onEdit: (row: Professor) => void;
};

export function ProfessorsTable({ data, onEdit }: ProfessorsTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'nombre', desc: false }
  ]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([
    { id: 'activo', value: 'active' }
  ]);
  const [globalFilter, setGlobalFilter] = React.useState('');

  const columns = React.useMemo<ColumnDef<Professor>[]>(
    () => [
      {
        accessorKey: 'nombre',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Nombre
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-medium">
              {row.original.nombre} {row.original.apellidos}
            </span>
          </div>
        ),
        filterFn: (row, id, value) => {
            const search = value.toLowerCase();
            const nombre = `${row.original.nombre} ${row.original.apellidos}`.toLowerCase();
            const depto = (row.original.departamento || '').toLowerCase();
            return nombre.includes(search) || depto.includes(search);
        }
      },
      {
        accessorKey: 'email',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Email
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => {
          const email = row.original.email;
          if (!email) return <span className="text-muted-foreground">—</span>;
          return (
            <a
              href={`mailto:${email}`}
              className="text-sm text-primary underline-offset-2 hover:underline"
            >
              {email}
            </a>
          );
        },
      },
      {
        accessorKey: 'departamento',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Departamento
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.departamento || <span className="text-muted-foreground">—</span>}
          </span>
        ),
      },
      // --- NUEVA COLUMNA: Conciliación ---
      {
        accessorKey: 'conciliacion',
        header: 'Conciliación',
        cell: ({ row }) => {
          const val = row.original.conciliacion;
          if (!val) return <span className="text-muted-foreground text-xs">—</span>;
          
          // FIX: Especificamos explícitamente que 'label' es un string
          // para poder asignarle valores como "Entrada Tardía" que no están en el tipo original.
          let label: string = val;
          let colorClass = "bg-slate-100 text-slate-700"; // Default

          if (val === 'entrada_tardia') {
            label = "Entrada Tardía";
            colorClass = "bg-indigo-50 text-indigo-700 border-indigo-200";
          } else if (val === 'salida_temprana') {
            label = "Salida Temprana";
            colorClass = "bg-rose-50 text-rose-700 border-rose-200";
          } else if (val === 'mixta') {
            label = "Mixta (±1h)";
            colorClass = "bg-violet-50 text-violet-700 border-violet-200";
          }

          return (
            <Badge variant="outline" className={`whitespace-nowrap ${colorClass}`}>
              {label}
            </Badge>
          );
        },
      },
      // -----------------------------------
      {
        accessorKey: 'activo',
        header: 'Estado',
        cell: ({ row }) => (
          row.original.activo ? (
            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
              Activo
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-slate-100 text-slate-600">
              Inactivo
            </Badge>
          )
        ),
        filterFn: (row, id, value) => {
          if (value === 'all') return true;
          if (value === 'active') return row.original.activo === true;
          if (value === 'inactive') return row.original.activo === false;
          return true;
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
                  Editar profesor
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [onEdit]
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
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
  });

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center">
          <div className="relative w-full md:max-w-xs">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre o departamento..."
              value={globalFilter ?? ''}
              onChange={(event) => setGlobalFilter(event.target.value)}
              className="pl-8 h-9"
            />
          </div>

          <Select
            value={(table.getColumn('activo')?.getFilterValue() as string) ?? 'active'}
            onValueChange={(value) => table.getColumn('activo')?.setFilterValue(value)}
          >
            <SelectTrigger className="h-9 w-full md:w-[150px]">
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="inactive">Inactivos</SelectItem>
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
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
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
          {table.getFilteredRowModel().rows.length} profesores.
        </div>
      </div>
    </div>
  );
}