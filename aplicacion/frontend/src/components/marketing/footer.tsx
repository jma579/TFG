export function MarketingFooter() {
  return (
    <footer className="border-t bg-gradient-to-t from-background to-muted/20">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} Detector de Conflictos · TFG · Jose Martín Aramburu</p>
        <div className="flex items-center gap-4">{/* enlaces opcionales */}</div>
      </div>
    </footer>
  );
}
