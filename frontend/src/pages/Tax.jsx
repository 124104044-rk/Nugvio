import { useState } from "react";
import { api } from "@/lib/api";
import { Calculator, Info } from "lucide-react";

export default function Tax() {
  const [income, setIncome] = useState(1200000);
  const [regime, setRegime] = useState("new");
  const [d80c, setD80c] = useState(150000);
  const [hra, setHra] = useState(120000);
  const [other, setOther] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const estimate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/tax/estimate", {
        annual_income: parseFloat(income), regime,
        deductions_80c: parseFloat(d80c), hra: parseFloat(hra), other_deductions: parseFloat(other),
      });
      setResult(data);
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold">Tax Assistant</h1>
        <p className="text-[var(--ink-soft)] mt-1">Old regime vs New regime — get an educational estimate in seconds.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <div className="card p-6" data-testid="tax-form">
          <div className="text-xs text-[var(--ink-soft)]">Annual income (₹)</div>
          <input data-testid="tax-income" className="input mt-1" type="number" value={income} onChange={e=>setIncome(e.target.value)}/>
          <div className="text-xs text-[var(--ink-soft)] mt-4">Regime you prefer to see first</div>
          <div className="flex gap-2 mt-1">
            <button onClick={()=>setRegime('new')} className={`pill-btn text-sm ${regime==='new'?'btn-primary':'btn-ghost'}`}>New</button>
            <button onClick={()=>setRegime('old')} className={`pill-btn text-sm ${regime==='old'?'btn-primary':'btn-ghost'}`}>Old</button>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div>
              <div className="text-xs text-[var(--ink-soft)]">80C (LIC, PPF, ELSS)</div>
              <input data-testid="tax-80c" className="input mt-1" type="number" value={d80c} onChange={e=>setD80c(e.target.value)}/>
            </div>
            <div>
              <div className="text-xs text-[var(--ink-soft)]">HRA claimed</div>
              <input data-testid="tax-hra" className="input mt-1" type="number" value={hra} onChange={e=>setHra(e.target.value)}/>
            </div>
            <div>
              <div className="text-xs text-[var(--ink-soft)]">Other deductions</div>
              <input data-testid="tax-other" className="input mt-1" type="number" value={other} onChange={e=>setOther(e.target.value)}/>
            </div>
          </div>
          <button data-testid="tax-estimate" onClick={estimate} disabled={busy} className="pill-btn btn-primary mt-5 inline-flex items-center gap-2">
            <Calculator size={16}/> {busy ? "Calculating…" : "Estimate tax"}
          </button>
          <div className="text-xs text-[var(--ink-soft)] mt-3 flex items-center gap-1"><Info size={12}/> Educational only. Not filed tax advice.</div>
        </div>

        <div className="card p-6" data-testid="tax-result">
          {!result && <div className="text-[var(--ink-soft)]">Punch in your numbers to see the comparison.</div>}
          {result && (
            <>
              <div className="text-xs text-[var(--ink-soft)]">Recommended for you</div>
              <div className="text-3xl font-bold uppercase" style={{color: result.recommended==='new' ? 'var(--blue)':'var(--orange)'}}>
                {result.recommended} regime
              </div>
              <div className="text-sm mt-1">You could save <b>₹{Math.round(result.savings).toLocaleString('en-IN')}</b> by choosing this regime.</div>
              <div className="grid grid-cols-2 gap-3 mt-5">
                <div className={`card p-4 ${result.recommended==='new'?'nudge-green':''}`}>
                  <div className="text-xs text-[var(--ink-soft)]">New regime tax</div>
                  <div className="text-2xl font-bold">₹{Math.round(result.new_regime_tax).toLocaleString('en-IN')}</div>
                </div>
                <div className={`card p-4 ${result.recommended==='old'?'nudge-green':''}`}>
                  <div className="text-xs text-[var(--ink-soft)]">Old regime tax</div>
                  <div className="text-2xl font-bold">₹{Math.round(result.old_regime_tax).toLocaleString('en-IN')}</div>
                </div>
              </div>
              <div className="mt-4 text-xs text-[var(--ink-soft)]">{result.note}</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
