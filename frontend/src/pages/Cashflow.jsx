import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, ReferenceLine, Tooltip } from "recharts";
import { ShieldAlert } from "lucide-react";

export default function Cashflow() {
  const [d, setD] = useState(null);
  useEffect(() => { (async () => setD((await api.get("/cashflow/predict")).data))(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Cashflow Prediction</h1>
        <p className="text-[var(--ink-soft)] mt-1">Where your money's headed over the next 30 days.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-5">
          <div className="text-xs text-[var(--ink-soft)]">Avg daily spend</div>
          <div className="text-3xl font-bold mt-1">₹{Math.round(d?.avg_daily_spend ?? 0).toLocaleString('en-IN')}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-[var(--ink-soft)]">30-day burn</div>
          <div className="text-3xl font-bold mt-1">₹{Math.round((d?.avg_daily_spend ?? 0) * 30).toLocaleString('en-IN')}</div>
        </div>
        <div className={`card p-5 ${d?.warnings?.length ? 'nudge-red' : 'nudge-green'}`}>
          <div className="text-xs text-[var(--ink-soft)]">Alerts</div>
          <div className="text-lg font-semibold mt-1">{d?.warnings?.length || 0}</div>
          {d?.warnings?.[0] && <div className="text-sm mt-2 flex items-center gap-1"><ShieldAlert size={14}/> {d.warnings[0].message}</div>}
        </div>
      </div>

      <div className="card p-6" data-testid="cashflow-chart">
        <div className="text-lg font-semibold mb-2">Balance projection</div>
        <div className="h-72">
          <ResponsiveContainer>
            <AreaChart data={d?.forecast ?? []}>
              <defs>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F97316" stopOpacity={0.5}/>
                  <stop offset="100%" stopColor="#F97316" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="day"/>
              <YAxis/>
              <Tooltip formatter={(v)=>`₹${Math.round(v).toLocaleString('en-IN')}`} labelFormatter={(l)=>`Day ${l}`}/>
              {d?.warnings?.map(w => (
                <ReferenceLine key={w.day} x={w.day} stroke="#F43F5E" strokeDasharray="3 3" label={{ value: '⚠', position:'top', fill: '#F43F5E' }}/>
              ))}
              <Area type="monotone" dataKey="balance" stroke="#F97316" strokeWidth={2.5} fill="url(#g2)"/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
