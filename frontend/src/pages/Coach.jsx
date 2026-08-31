import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Send, Bot, User, Sparkles } from "lucide-react";

const SESSION_KEY = "nugvio_coach_session";

const STATIC_SUGGESTIONS = [
  "What's my biggest money problem right now?",
  "How's my financial health looking?",
  "What should I do first this month?",
];

export default function Coach() {
  const nav = useNavigate();
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sid] = useState(() => {
    let s = localStorage.getItem(SESSION_KEY);
    if (!s) { s = "s-" + Math.random().toString(36).slice(2, 10); localStorage.setItem(SESSION_KEY, s); }
    return s;
  });
  const scrollRef = useRef(null);
  const [suggestions, setSuggestions] = useState(STATIC_SUGGESTIONS);

  useEffect(() => { (async () => {
    try {
      const { data } = await api.get("/action-center");
      const dynamic = data.insights
        .filter(i => i.severity === "high" || i.severity === "medium")
        .slice(0, 3)
        .map(i => `Help me with this: ${i.title}`);
      if (dynamic.length) setSuggestions([...dynamic, ...STATIC_SUGGESTIONS.slice(0, 2)]);
    } catch {}
  })(); }, []);

  useEffect(() => { (async () => {
    const { data } = await api.get(`/coach/history?session_id=${sid}`);
    setMsgs(data);
  })(); }, [sid]);

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs, busy]);

  const send = async (textArg) => {
    const text = (textArg ?? input).trim();
    if (!text || busy) return;
    setInput("");
    setMsgs(m => [...m, { id: 'u'+Date.now(), role: 'user', text }]);
    setBusy(true);
    try {
      const { data } = await api.post("/coach/chat", { session_id: sid, text });
      setMsgs(m => [...m, { id: 'c'+Date.now(), role: 'coach', text: data.reply, actions: data.actions }]);
    } catch {
      setMsgs(m => [...m, { id: 'e'+Date.now(), role: 'coach', text: "Something went wrong. Please retry." }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-end justify-between shrink-0">
        <div>
          <h1 className="text-4xl font-bold">AI Coach</h1>
          <p className="text-[var(--ink-soft)] mt-1">A smart friend, on tap. No jargon. No hype.</p>
        </div>
        <div className="chip" data-testid="coach-context-chip" style={{ background: "#EFF6FF", borderColor: "#BFDBFE" }}>
          <Sparkles size={13} color="#2563EB" /> <span className="font-semibold text-[var(--blue)]">Sees your live numbers</span>
        </div>
      </div>

      <div ref={scrollRef} className="card flex-1 overflow-y-auto p-6 space-y-4" data-testid="coach-messages">
        {msgs.length === 0 && (
          <div className="text-center text-[var(--ink-soft)] py-10">
            <Bot size={40} className="mx-auto mb-3" color="#2563EB"/>
            <div className="font-hand text-2xl" style={{color:'var(--coral)'}}>ask me anything about money</div>
            <div className="text-xs text-[var(--ink-soft)] mt-1">I can see your budgets, debts, goals and investments — so I'll answer with your real numbers.</div>
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {suggestions.map((s,i) => (
                <button key={i} onClick={()=>send(s)} className="pill-btn btn-ghost text-sm" data-testid={`coach-suggestion-${i}`}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {msgs.map(m => (
          <div key={m.id} className={`flex gap-3 ${m.role==='user' ? 'justify-end' : ''}`}>
            {m.role==='coach' && <div className="p-2 h-9 w-9 rounded-full bg-slate-100 flex items-center justify-center"><Bot size={16} color="#2563EB"/></div>}
            <div className={`max-w-[70%] p-4 rounded-2xl ${m.role==='user' ? 'bg-[var(--ink)] text-white rounded-br-sm' : 'bg-slate-50 border-l-4 border-[var(--orange)] rounded-bl-sm'}`}>
              <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.text}</div>
              {m.role==='coach' && m.actions?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {m.actions.map((a, i) => (
                    <button key={i} data-testid={`coach-action-${i}`} onClick={()=>nav(a.route)} className="pill-btn btn-primary text-xs">
                      {a.label} →
                    </button>
                  ))}
                </div>
              )}
            </div>
            {m.role==='user' && <div className="p-2 h-9 w-9 rounded-full bg-slate-100 flex items-center justify-center"><User size={16}/></div>}
          </div>
        ))}
        {busy && <div className="text-sm text-[var(--ink-soft)] flex items-center gap-2"><Bot size={14}/> coach is thinking…</div>}
      </div>

      <form onSubmit={(e)=>{e.preventDefault(); send();}} className="card p-3 flex gap-2 shrink-0" data-testid="coach-form">
        <input data-testid="coach-input" className="input flex-1" placeholder="Ask about money…" value={input} onChange={e=>setInput(e.target.value)} />
        <button data-testid="coach-send" disabled={busy} className="pill-btn btn-primary flex items-center gap-2"><Send size={16}/> Send</button>
      </form>
    </div>
  );
}
