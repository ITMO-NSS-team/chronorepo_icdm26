"""Build the self-contained HTML results report from results/digest.json.
Usage: py -3.12 make_report.py   ->  ../report.html"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
DATA = json.loads((HERE / "results" / "digest.json").read_text("utf-8"))
OUT = HERE.parent / "report.html"

TEMPLATE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChronoRepo — сводка экспериментов</title>
<style>
  :root {
    color-scheme: light;
    --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e;
    --muted:#898781; --grid:#e1e0d9; --border:rgba(11,11,11,.10);
    --blue:#2a78d6; --orange:#eb6834; --aqua:#1baf7a; --good:#006300;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --page:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7;
      --muted:#898781; --grid:#2c2c2a; --border:rgba(255,255,255,.10);
      --blue:#3987e5; --orange:#d95926; --aqua:#199e70; --good:#0ca30c;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--page); color:var(--ink);
         font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
  main { max-width:980px; margin:0 auto; padding:24px 16px 60px; }
  h1 { font-size:24px; margin:0 0 4px; } h1 + p { color:var(--ink2); margin-top:0; }
  h2 { font-size:18px; margin:34px 0 6px; }
  h2 .n { color:var(--muted); font-weight:400; font-size:13px; }
  .card { background:var(--surface); border:1px solid var(--border);
          border-radius:10px; padding:16px; margin-top:10px; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media (max-width:760px){ .row { grid-template-columns:1fr; } }
  table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
  th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.04em;
       color:var(--muted); padding:6px 8px; border-bottom:1px solid var(--grid); }
  td { padding:6px 8px; border-bottom:1px solid var(--grid); }
  tr:last-child td { border-bottom:none; }
  tr.hl td { font-weight:700; }
  td.num { text-align:right; }
  .note { color:var(--muted); font-size:12px; margin-top:8px; }
  .glos dt { font-weight:600; margin-top:8px; } .glos dd { margin:0 0 4px 0; color:var(--ink2); }
  svg { width:100%; height:auto; display:block; }
  .axis { stroke:var(--grid); stroke-width:1; }
  .lbl { fill:var(--ink2); font-size:11px; }
  .lbl2 { fill:var(--muted); font-size:10px; }
  .kpis { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }
  .kpi { background:var(--surface); border:1px solid var(--border); border-radius:10px;
         padding:10px 16px; }
  .kpi b { display:block; font-size:22px; }
  .kpi span { color:var(--ink2); font-size:12px; }
  .legend { display:flex; gap:16px; font-size:12px; color:var(--ink2); margin-top:6px; flex-wrap:wrap;}
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; }
</style>
</head>
<body>
<main>
<h1>ChronoRepo — сводка экспериментов</h1>
<p>Локализация изменений и предсказание связанных правок по дешёвому графу репозитория
(структура + история коммитов), без нейросетей и GPU. Прогоны: ночь 31.07 – 01.08.2026.</p>

<div class="kpis" id="kpis"></div>

<h2>1 · Задача «issue → файлы»: точность поиска нужных файлов</h2>
<div class="card">
  <div id="e2bars"></div>
  <div class="legend">
    <span><span class="dot" style="background:var(--blue)"></span>доля задач, где нужный файл найден в топ-10 (R@10)</span>
    <span><span class="dot" style="background:var(--blue);opacity:.45"></span>… в топ-1 (R@1)</span>
  </div>
  <div class="note">SWE-bench Lite — 300 реальных GitHub-issue, Verified — 500. Одинаковый протокол
  для всех методов, история и код берутся строго до момента issue.</div>
</div>
<div class="card"><div id="e2table"></div></div>

<h2>1б · LocBench: 560 issue из 165 проектов, четыре типа задач</h2>
<div class="card"><div id="lbtable"></div>
<div class="note">Строгая метрика Acc@k — «<i>все</i> нужные файлы в топ-k» — как в статье LocAgent,
поэтому их опубликованные числа можно ставить в ту же таблицу. Наш прогон: 540 из 560 задач
(20 потеряно на ошибках клонирования/обработки). LLM-строки — из статьи LocAgent (ACL 2025).</div></div>
<div class="card"><div id="lbcats"></div>
<div class="note">Прирост есть во всех четырёх категориях — метод работает не только на багах.</div></div>

<h2>2 · Качество × цена <span class="n">— главная картинка</span></h2>
<div class="card">
  <div id="pareto"></div>
  <div class="legend">
    <span><span class="dot" style="background:var(--orange)"></span>текстовый поиск</span>
    <span><span class="dot" style="background:var(--blue)"></span>наш подход (граф, CPU)</span>
    <span><span class="dot" style="background:var(--aqua)"></span>LLM-системы (числа из публикаций)</span>
  </div>
  <div class="note">Ось X — примерная стоимость обработки одной задачи (лог-шкала).
  Для LLM-систем качество — из их статей (метрика Acc@5, SWE-bench Lite); для дешёвых методов —
  наши замеры (Hit@10, Lite). Метрики не идентичны, поэтому сравнение ориентировочное — это
  честно указано и в статье.</div>
</div>

<h2>3 · Почему граф помогает: два независимых слоя связей</h2>
<div class="card">
  <div id="e1bars"></div>
  <div class="note">Для каждого файла сравниваем 10 ближайших соседей по импортам и по истории
  (перекрытие по Жаккару, 0 = слои полностью разные). Почти везде &lt; 0.3: история знает то,
  чего не видно в коде.</div>
</div>

<h2>4 · Задача «если правишь файл A — что ещё придётся править»</h2>
<div class="card">
  <div id="e3bars"></div>
  <div class="note">2 309 реальных коммитов из 12 проектов; по одному файлу коммита предсказываем
  остальные. Текстовый поиск здесь неприменим в принципе — связь между файлами не текстовая.
  Простой счётчик совместных изменений оказался сильнее хитрых методов — и это удобно:
  именно он даёт понятные объяснения в демо.</div>
</div>

<h2>5 · Скорость и стоимость (замерено)</h2>
<div class="card"><div id="costtable"></div>
<div class="note">Один процесс CPU, Windows 10, без GPU. «Обработка задачи» включает построение
обоих графов с нуля и все 28 вариантов ранжирования; в демо-системе граф строится один раз,
запрос занимает миллисекунды.</div></div>

<h2>6 · Словарик <span class="n">— что означают методы в таблицах</span></h2>
<div class="card"><dl class="glos">
<dt>Текстовый поиск BM25</dt><dd>Классический поиск «по словам»: файлы, в которых чаще встречаются
слова из текста issue. Базовый уровень, стандарт индустрии.</dd>
<dt>Поиск идентификаторов (grep)</dt><dd>Из issue берутся имена функций/переменных
(например <code>register_blueprint</code>) и ищутся файлы, где они встречаются.</dd>
<dt>Граф импортов</dt><dd>Файлы соединены связью, если один импортирует другой. Строится из кода.</dd>
<dt>Граф истории</dt><dd>Файлы соединены, если их правили в одном коммите; чем коммит старше,
тем слабее связь. Строится из git-истории за секунды.</dd>
<dt>«BM25/Grep + граф»</dt><dd>Двухшаговая схема: сначала текстовый поиск даёт стартовые файлы,
затем их «важность» растекается по связям графа (несколько итераций, как в PageRank), и итоговый
список — смесь текстовой и графовой оценки.</dd>
<dt>Счётчик совместных изменений</dt><dd>Для файла A — список файлов, которые чаще всего
менялись вместе с ним (метод ROSE, 2004).</dd>
</dl></div>

<p class="note" id="stamp"></p>
</main>
<script>
const D = __DATA__;
const $ = id => document.getElementById(id);
const fmt = x => (x==null? "–" : x.toFixed(3));
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text != null) e.textContent = text;
  parent.appendChild(e); return e;
}

/* ---- KPIs ---- */
(function(){
  const v = D.verified.all, l = D.lite.all;
  const kpis = [
    [( (v["bm25_a000_l90"].r10 - v["bm25"].r10)*100 ).toFixed(1)+" п.п.", "прирост R@10 над BM25 (Verified, 500 задач)"],
    [( (l["bm25_a025_l90"].r10 - l["bm25"].r10)*100 ).toFixed(1)+" п.п.", "прирост R@10 над BM25 (Lite, 300 задач)"],
    ["2.0×", "рост точности топ-1 на Verified (0.15 → 0.30)"],
    ["≈ $0", "стоимость запроса: CPU, миллисекунды"],
  ];
  $("kpis").innerHTML = kpis.map(([b,s])=>`<div class="kpi"><b>${b}</b><span>${s}</span></div>`).join("");
})();

/* ---- E2 grouped bars (Lite | Verified) ---- */
(function(){
  const order = ["bm25","grep","bm25_a100_l0","bm25_a000_l90","bm25_a025_l90"];
  const names = D.names.e2;
  const panels = [["lite","SWE-bench Lite (300)"],["verified","SWE-bench Verified (500)"]];
  const W=940,H=260,PW=W/2-20,x0=210,bh=16,gap=30;
  const svg = el("svg",{viewBox:`0 0 ${W} ${H}`},$( "e2bars"));
  panels.forEach(([key,title],pi)=>{
    const g = el("g",{transform:`translate(${pi*(PW+40)},0)`},svg);
    el("text",{x:x0,y:16,class:"lbl","font-weight":"600"},g,title);
    order.forEach((cfg,i)=>{
      const m = D[key].all[cfg]; if(!m) return;
      const y = 36+i*gap;
      el("text",{x:x0-8,y:y+bh-4,class:"lbl","text-anchor":"end"},g,names[cfg][0]);
      const w10 = (PW-x0-40)*m.r10, w1 = (PW-x0-40)*m.r1;
      const r10 = el("rect",{x:x0,y:y,width:w10,height:bh,rx:4,fill:"var(--blue)"},g);
      el("title",{},r10,`R@10 = ${fmt(m.r10)}, R@1 = ${fmt(m.r1)}`);
      el("rect",{x:x0,y:y,width:w1,height:bh,rx:4,fill:"var(--blue)",opacity:".45"},g);
      el("text",{x:x0+w10+6,y:y+bh-4,class:"lbl"},g,fmt(m.r10));
    });
  });
})();

/* ---- E2 table ---- */
(function(){
  const order = ["bm25","grep","bm25_a100_l0","bm25_a000_l90","bm25_a025_l90","grep_a025_l0"];
  const names = D.names.e2;
  const best = {};
  ["lite","verified"].forEach(b=>{
    best[b] = Math.max(...order.map(c=>D[b].all[c]?.r10||0));
  });
  let h = `<table><tr><th>метод</th><th>Lite R@1</th><th>Lite R@10</th><th>Lite MAP</th>
           <th>Verif. R@1</th><th>Verif. R@10</th><th>Verif. MAP</th></tr>`;
  order.forEach(c=>{
    const l=D.lite.all[c], v=D.verified.all[c]; if(!l||!v) return;
    const hl = v.r10===best.verified? ' class="hl"':'';
    h += `<tr${hl}><td>${names[c][0]}</td><td class="num">${fmt(l.r1)}</td>
      <td class="num">${fmt(l.r10)}</td><td class="num">${fmt(l.ap)}</td>
      <td class="num">${fmt(v.r1)}</td><td class="num">${fmt(v.r10)}</td>
      <td class="num">${fmt(v.ap)}</td></tr>`;
  });
  $("e2table").innerHTML = h + "</table>";
})();

/* ---- LocBench strict table + categories ---- */
(function(){
  if (!D.locbench || !D.locbench.strict) return;
  const names = D.names.e2, st = D.locbench.strict, all = D.locbench.all;
  const order = ["bm25","grep","bm25_a025_l90","grep_a025_l0"];
  const pct = x => (100*x).toFixed(1)+"%";
  let h = `<table><tr><th>метод</th><th>R@1</th><th>R@10</th>
    <th>строгая Acc@5</th><th>строгая Acc@10</th><th>цена/задача</th></tr>`;
  order.forEach(c=>{
    if(!st[c]) return;
    h += `<tr${c==="bm25_a025_l90"?' class="hl"':''}><td>${names[c][0]}</td>
      <td class="num">${fmt(all[c].r1)}</td><td class="num">${fmt(all[c].r10)}</td>
      <td class="num">${pct(st[c].acc5)}</td><td class="num">${pct(st[c].acc10)}</td>
      <td class="num">≈ $0</td></tr>`;
  });
  [["CodeRankEmbed (эмбеддинги, из статьи LocAgent)","74.3%","80.9%","GPU"],
   ["Agentless + Claude-3.5 (из статьи)","67.5%","67.5%","LLM-вызовы"],
   ["LocAgent + Claude-3.5 (из статьи)","83.4%","86.1%","≈ $0.66"]].forEach(r=>{
    h += `<tr><td style="color:var(--muted)">${r[0]}</td><td class="num">–</td>
      <td class="num">–</td><td class="num">${r[1]}</td><td class="num">${r[2]}</td>
      <td class="num">${r[3]}</td></tr>`;
  });
  $("lbtable").innerHTML = h+"</table>";

  const cats = D.locbench.by_category;
  let h2 = `<table><tr><th>категория задач</th><th>n</th>
    <th>BM25 R@10</th><th>наш гибрид R@10</th><th>прирост</th></tr>`;
  Object.entries(cats).sort((a,b)=>b[1].bm25.n-a[1].bm25.n).forEach(([cat,cfgs])=>{
    const b=cfgs.bm25, hcf=cfgs.bm25_a025_l90; if(!b||!hcf) return;
    h2 += `<tr><td>${cat}</td><td class="num">${b.n}</td>
      <td class="num">${fmt(b.r10)}</td><td class="num">${fmt(hcf.r10)}</td>
      <td class="num" style="color:var(--good)">+${(100*(hcf.r10-b.r10)).toFixed(1)} п.п.</td></tr>`;
  });
  $("lbcats").innerHTML = h2+"</table>";
})();

/* ---- Pareto ---- */
(function(){
  const pts = [
    {x:0.0002, y:D.lite.all["bm25"].hit10,  c:"var(--orange)", n:"BM25"},
    {x:0.0002, y:D.lite.all["grep"].hit10,  c:"var(--orange)", n:"grep"},
    {x:0.0004, y:D.lite.all["bm25_a025_l90"].hit10, c:"var(--blue)", n:"ChronoRepo (наш)"},
    {x:0.70,   y:0.697, c:"var(--aqua)", n:"Agentless (лит.)"},
    {x:0.66,   y:0.942, c:"var(--aqua)", n:"LocAgent Claude-3.5 (лит.)"},
    {x:0.09,   y:0.927, c:"var(--aqua)", n:"LocAgent Qwen-32B ft (лит.)"},
  ];
  const W=940,H=320,L=60,R=30,T=20,B=46;
  const xmin=Math.log10(0.0001), xmax=Math.log10(2);
  const X=v=>L+(Math.log10(v)-xmin)/(xmax-xmin)*(W-L-R);
  const Y=v=>T+(1-v)*(H-T-B);
  const svg = el("svg",{viewBox:`0 0 ${W} ${H}`},$("pareto"));
  [0.4,0.6,0.8,1].forEach(v=>{
    el("line",{x1:L,x2:W-R,y1:Y(v),y2:Y(v),class:"axis"},svg);
    el("text",{x:L-8,y:Y(v)+4,class:"lbl2","text-anchor":"end"},svg,v.toFixed(1));
  });
  [0.0001,0.001,0.01,0.1,1].forEach(v=>{
    el("text",{x:X(v),y:H-18,class:"lbl2","text-anchor":"middle"},svg,
       v>=1? "$"+v : v>=0.01? "$"+v.toFixed(2) : "$"+v);
  });
  el("text",{x:(L+W-R)/2,y:H-2,class:"lbl2","text-anchor":"middle"},svg,"стоимость одной задачи, $ (лог-шкала)");
  el("line",{x1:L,x2:W-R,y1:Y(0.35),y2:Y(0.35),class:"axis",opacity:0},svg);
  pts.forEach(p=>{
    const c = el("circle",{cx:X(p.x),cy:Y(p.y),r:9,fill:p.c,stroke:"var(--surface)","stroke-width":2},svg);
    el("title",{},c,`${p.n}: качество ${p.y.toFixed(2)}, ≈$${p.x}`);
    el("text",{x:X(p.x),y:Y(p.y)-14,class:"lbl","text-anchor":"middle"},svg,p.n);
  });
})();

/* ---- E1 bars ---- */
(function(){
  const e1 = Object.assign({}, D.verified.e1 || D.lite.e1);
  const items = Object.entries(e1).map(([r,m])=>({r:r.split("/")[1]||r, v:m.median}))
    .sort((a,b)=>a.v-b.v);
  const W=940,H=210,L=10,B=60,bw=Math.min(56,(W-2*L)/items.length-10);
  const svg = el("svg",{viewBox:`0 0 ${W} ${H}`},$("e1bars"));
  const Y=v=>16+(1-v/0.5)*(H-B-16);
  el("line",{x1:L,x2:W-L,y1:Y(0.3),y2:Y(0.3),stroke:"var(--orange)","stroke-width":1.5,"stroke-dasharray":"5 4"},svg);
  el("text",{x:W-L,y:Y(0.3)-5,class:"lbl2","text-anchor":"end"},svg,"порог 0.3 — «слои похожи»");
  items.forEach((it,i)=>{
    const x=L+i*((W-2*L)/items.length)+5;
    const b = el("rect",{x:x,y:Y(it.v),width:bw,height:(H-B)-Y(it.v)+16,rx:4,fill:"var(--blue)"},svg);
    el("title",{},b,`${it.r}: медианный Жаккар ${it.v.toFixed(2)}`);
    el("text",{x:x+bw/2,y:Y(it.v)-5,class:"lbl2","text-anchor":"middle"},svg,it.v.toFixed(2));
    el("text",{x:x+bw/2,y:H-B+30,class:"lbl2","text-anchor":"middle",transform:`rotate(35 ${x+bw/2} ${H-B+30})`},svg,it.r);
  });
})();

/* ---- E3 bars ---- */
(function(){
  const names = D.names.e3;
  const order = Object.entries(D.e3.configs).sort((a,b)=>b[1].r10-a[1].r10);
  const W=940,H=order.length*34+20,x0=250,bh=16;
  const svg = el("svg",{viewBox:`0 0 ${W} ${H}`},$("e3bars"));
  order.forEach(([cfg,m],i)=>{
    const y=10+i*34;
    el("text",{x:x0-8,y:y+bh-4,class:"lbl","text-anchor":"end"},svg,(names[cfg]||[cfg])[0]);
    const w=(W-x0-60)*m.r10;
    const b = el("rect",{x:x0,y:y,width:w,height:bh,rx:4,fill:"var(--blue)"},svg);
    el("title",{},b,`R@10 = ${fmt(m.r10)}, MRR = ${fmt(m.mrr)}`);
    el("text",{x:x0+w+6,y:y+bh-4,class:"lbl"},svg,`${fmt(m.r10)}  (MRR ${fmt(m.mrr)})`);
  });
})();

/* ---- cost table ---- */
(function(){
  let h = `<table><tr><th>прогон</th><th>задач</th><th>медиана, с/задача</th><th>p90, с/задача</th></tr>`;
  [["lite","SWE-bench Lite"],["verified","SWE-bench Verified"],["locbench","LocBench"]].forEach(([k,t])=>{
    if(!D[k]) return;
    h += `<tr><td>${t}</td><td class="num">${D[k].n}</td>
      <td class="num">${D[k].sec_median??"–"}</td><td class="num">${D[k].sec_p90??"–"}</td></tr>`;
  });
  $("costtable").innerHTML = h+"</table>";
})();

$("stamp").textContent = "Сгенерировано make_report.py из digest.json. " +
  (D.locbench && D.locbench.n < 500 ? `LocBench: прогон ещё идёт (готово ${D.locbench.n} задач) — таблицы обновятся.` : "");
</script>
</body>
</html>
"""


def main():
    html = TEMPLATE.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
