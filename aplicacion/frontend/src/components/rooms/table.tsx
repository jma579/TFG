'use client';

import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from '@tanstack/react-table';
import {
  ArrowUpDown,
  MoreHorizontal,
  Pencil,
  Plus,
  Power,
  Search,
  Trash2} from 'lucide-react';
import * as React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import type { Room } from './data';

type RoomsTableProps = {
  data: Room[];
  onEdit: (room: Room) => void;
  onDelete: (room: Room) => void;
  onToggleActive: (room: Room) => void;
  onCreate: () => void;
};

export function RoomsTable({ data, onEdit, onDelete, onToggleActive, onCreate }: RoomsTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'codigo', desc: false }
  ]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = React.useState('');

  const tiposDisponibles = React.useMemo(() => {
    const set = new Set<string>();
    data.forEach((r) => {
      if (r.tipo) set.add(r.tipo);
    });
    return Array.from(set).sort();
  }, [data]);

  const columns = React.useMemo<ColumnDef<Room>[]>(
    () => [
      {
        accessorKey: 'codigo',
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
          <div className="font-mono font-medium">{row.getValue('codigo')}</div>
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
              Nombre
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => <div>{row.getValue('nombre')}</div>,
      },
      {
        accessorKey: 'activo',
        header: 'Estado',
        cell: ({ row }) => {
          const activo = row.getValue('activo') as boolean;
          return (
            <Badge variant={activo ? "default" : "secondary"} className={activo ? "bg-green-600 hover:bg-green-700" : ""}>
              {activo ? 'Activo' : 'Inactivo'}
            </Badge>
          );
        },
      },
      {
        accessorKey: 'tipo',
        header: 'Tipo',
        cell: ({ row }) => (
          <Badge variant="outline" className="font-normal">
            {row.getValue('tipo')}
          </Badge>
        ),
      },
      {
        accessorKey: 'capacidad',
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
              className="-ml-4"
            >
              Capacidad
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          );
        },
        cell: ({ row }) => {
          const cap = row.getValue('capacidad') as number | null;
          return <div className="font-medium">{cap ?? '—'}</div>;
        },
      },
      {
        id: 'actions',
        enableHiding: false,
        cell: ({ row }) => {
          const room = row.original;
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
                
                <DropdownMenuItem onClick={() => onEdit(room)}>
                  <Pencil className="mr-2 h-4 w-4" /> Editar
                </DropdownMenuItem>
                
                <DropdownMenuItem onClick={() => onToggleActive(room)}>
                  <Power className="mr-2 h-4 w-4" />
                  {room.activo ? 'Desactivar' : 'Activar'}
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete(room)}
                >
                  <Trash2 className="mr-2 h-4 w-4" /> Eliminar (Físico)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [onEdit, onDelete, onToggleActive]
  );

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, columnId, filterValue) => {
      const search = filterValue.toLowerCase();
      const codigo = (row.getValue('codigo') as string).toLowerCase();
      const nombre = (row.getValue('nombre') as string).toLowerCase();
      const tipo = (row.getValue('tipo') as string).toLowerCase();
      return codigo.includes(search) || nombre.includes(search) || tipo.includes(search);
    },
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
          <div className="relative w-full md:max-w-sm">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar aulas..."
              value={globalFilter ?? ''}
              onChange={(event) => setGlobalFilter(event.target.value)}
              className="pl-8"
            />
          </div>
          
          <Select
            value={(table.getColumn('tipo')?.getFilterValue() as string) ?? 'all'}
            onValueChange={(value) =>
              table.getColumn('tipo')?.setFilterValue(value === 'all' ? undefined : value)
            }
          >
            <SelectTrigger className="w-full md:w-[180px]">
              <SelectValue placeholder="Tipo de aula" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los tipos</SelectItem>
              {tiposDisponibles.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" /> Nueva aula
        </Button>
      </div>

      <div className="rounded-md border">
        <div className="relative h-[600px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-background shadow-sm">
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
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
                    className={!row.original.activo ? 'opacity-60 bg-muted/50' : ''}
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
          </Table>
        </div>
      </div>
      <div className="flex items-center justify-end space-x-2 py-4">
        <div className="text-xs text-muted-foreground">
          Mostrando {table.getFilteredRowModel().rows.length} aulas
        </div>
      </div>
    </div>
  );
}