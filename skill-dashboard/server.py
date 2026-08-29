#!/usr/bin/env python3
"""Media House · Skill Dashboard

★ 三條鐵律（沿用 mhl-studio／dpm-studio／sae-studio）：
   ① 打勾是宣稱，檔案是證據 —— 沒有「標記完成」按鈕。
      一支 skill 是 draft 還是 published，判定依據是它在 drafts/ 還是 skills/，
      不是有沒有人打勾。靠打勾推進的看板，三個月後會變成一面全綠但沒有人相信的牆。
   ② GitHub 是唯一事實來源 —— 本服務不寫入任何東西。
   ③ 每次請求重讀檔案 —— 畫面與 repo 不一致時，錯的一定是畫面。

無資料庫、無登入、無第三方依賴（Python 標準庫）。
"""
import json
import os
import re
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(os.environ.get("MEDIAHOUSE_ROOT", Path(__file__).resolve().parent.parent))
PORT = int(os.environ.get("PORT", "8080"))

CSS = """
:root{color-scheme:light;--s1:#fcfcfb;--s2:#f3f3f1;--tp:#0b0b0b;--ts:#52514e;
--tm:#7a7975;--bd:rgba(11,11,11,.10);--good:#0ca30c;--warn:#fab219;
--serious:#ec835a;--crit:#d03b3b;--goodtx:#006300}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--s1:#1a1a19;--s2:#232322;
--tp:#fff;--ts:#c3c2b7;--tm:#8f8e86;--bd:rgba(255,255,255,.10);--goodtx:#0ca30c}}
*{box-sizing:border-box}
body{margin:0;background:var(--s1);color:var(--tp);
font:14px/1.6 ui-sans-serif,-apple-system,"Noto Sans TC",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 72px}
h1{font-size:21px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:15px;margin:34px 0 12px;color:var(--tp)}
.sub{color:var(--ts);margin:0 0 22px;font-size:13px}
a{color:inherit}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px}
.tile{background:var(--s2);border:1px solid var(--bd);border-radius:10px;padding:13px 15px}
.tile .n{font-size:27px;font-weight:640;letter-spacing:-.02em;line-height:1.15}
.tile .l{color:var(--ts);font-size:12px;margin-top:2px}
.tile .h{color:var(--tm);font-size:11px;margin-top:5px;line-height:1.45}
.note{background:var(--s2);border:1px solid var(--bd);border-left:3px solid var(--warn);
border-radius:8px;padding:12px 15px;margin:16px 0;font-size:13px;color:var(--ts)}
.note b{color:var(--tp)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-weight:600;color:var(--ts);font-size:11.5px;
text-transform:uppercase;letter-spacing:.04em;padding:8px 9px;border-bottom:1px solid var(--bd)}
td{padding:8px 9px;border-bottom:1px solid var(--bd);vertical-align:top}
tr:hover td{background:var(--s2)}
.scroll{overflow-x:auto;border:1px solid var(--bd);border-radius:10px}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;
padding:1px 7px;border-radius:99px;border:1px solid var(--bd);white-space:nowrap}
.pub{color:var(--goodtx)}.dft{color:var(--serious)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.muted{color:var(--tm)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.bar input,.bar select{background:var(--s2);color:var(--tp);border:1px solid var(--bd);
border-radius:7px;padding:6px 9px;font:inherit;font-size:13px}
.bar input{min-width:230px}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--bd);
color:var(--tm);font-size:12px;line-height:1.7}
code{background:var(--s2);padding:1px 5px;border-radius:4px;font-size:12px}
.k{color:var(--ts)}
"""

JS = """
function flt(){
 const q=(document.getElementById('q').value||'').toLowerCase();
 const st=document.getElementById('st').value, ly=document.getElementById('ly').value;
 let n=0;
 document.querySelectorAll('#rows tr').forEach(r=>{
  const ok=(!q||r.dataset.s.includes(q))&&(!st||r.dataset.st===st)&&(!ly||r.dataset.ly===ly);
  r.style.display=ok?'':'none'; if(ok)n++;});
 document.getElementById('cnt').textContent=n;
}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def load():
    """每次請求重讀 —— 畫面與 repo 不一致時，錯的一定是畫面。"""
    reg = ROOT / "registry" / "skills.json"
    if not reg.exists():
        return None
    d = json.loads(reg.read_text(encoding="utf-8"))
    # ★ 交叉核對：registry 說的數字 vs 磁碟上真的有幾個檔案
    d["_disk"] = {
        "published": len(list((ROOT / "skills").glob("*/SKILL.md"))),
        "draft": len(list((ROOT / "drafts" / "skills").glob("*/SKILL.md"))),
    }
    return d


def page(title, body):
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">
{body}
<footer>
<b>打勾是宣稱，檔案是證據。</b> 本服務沒有「標記完成」按鈕 ——
一支 skill 是 draft 還是 published，判定依據是它在 <code>drafts/</code> 還是 <code>skills/</code>。<br>
<b>GitHub 是唯一事實來源。</b> 本服務不寫入任何東西，每次請求重讀檔案。<br>
資料來源 <code>registry/skills.json</code>（產物，由 <code>scripts/build_registry.py</code> 產生）
· <a href="/api/state">/api/state</a><br>
<b>上游方法論。</b> 這條產線是兌心科技影像方法論的下游 ——
盤點與方法論的接點寫在
<a href="https://research-board-production.up.railway.app/#mhskills" target="_blank" rel="noopener">Research 報告欄 REPORT 28</a>
（81 支全索引：<a href="https://research-board-production.up.railway.app/mediahouse-skills.html" target="_blank" rel="noopener">/mediahouse-skills.html</a>，
<b>該頁是有日期的死快照，本頁才是即時的</b>）。<br>
<b>技巧內容預設 E6（作者自述），我方未實測</b>，未經實測回填不得作為對外效果承諾依據。
</footer></div><script>{JS}</script></body></html>"""


