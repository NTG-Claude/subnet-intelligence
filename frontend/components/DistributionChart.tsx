'use client'

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

interface Bucket {
  range_start: number
  count: number
}

function bucketLabel(start: number): string {
  return `${Math.round(start)}–${Math.round(start + 10)}`
}

export default function DistributionChart({ buckets }: { buckets: Bucket[] }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={buckets} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
        <XAxis
          dataKey="range_start"
          tickFormatter={bucketLabel}
          tick={{ fontSize: 11, fill: '#64748b' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
          labelFormatter={(v) => `Score ${bucketLabel(Number(v))}`}
          formatter={(v: number) => [`${v} subnets`, '']}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {buckets.map((b, i) => (
            <Cell
              key={i}
              fill={b.range_start >= 70 ? '#4ade80' : b.range_start >= 40 ? '#facc15' : '#f87171'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
