"""
render.py —— 稿件管理页（从数据库读所有稿件，攒历史、可筛选、可手动标记）

- 攒所有跑过的稿件，不覆盖
- 已发/未发 状态：自动发的自动标已发；手动发的可点按钮标记（存浏览器本地）
- 双击 dashboard.html 即可打开
"""
from __future__ import annotations

import html
import pathlib
import time

_CSS = """
:root{--bg:#f5f5f4;--card:#fff;--ink:#1c1c1a;--sub:#6b6a65;--line:#e6e4de;--green:#0f6e56;--amber:#9a5b00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:780px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:22px;font-weight:600;margin:0 0 4px}
.sub{color:var(--sub);font-size:14px;margin-bottom:18px}
.filters{display:flex;gap:8px;margin-bottom:22px;position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:5}
.fbtn{border:1px solid var(--line);background:#fff;color:var(--ink);font-size:14px;padding:6px 16px;border-radius:20px;cursor:pointer}
.fbtn.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:24px}
.cover{width:100%;display:block;aspect-ratio:16/9;object-fit:cover;background:#eceae4}
.nocover{width:100%;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;color:var(--sub);background:#eceae4;font-size:14px}
.pad{padding:18px 20px 20px}
.top{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.badge{font-size:12px;padding:3px 10px;border-radius:20px;font-weight:500}
.b-no{background:#fff4e5;color:var(--amber)}
.b-yes{background:#e7f5ee;color:var(--green)}
.title{font-size:19px;font-weight:600;margin:0;flex:1}
.content{white-space:pre-wrap;margin:12px 0 0;color:#2b2b28;max-height:200px;overflow:hidden;position:relative}
.content.open{max-height:none}
.more{color:var(--sub);font-size:13px;cursor:pointer;margin-top:6px;display:inline-block}
.tools{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:#fafaf8;color:var(--ink);font-size:13px;padding:5px 12px;border-radius:8px;cursor:pointer;text-decoration:none}
.btn:hover{border-color:#c9c7c0}
.btn.done{background:#e7f5ee;border-color:#8fd3b4;color:var(--green)}
.meta{margin-top:14px;padding-top:10px;border-top:1px dashed var(--line);color:var(--sub);font-size:12px}
.dup{background:#fff4e5;border:1px solid #f0c987;color:var(--amber);font-size:13px;padding:8px 12px;border-radius:8px;margin-bottom:10px}
"""

_JS = """
const OVR_KEY='tt_status_overrides';
function ovr(){try{return JSON.parse(localStorage.getItem(OVR_KEY)||'{}')}catch(e){return {}}}
function saveOvr(o){localStorage.setItem(OVR_KEY,JSON.stringify(o))}
function effStatus(card){const o=ovr();const t=card.dataset.title;return o[t]||card.dataset.status;}
function applyOverrides(){
  document.querySelectorAll('.card').forEach(c=>{
    const s=effStatus(c);
    const b=c.querySelector('.badge');
    b.textContent=s; b.className='badge '+(s==='已发'?'b-yes':'b-no');
    const btn=c.querySelector('.markbtn');
    btn.textContent=(s==='已发')?'标记为未发':'标记为已发';
    btn.classList.toggle('done', s==='已发');
  });
  applyFilter();
}
function toggleStatus(t){const o=ovr();const cards=[...document.querySelectorAll('.card')].filter(c=>c.dataset.title===t);
  const cur=cards[0]?effStatus(cards[0]):'未发';o[t]=(cur==='已发')?'未发':'已发';saveOvr(o);applyOverrides();}
let curFilter='全部';
function setFilter(f,btn){curFilter=f;document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');applyFilter();}
function applyFilter(){document.querySelectorAll('.card').forEach(c=>{
  const s=effStatus(c); c.style.display=(curFilter==='全部'||s===curFilter)?'':'none';});
  const vis=[...document.querySelectorAll('.card')].filter(c=>c.style.display!=='none').length;
  document.getElementById('viscount').textContent=vis;}
function copyText(id,btn){const el=document.getElementById(id);const ta=document.createElement('textarea');
  ta.value=el.getAttribute('data-copy');ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy')}catch(e){}document.body.removeChild(ta);
  const o=btn.textContent;btn.textContent='已复制';setTimeout(()=>btn.textContent=o,1200);}
function toggleMore(id,el){document.getElementById(id).classList.toggle('open');el.textContent=document.getElementById(id).classList.contains('open')?'收起':'展开全文';}
window.addEventListener('DOMContentLoaded',applyOverrides);
"""


def _card(i: int, a: dict) -> str:
    title = html.escape(a.get("title", ""))
    body = html.escape(a.get("body", ""))
    img = a.get("image")
    track = html.escape(a.get("track", "-"))
    source = html.escape(a.get("source", "-"))
    ts = html.escape(str(a.get("created_at", "-")))
    status = a.get("status", "未发")

    if img:
        cover = f'<img class="cover" src="{html.escape(img)}" alt="">'
        dl = f'<a class="btn" href="{html.escape(img)}" download>下载配图</a>'
    else:
        cover = '<div class="nocover">（无配图，可手动配）</div>'
        dl = ''

    return f"""
    <div class="card" data-title="{title}" data-status="{html.escape(status)}">
      {cover}
      <div class="pad">
        <div class="top">
          <span class="badge {'b-yes' if status=='已发' else 'b-no'}">{html.escape(status)}</span>
          <p class="title">{title}</p>
        </div>
        <div class="content" id="c{i}" data-copy="{body}">{body}</div>
        <span class="more" onclick="toggleMore('c{i}',this)">展开全文</span>
        <div class="tools">
          <button class="btn" onclick="copyText('c{i}',this)">复制正文</button>
          {dl}
          <button class="btn markbtn" onclick="toggleStatus('{title}')">标记为已发</button>
        </div>
        <div class="meta">赛道：{track} · 来源：{source} · 生成：{ts}</div>
      </div>
    </div>"""


def render_dashboard(articles: list[dict], out_path: str = "output/dashboard.html") -> str:
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    now = time.strftime("%Y-%m-%d %H:%M")
    total = len(articles)
    unsent = sum(1 for a in articles if a.get("status") != "已发")
    cards = "\n".join(_card(i, a) for i, a in enumerate(articles)) or \
        '<p style="color:#6b6a65">还没有稿件，先跑 python run_daily.py。</p>'
    doc = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>稿件管理台</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>稿件管理台</h1>
<div class="sub">更新于 {now} · 共 {total} 篇 · 未发 {unsent} 篇 · 当前显示 <b id="viscount">{total}</b> 篇</div>
<div class="filters">
  <button class="fbtn on" onclick="setFilter('全部',this)">全部</button>
  <button class="fbtn" onclick="setFilter('未发',this)">未发</button>
  <button class="fbtn" onclick="setFilter('已发',this)">已发</button>
</div>
{cards}
</div><script>{_JS}</script></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


# 兼容旧调用：render() 现在渲染完整管理台
def render(items=None, out_path: str = "output/dashboard.html") -> str:
    import store
    return render_dashboard(store.all_articles(), out_path)