def overview(d):
    s, disk = d["summary"], d["_disk"]
    drift = (s["published"] != disk["published"] or s["draft"] != disk["draft"])
    tiles = [
        (s["total"], "skill 總數", "published ＋ draft"),
        (s["published"], "已發布", "skills/ ——安裝 plugin 的人會拿到這些"),
        (s["draft"], "草稿", "drafts/ ——自動產出，<b>未經人工整理與實測</b>"),
        (s["billable"], "會扣額度", f"其餘 {s['total'] - s['billable']} 支不花錢"),
    ]
    t = "".join(f'<div class="tile"><div class="n">{n}</div><div class="l">{l}</div>'
                f'<div class="h">{h}</div></div>' for n, l, h in tiles)

    warn = ""
    if drift:
        warn = ('<div class="note" style="border-left-color:var(--crit)">'
                f'🔴 <b>registry 與磁碟不一致</b>：registry 說 published {s["published"]}／'
                f'draft {s["draft"]}，磁碟上是 {disk["published"]}／{disk["draft"]}。'
                '跑 <code>python3 scripts/build_registry.py</code>。'
                '<br>★ 這個檢查存在的理由：一份會過期而不自知的清單，比沒有清單更危險。</div>')

    cases = ""
    for c in d.get("cases", []):
        cc = c.get("counts", {})
        cases += (f'<tr><td class="mono">{esc(c["case"])}</td>'
                  f'<td>{esc(c.get("account"))}</td>'
                  f'<td>{cc.get("WORTH_SKILL", 0)}</td>'
                  f'<td>{cc.get("OPINION_ONLY", 0)}</td>'
                  f'<td>{cc.get("INSUFFICIENT_DATA", 0)}</td>'
                  f'<td class="mono muted">{esc(c.get("classifier_error_rate"))}</td></tr>')

    rows = ""
    for k in d["skills"]:
        pub = k["status"] == "published"
        badge = (f'<span class="badge {"pub" if pub else "dft"}">'
                 f'{"●" if pub else "◐"} {"已發布" if pub else "草稿"}</span>')
        tools = ", ".join(k["tools"]) or "—"
        rows += (f'<tr data-st="{esc(k["status"])}" data-ly="{esc(k["layer"])}" '
                 f'data-s="{esc((k["name"] + " " + (k["title"] or "") + " " + k["description"]).lower())}">'
                 f'<td>{badge}</td>'
                 f'<td><a class="mono" href="/s/{esc(k["name"])}">{esc(k["name"])}</a>'
                 f'<div class="muted">{esc((k["title"] or "")[:46])}</div></td>'
                 f'<td class="mono">{esc(k["layer"])}</td>'
                 f'<td class="mono">{esc(k["role"])}</td>'
                 f'<td>{"⚠️ 會扣" if k["billable"] else "—"}</td>'
                 f'<td class="mono muted">{esc(tools)}</td>'
                 f'<td class="mono muted">{esc(k["source_shortcode"] or "—")}</td></tr>')

    return page("Media House · Skill Dashboard", f"""
<h1>Media House · Skill Dashboard</h1>
<p class="sub">把社群技巧影片變成可執行的 SKILL.md。這裡管理它們的狀態與晉升。</p>
{warn}
<div class="tiles">{t}</div>

<div class="note">
<b>⚠️ 草稿不是 skill。</b> {s['draft']} 支草稿由規則從逐字稿自動萃取，
<b>沒有經過人整理、沒有經過實測</b>，全部 <code>verification = V0</code>。
它們待在 <code>drafts/</code> 而不是 <code>skills/</code>，是因為我方實測證明逐字稿在兩件事上系統性不可靠：
<b>專有名詞</b>（同一個工具名在兩支片裡有兩種錯法）與 <b>否定詞脫落</b>（句子讀起來完全通順但語意反轉）。
<b>晉升是人的動作，不是腳本的動作。</b>
</div>

<h2>案例分流</h2>
<div class="scroll"><table>
<thead><tr><th>Case</th><th>帳號</th><th>值得做</th><th>觀點片</th><th>沒拿到逐字稿</th><th>分類器錯誤率</th></tr></thead>
<tbody>{cases}</tbody></table></div>
<p class="sub" style="margin-top:8px">「沒拿到逐字稿」是 <b>我們沒拿到</b>，不是「這支沒有字幕」——
兩者在報表上長得一樣，意思相反。分類器錯誤率為 <code>UNMEASURED</code>：
沒有人工標註就只有「分佈」沒有「錯誤率」。</p>

<h2>Skill 清單（<span id="cnt">{s['total']}</span> / {s['total']}）</h2>
<div class="bar">
 <input id="q" placeholder="搜尋名稱、標題、說明…" oninput="flt()">
 <select id="st" onchange="flt()"><option value="">全部狀態</option>
  <option value="published">已發布</option><option value="draft">草稿</option></select>
 <select id="ly" onchange="flt()"><option value="">全部層級</option>
  {"".join(f'<option value="{esc(k)}">{esc(k)}</option>' for k in s["by_layer"])}</select>
</div>
<div class="scroll"><table>
<thead><tr><th>狀態</th><th>名稱</th><th>層</th><th>role</th><th>計費</th><th>閘道工具</th><th>來源</th></tr></thead>
<tbody id="rows">{rows}</tbody></table></div>
""")


