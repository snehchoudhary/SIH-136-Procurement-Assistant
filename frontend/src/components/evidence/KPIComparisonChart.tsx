import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import type { KPIResult } from '../../types/evidence';

interface KPIComparisonChartProps {
  kpiResults: KPIResult[];
}

function outcomeColor(outcome: KPIResult['outcome']): string {
  switch (outcome) {
    case 'passed':
      return 'rgb(var(--success))';
    case 'failed':
      return 'rgb(var(--danger))';
    case 'missing_evidence':
      return 'rgb(var(--muted))';
  }
}

interface TooltipPayload {
  name: string;
  value: number;
  color: string;
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className='rounded-xl border border-border bg-surface p-3 shadow-lg text-xs'>
      <p className='font-semibold text-text mb-1'>{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className='mb-0.5'>
          {entry.name}: {entry.value != null ? `${entry.value.toFixed(1)}%` : '—'}
        </p>
      ))}
    </div>
  );
};

export const KPIComparisonChart: React.FC<KPIComparisonChartProps> = ({ kpiResults }) => {
  const data = useMemo(
    () =>
      kpiResults.map((kpi) => ({
        name: kpi.kpi_label,
        Claimed: kpi.claimed_value,
        Recomputed: kpi.recomputed_value,
        threshold: kpi.threshold,
        outcome: kpi.outcome,
        unit: kpi.unit,
      })),
    [kpiResults]
  );

  if (kpiResults.length === 0) {
    return (
      <div className='flex h-40 items-center justify-center text-sm text-muted'>
        No KPI data available.
      </div>
    );
  }

  // Use the first threshold for the reference line (or max across all)
  const threshold = data.find((d) => d.threshold !== null)?.threshold ?? null;

  return (
    <ResponsiveContainer width='100%' height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }} barGap={4}>
        <CartesianGrid strokeDasharray='3 3' stroke='rgb(var(--border))' />
        <XAxis
          dataKey='name'
          tick={{ fontSize: 10, fill: 'rgb(var(--muted))' }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'rgb(var(--muted))' }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
          domain={[0, 100]}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '10px', color: 'rgb(var(--muted))' }}
          iconSize={10}
          iconType='circle'
        />
        <Bar
          dataKey='Claimed'
          fill='rgb(var(--primary))'
          radius={[3, 3, 0, 0]}
          isAnimationActive
          animationDuration={600}
          opacity={0.75}
        />
        <Bar
          dataKey='Recomputed'
          radius={[3, 3, 0, 0]}
          isAnimationActive
          animationDuration={600}
          // Color each result according to its validation outcome.
          shape={(props: unknown) => {
            const shapeProps = props as React.SVGProps<SVGRectElement> & { index?: number };
            const index = shapeProps.index ?? 0;
            return <rect {...shapeProps} fill={outcomeColor(data[index]?.outcome ?? 'missing_evidence')} />;
          }}
        />
        {threshold !== null && (
          <ReferenceLine
            y={threshold}
            stroke='rgb(var(--warning))'
            strokeDasharray='4 3'
            strokeWidth={1.5}
            label={{
              value: `Threshold ${threshold}%`,
              position: 'right',
              fontSize: 9,
              fill: 'rgb(var(--warning))',
            }}
          />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
};
