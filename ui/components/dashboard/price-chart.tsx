'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function PriceChart() {
  const data = [
    { time: '12:00', value: 158400 },
    { time: '14:00', value: 162300 },
    { time: '16:00', value: 159800 },
    { time: '18:00', value: 168900 },
    { time: '20:00', value: 166200 },
    { time: '22:00', value: 172500 },
    { time: '00:00', value: 187456 },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1a9fff" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#1a9fff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" vertical={false} />
        <XAxis dataKey="time" stroke="#a0a0a0" style={{ fontSize: '12px' }} />
        <YAxis stroke="#a0a0a0" style={{ fontSize: '12px' }} />
        <Tooltip 
          contentStyle={{
            backgroundColor: '#0f0f0f',
            border: '1px solid #1a1a1a',
            borderRadius: '8px',
          }}
          formatter={(value: any) => `$${value.toLocaleString()}`}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#1a9fff"
          strokeWidth={2}
          dot={false}
          isAnimationActive={true}
          fillOpacity={1}
          fill="url(#colorValue)"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
