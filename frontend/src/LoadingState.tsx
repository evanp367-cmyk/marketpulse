type Props = { label: string };

export function ChartSkeleton({ label }: Props) {
  return <div className="chart-skeleton" role="status" aria-label={label}>
    <span className="sr-only">{label}</span>
    <div className="skeleton chart-skeleton-trace" aria-hidden="true" />
    <div className="skeleton chart-skeleton-volume" aria-hidden="true" />
  </div>;
}

export function MarketSkeleton({ label }: Props) {
  return <div className="market-skeleton" role="status" aria-label={label}>
    <span className="sr-only">{label}</span>
    {Array.from({ length: 5 }, (_, index) => <div className="market-skeleton-row" key={index} aria-hidden="true">
      <span className="skeleton" /><span className="skeleton" /><span className="skeleton" />
    </div>)}
  </div>;
}