def detail(d, name):
    k = next((x for x in d["skills"] if x["name"] == name), None)
    if not k:
        return None
    p = ROOT / k["path"]
    body = p.read_text(encoding="utf-8") if p.exists() else "（檔案不存在）"
    pub = k["status"] == "published"
    meta = "".join(
        f'<tr><td class="k">{a}</td><td class="mono">{esc(b)}</td></tr>' for a, b in [
            ("狀態", "published（skills/）" if pub else "draft（drafts/）"),
            ("層", k["layer"]), ("role", k["role"]),
            ("會扣額度", "是" if k["billable"] else "否"),
            ("閘道工具", ", ".join(k["tools"]) or "無"),
            ("來源 case", k["case"] or "—"),
            ("來源 shortcode", k["source_shortcode"] or "—"),
            ("檔案", k["path"]), ("行數", k["lines"]),
            ("有《紅線》章節", "是" if k["has_redline"] else "否"),
            ("有證據強度標記", "是" if k["has_evidence"] else "否"),
        ])
    promo = "" if pub else """
<div class="note"><b>晉升到 skills/ 前必須做的四件事：</b>
① 人工重讀逐字稿，確認步驟是真的、<b>且沒有否定詞脫落</b>
② 跑 <code>/video-ingest</code> 抽幀讀圖，把工具名從 E5 升到 E1
③ 補 <code>boundary</code> 與 <code>pitfalls</code>（坑必須來自證據）
④ 跑 <code>/skill-compile</code> 重寫，再 <code>/skill-audit</code>
<br><b>四件事沒做完，不得移進 skills/。</b></div>"""
    return page(f"{name} · Skill Dashboard", f"""
<p class="sub"><a href="/">← 回清單</a></p>
<h1>{esc(name)}</h1>
<p class="sub">{esc(k["title"] or "")}</p>
{promo}
<h2>Metadata</h2>
<div class="scroll"><table><tbody>{meta}</tbody></table></div>
<h2>SKILL.md 原文</h2>
<div class="scroll"><pre style="margin:0;padding:14px;white-space:pre-wrap;
font-family:ui-monospace,Menlo,monospace;font-size:12px;line-height:1.65">{esc(body)}</pre></div>
""")


class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, payload):
        b = payload.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/healthz":
            return self._send(200, "text/plain; charset=utf-8", "ok")
        d = load()
        if d is None:
            return self._send(503, "text/html; charset=utf-8", page("尚未建立 registry", """
<h1>registry 尚未建立</h1>
<div class="note">找不到 <code>registry/skills.json</code>。
跑 <code>python3 scripts/build_registry.py</code>。<br>
<b>⚠️ 這不是「沒有 skill」，是「還沒有清單可讀」——兩者在畫面上長得一樣。</b></div>"""))
        if path == "/api/state":
            return self._send(200, "application/json; charset=utf-8",
                              json.dumps(d, ensure_ascii=False, indent=2))
        if path.startswith("/s/"):
            h = detail(d, path[3:])
            if h is None:
                return self._send(404, "text/html; charset=utf-8",
                                  page("找不到", "<h1>404</h1><p class='sub'>"
                                       "<a href='/'>← 回清單</a></p>"))
            return self._send(200, "text/html; charset=utf-8", h)
        if path == "/":
            return self._send(200, "text/html; charset=utf-8", overview(d))
        return self._send(404, "text/html; charset=utf-8",
                          page("找不到", "<h1>404</h1><p class='sub'><a href='/'>← 回清單</a></p>"))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Skill Dashboard · root={ROOT} · port={PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
