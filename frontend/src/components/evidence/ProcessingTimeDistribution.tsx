import React, { useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import type { EvidenceRow } from '../../types/evidence';

interface ProcessingTimeDistributionProps {
  rows: EvidenceRow[];
}

const BIN_SIZE = 5; // minutes
const MAX_BINS = 20;

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

interface BinData {
  label: string;
  before: number;
  after: number;
}

export const ProcessingTimeDistribution: React.FC<ProcessingTimeDistributionProps> = ({ rows }) => {
  const { binData, medianBefore, medianAfter } = useMemo(() => {
    const beforeValues: number[] = [];
    const afterValues: number[] = [];

    for (const row of rows) {
      const before = typeof row.processing_time_before === 'number' ? row.processing_time_before : Number(row.processing_time_before);
      const after = typeof row.processing_time_after === 'number' ? row.processing_time_after : Number(row.processing_time_after);
      if (Number.isFinite(before)) beforeValues.push(before);
      if (Number.isFinite(after)) afterValues.push(after);
    }

    if (beforeValues.length === 0 && afterValues.length === 0) {
      return { binData: [], medianBefore: null, medianAfter: null };
    }

    const allValues = [...beforeValues, ...afterValues];
    const minVal = Math.floor(Math.min(...allValues) / BIN_SIZE) * BIN_SIZE;
    const maxVal = Math.ceil(Math.max(...allValues) / BIN_SIZE) * BIN_SIZE;

    const numBins = Math.min(MAX_BINS, Math.ceil((maxVal - minVal) / BIN_SIZE));
    const bins: BinData[] = Array.from({ length: numBins }, (_, i) => ({
      label: `${minVal + i * BIN_SIZE}–${minVal + (i + 1) * BIN_SIZE}`,
      before: 0,
      after: 0,
    }));

    for (const v of beforeValues) {
      const idx = Math.min(Math.floor((v - minVal) / BIN_SIZE), numBins - 1);
      if (idx >= 0 && idx < numBins) bins[idx].before++;
    }
    for (const v of afterValues) {
      const idx = Math.min(Math.floor((v - minVal) / BIN_SIZE), numBins - 1);
      if (idx >= 0 && idx < numBins) bins[idx].after++;
    }

    return {
      binData: bins,
      medianBefore: median(beforeValues),
      medianAfter: median(afterValues),
    };
  }, [rows]);

  if (binData.length === 0) {
    return (
      <div className='flex h-36 items-center justify-center text-xs text-muted'>
        Load a dataset to see the processing time distribution.
      </div>
    );
  }

  // Find bin labels for median reference lines
  function binForValue(val: number | null): string | null {
    if (val === null || binData.length === 0) return null;
    // Find the label of the bin that contains val
    for (const bin of binData) {
      const [lo, hi] = bin.label.split('–').map(Number);
      if (val >= lo && val < hi) return bin.label;
    }
    return binData[binData.length - 1].label;
  }

  const medBeforeLabel = binForValue(medianBefore);
  const medAfterLabel = binForValue(medianAfter);

  return (
    <div>
      <p className='text-[10px] text-muted mb-2 font-medium uppercase tracking-wide'>
        Processing Time Distribution (min)
      </p>
      <ResponsiveContainer width='100%' height={180}>
        <ComposedChart data={binData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray='3 3' stroke='rgba(255,255,255,0.06)' />
          <XAxis
            dataKey='label'
            tick={{ fontSize: 9, fill: 'rgb(var(--muted))' }}
            tickLine={false}
            axisLine={false}
            interval='preserveStartEnd'
          />
          <YAxis
            tick={{ fontSize: 9, fill: 'rgb(var(--muted))' }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{ fontSize: '11px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}
            labelStyle={{ color: 'rgb(var(--text))', fontWeight: 600 }}
          />
          <Legend wrapperStyle={{ fontSize: '10px', color: 'rgb(var(--muted))' }} iconSize={8} />
          <Bar dataKey='before' name='Before' fill='rgb(var(--primary))' opacity={0.6} radius={[2, 2, 0, 0]} isAnimationActive animationDuration={600} />
          <Bar dataKey='after'  name='After'  fill='rgb(var(--success))' opacity={0.6} radius={[2, 2, 0, 0]} isAnimationActive animationDuration={600} />
          {medBeforeLabel && (
            <ReferenceLine
              x={medBeforeLabel}
              stroke='rgb(var(--primary))'
              strokeDasharray='4 3'
              strokeWidth={1.5}
              label={{ value: `Med↑ ${medianBefore?.toFixed(1)}`, position: 'top', fontSize: 8, fill: 'rgb(var(--primary))' }}
            />
          )}
          {medAfterLabel && (
            <ReferenceLine
              x={medAfterLabel}
              stroke='rgb(var(--success))'
              strokeDasharray='4 3'
              strokeWidth={1.5}
              label={{ value: `Med↓ ${medianAfter?.toFixed(1)}`, position: 'top', fontSize: 8, fill: 'rgb(var(--success))' }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
