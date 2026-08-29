import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Flame, Star, CheckCircle2, X } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function Learn() {
  const { refresh } = useAuth();
  const [data, setData] = useState({ lessons: [], total_xp: 0 });
  const [active, setActive] = useState(null); // lesson
  const [answer, setAnswer] = useState(null);
  const [phase, setPhase] = useState("read"); // read | quiz | done

  const load = async () => setData((await api.get("/lessons")).data);
  useEffect(() => { load(); }, []);

  const start = (l) => { setActive(l); setPhase("read"); setAnswer(null); };
  const submitQuiz = async () => {
    if (answer === null) return;
    const correct = active.quiz[0].answer === answer;
    const score = correct ? 100 : 40;
    try {
      const { data } = await api.post("/lessons/complete", { lesson_id: active.id, score });
      if (data.earned_points) toast.success(`+${data.earned_points} NugPoints`);
      else toast.info("Already completed");
    } catch {}
    setPhase("done");
    load(); refresh();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-4xl font-bold">Learn</h1>
          <p className="text-[var(--ink-soft)] mt-1">Bite-sized money lessons. Ace the quiz, earn NugPoints.</p>
        </div>
        <div className="flex gap-3">
          <div className="chip"><Star size={14} color="#F97316"/> <b>{data.total_xp}</b> XP</div>
          <div className="chip"><Flame size={14} color="#F43F5E"/> streak alive</div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {data.lessons.map((l, i) => (
          <div key={l.id} className="card p-5 animate-slide" style={{animationDelay:`${i*30}ms`}} data-testid={`lesson-card-${l.id}`}>
            <div className="flex items-center justify-between">
              <div className="chip">{l.minutes} min · {l.xp} XP</div>
              {l.completed && <span className="chip" style={{background:'#DCFCE7', color:'#166534', borderColor:'#BBF7D0'}}><CheckCircle2 size={12}/> Done</span>}
            </div>
            <div className="text-lg font-semibold mt-3">{l.title}</div>
            <div className="text-sm text-[var(--ink-soft)] mt-1 line-clamp-2">{l.body.slice(0, 90)}…</div>
            <button data-testid={`lesson-open-${l.id}`} onClick={()=>start(l)} className="pill-btn btn-ghost text-sm mt-4">{l.completed ? "Review" : "Start →"}</button>
          </div>
        ))}
      </div>

      {active && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={()=>setActive(null)}>
          <div className="card p-8 max-w-xl w-full bg-white" onClick={e=>e.stopPropagation()} data-testid="lesson-modal">
            <div className="flex items-center justify-between mb-4">
              <div className="chip">{active.minutes} min · {active.xp} XP</div>
              <button onClick={()=>setActive(null)} className="p-2 hover:bg-slate-100 rounded-full"><X size={18}/></button>
            </div>
            <h2 className="text-2xl font-bold">{active.title}</h2>

            {phase === "read" && (
              <>
                <p className="text-[var(--ink)] mt-3 leading-relaxed">{active.body}</p>
                <button data-testid="lesson-to-quiz" onClick={()=>setPhase("quiz")} className="pill-btn btn-primary mt-6">Take the quiz →</button>
              </>
            )}

            {phase === "quiz" && (
              <>
                <div className="text-lg font-semibold mt-3">{active.quiz[0].q}</div>
                <div className="space-y-2 mt-3">
                  {active.quiz[0].options.map((o, i) => (
                    <button key={i} onClick={()=>setAnswer(i)} className={`w-full text-left p-3 rounded-xl border ${answer===i ? 'border-[var(--blue)] bg-[#EFF6FF]' : 'border-[var(--border)] bg-white hover:bg-slate-50'}`} data-testid={`quiz-opt-${i}`}>
                      {o}
                    </button>
                  ))}
                </div>
                <button data-testid="quiz-submit" onClick={submitQuiz} className="pill-btn btn-orange mt-6">Submit</button>
              </>
            )}

            {phase === "done" && (
              <div className="text-center mt-4">
                <div className="text-5xl">🎉</div>
                <div className="text-xl font-bold mt-2">Lesson complete</div>
                <div className="text-sm text-[var(--ink-soft)] mt-1">NugPoints added to your wallet.</div>
                <button onClick={()=>setActive(null)} className="pill-btn btn-primary mt-6">Close</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
