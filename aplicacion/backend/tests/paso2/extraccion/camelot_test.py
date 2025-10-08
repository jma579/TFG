import camelot

# Cambia la ruta al PDF que quieres probar
pdf_path = r"C:\Users\usuario\TFG\Horarios\Grado\1C_DOBLE GRADO_v6.pdf"

# Prueba ambos flavors
for flavor in ["lattice", "stream"]:
    print(f"Probando flavor: {flavor}")
    tables = camelot.read_pdf(pdf_path, pages="all", flavor=flavor)
    print(f"Tablas detectadas ({flavor}): {len(tables)}")
    for i, table in enumerate(tables):
        # Guarda cada tabla como CSV
        csv_path = f"tabla_{flavor}_{i+1}.csv"
        table.to_csv(csv_path)
        print(f"Tabla {i+1} guardada en {csv_path}")
        # También puedes guardar como TXT para inspección rápida
        txt_path = f"tabla_{flavor}_{i+1}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(table.df.to_string(index=False))
        print(f"Tabla {i+1} guardada en {txt_path}")