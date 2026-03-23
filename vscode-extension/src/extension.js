// ⚡ Charlie 2.0 — VS Code Extension
// RightsFrames Intelligence / cloydRightsFrames
'use strict';
const vscode = require('vscode');
const http   = require('http');
const https  = require('https');

let outputChannel, statusBarItem;

function getConfig() {
  const c = vscode.workspace.getConfiguration('charlie2');
  return {
    apiUrl:            c.get('apiUrl',            'http://10.99.0.1:8000'),
    provider:          c.get('provider',           'auto'),
    useConstitutional: c.get('useConstitutional',  true),
    useDebate:         c.get('useDebate',          false),
    useRag:            c.get('useRag',             true)
  };
}

function apiPost(path, body, ms = 90000) {
  const { apiUrl } = getConfig();
  const url = new URL(apiUrl + path);
  const lib = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req  = lib.request({
      hostname: url.hostname,
      port:     url.port || (url.protocol === 'https:' ? 443 : 80),
      path:     url.pathname,
      method:   'POST',
      headers:  {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(data)
      },
      timeout: ms
    }, res => {
      let b = '';
      res.on('data', c => b += c);
      res.on('end', () => {
        try { resolve(JSON.parse(b)); }
        catch { resolve({ response: b }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    req.write(data);
    req.end();
  });
}

function apiGet(path, ms = 8000) {
  const { apiUrl } = getConfig();
  const url = new URL(apiUrl + path);
  const lib = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const req = lib.get({
      hostname: url.hostname,
      port:     url.port || (url.protocol === 'https:' ? 443 : 80),
      path:     url.pathname,
      timeout:  ms
    }, res => {
      let b = '';
      res.on('data', c => b += c);
      res.on('end', () => {
        try { resolve(JSON.parse(b)); }
        catch { resolve({ raw: b }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
  });
}

async function ask(prompt, mode = 'rag') {
  const cfg = getConfig();
  let ep = '/ai/rag-chat';
  if (mode === 'constitutional' || cfg.useConstitutional)
    ep = '/ai/constitutional-chat';
  if (mode === 'debate' || cfg.useDebate)
    ep = '/ai/debate';
  try {
    const r = await apiPost(ep, { prompt, provider: cfg.provider });
    return {
      response:   r.response || r.final_response || 'No response',
      provider:   r.provider || 'unknown',
      verdict:    r.constitutional_verdict || r.debate_verdict || 'OK',
      violations: r.constitutional_violations || 0,
      seal:       r.sovereign_seal || r.debate_hash || ''
    };
  } catch(e) {
    return {
      response:  `Charlie 2.0 offline: ${e.message}`,
      provider:  'error',
      verdict:   'ERROR',
      violations: 0,
      seal:      ''
    };
  }
}

function setStatus(text, tip) {
  if (statusBarItem) {
    statusBarItem.text    = text;
    statusBarItem.tooltip = tip;
  }
}

async function checkHealth() {
  try {
    const h = await apiGet('/health', 3000);
    if (h.status === 'OK')
      setStatus('⚡ C2', `Charlie 2.0 ONLINE — ${h.memory || '--'}`);
    else
      setStatus('⚡ C2 ✗', 'Charlie 2.0 offline');
  } catch {
    setStatus('⚡ C2 ✗', 'Cannot connect to Charlie 2.0');
  }
}

function getSelection(editor) {
  if (!editor) return '';
  const s = editor.selection;
  return editor.document.getText(s.isEmpty ? undefined : s);
}

function showPanel(title, result) {
  const vc   = result.verdict || 'OK';
  const vcol = vc === 'APPROVED' ? '#3fb950'
             : vc === 'BLOCKED'  ? '#f85149'
             : '#e3b341';
  const p = vscode.window.createWebviewPanel(
    'charlie2', `⚡ ${title}`, vscode.ViewColumn.Beside, {});
  p.webview.html = `<!DOCTYPE html><html>
<head><meta charset="UTF-8"><style>
  body{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;
       padding:20px;line-height:1.7;}
  .hdr{background:#161b22;border:1px solid #30363d;border-radius:8px;
       padding:12px 16px;margin-bottom:16px;}
  .ttl{color:#00d4ff;font-weight:700;font-size:14px;margin-bottom:4px;}
  .meta{font-size:11px;color:#8b949e;font-family:monospace;}
  .resp{background:#161b22;border:1px solid #30363d;border-radius:8px;
        padding:16px;white-space:pre-wrap;font-size:13px;line-height:1.8;}
  .seal{background:#0d2010;border:1px solid #3fb95020;border-radius:6px;
        padding:8px 12px;font-size:10px;font-family:monospace;
        color:#3fb950;margin-top:12px;}
  .vrd{display:inline-block;padding:2px 8px;border-radius:10px;
       font-size:10px;font-weight:700;
       border:1px solid ${vcol};color:${vcol};}
</style></head><body>
<div class="hdr">
  <div class="ttl">⚡ Charlie 2.0 — ${title}</div>
  <div class="meta">
    Provider: ${result.provider} &nbsp;|&nbsp;
    <span class="vrd">${vc}</span>
    ${result.violations
      ? ` &nbsp;|&nbsp; ${result.violations} constitutional flags`
      : ''}
  </div>
</div>
<div class="resp">${result.response
  .replace(/&/g,'&amp;')
  .replace(/</g,'&lt;')
  .replace(/>/g,'&gt;')}</div>
${result.seal
  ? `<div class="seal">⚖️ Sovereign Seal: ${result.seal}</div>`
  : ''}
</body></html>`;
}

function getChatHtml() {
  const { apiUrl } = getConfig();
  return `<!DOCTYPE html><html>
<head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;
     height:100vh;display:flex;flex-direction:column;}
.hdr{background:#161b22;border-bottom:1px solid #30363d;
     padding:10px 14px;display:flex;align-items:center;gap:8px;}
.dot{width:7px;height:7px;border-radius:50%;background:#3fb950;
     animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.ttl{color:#00d4ff;font-size:12px;font-weight:700;}
.api{margin-left:auto;font-size:9px;color:#8b949e;}
.pvrow{display:flex;gap:4px;padding:6px 10px;background:#161b22;
       border-bottom:1px solid #30363d;overflow-x:auto;}
.pvrow::-webkit-scrollbar{display:none;}
.pv{padding:2px 8px;border-radius:10px;font-size:9px;
    border:1px solid #30363d;background:#21262d;color:#8b949e;
    cursor:pointer;white-space:nowrap;}
.pv.active,.pv:hover{border-color:#00d4ff;color:#00d4ff;}
.msgs{flex:1;overflow-y:auto;padding:12px;
      display:flex;flex-direction:column;gap:8px;}
.msgs::-webkit-scrollbar{width:3px;}
.msgs::-webkit-scrollbar-thumb{background:#30363d;border-radius:2px;}
.user{background:linear-gradient(135deg,#1a3a4a,#0d2233);
      padding:8px 12px;border-radius:10px 2px 10px 10px;
      font-size:12px;align-self:flex-end;max-width:80%;}
.ai{background:#161b22;border:1px solid #30363d;padding:8px 12px;
    border-radius:2px 10px 10px 10px;font-size:12px;
    align-self:flex-start;max-width:90%;white-space:pre-wrap;line-height:1.6;}
.meta{font-size:9px;color:#8b949e;margin-top:3px;font-family:monospace;}
.seal{background:#0d2010;border-radius:4px;padding:4px 8px;
      font-size:8px;color:#3fb950;font-family:monospace;margin-top:4px;}
.inrow{padding:10px;background:#161b22;
       border-top:1px solid #30363d;display:flex;gap:8px;}
.inwrap{flex:1;background:#21262d;border:1px solid #30363d;
        border-radius:8px;display:flex;transition:border-color .2s;}
.inwrap:focus-within{border-color:#00d4ff;}
textarea{background:none;border:none;outline:none;color:#e6edf3;
         font-size:13px;padding:8px 10px;width:100%;resize:none;
         font-family:inherit;max-height:80px;}
textarea::placeholder{color:#8b949e;}
button{width:36px;height:36px;border-radius:8px;background:#00d4ff;
       border:none;cursor:pointer;display:flex;
       align-items:center;justify-content:center;flex-shrink:0;}
button:disabled{opacity:.4;cursor:not-allowed;}
button svg{width:15px;height:15px;}
.cur{display:inline-block;width:2px;height:12px;background:#00d4ff;
     animation:b .7s infinite;vertical-align:middle;}
@keyframes b{0%,100%{opacity:1}50%{opacity:0}}
.empty{display:flex;flex-direction:column;align-items:center;
       justify-content:center;height:100%;gap:6px;color:#8b949e;}
</style></head><body>
<div class="hdr">
  <div class="dot"></div>
  <span class="ttl">⚡ CHARLIE 2.0</span>
  <span class="api">${apiUrl}</span>
</div>
<div class="pvrow">
  <div class="pv active" onclick="sp('auto',this)">⚡ Auto</div>
  <div class="pv" onclick="sp('ollama',this)">🧠 Ollama</div>
  <div class="pv" onclick="sp('anthropic',this)">◆ Claude</div>
  <div class="pv" onclick="sp('openai',this)">◎ GPT</div>
</div>
<div class="msgs" id="msgs">
  <div class="empty" id="empty">
    <div style="font-size:36px">⚡</div>
    <div style="font-size:11px;font-weight:700;color:#00d4ff">Charlie 2.0</div>
    <div style="font-size:9px">Sovereign AI · RightsFrames Intelligence</div>
    <div style="font-size:9px;font-family:monospace">
      Ctrl+Shift+A — ask about selection
    </div>
  </div>
</div>
<div class="inrow">
  <div class="inwrap">
    <textarea id="inp" placeholder="Ask Charlie 2.0..." rows="1"
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"
      oninput="this.style.height='auto';
               this.style.height=Math.min(this.scrollHeight,80)+'px'">
    </textarea>
  </div>
  <button id="sb" onclick="send()">
    <svg viewBox="0 0 24 24" fill="none" stroke="#000"
         stroke-width="2.5" stroke-linecap="round">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
    </svg>
  </button>
</div>
<script>
const vscode = acquireVsCodeApi();
let prov = 'auto', busy = false;
function sp(p, el) {
  prov = p;
  document.querySelectorAll('.pv').forEach(e => e.classList.remove('active'));
  el.classList.add('active');
}
function addMsg(role, text) {
  const empty = document.getElementById('empty');
  if (empty) empty.remove();
  const area = document.getElementById('msgs');
  const d    = document.createElement('div');
  d.className = role;
  if (role === 'ai') d.id = 'curai';
  const tn = document.createTextNode(text || '');
  d.appendChild(tn);
  area.appendChild(d);
  area.scrollTop = area.scrollHeight;
  return { div: d, tn };
}
function send() {
  if (busy) return;
  const inp = document.getElementById('inp');
  const p   = inp.value.trim();
  if (!p) return;
  inp.value = ''; inp.style.height = 'auto';
  busy = true;
  document.getElementById('sb').disabled = true;
  addMsg('user', p);
  const { div, tn } = addMsg('ai', '');
  const cur = document.createElement('span');
  cur.className = 'cur';
  div.appendChild(cur);
  window._tn  = tn;
  window._div = div;
  window._cur = cur;
  vscode.postMessage({ type: 'chat', prompt: p, provider: prov });
}
window.addEventListener('message', e => {
  const d = e.data;
  if (d.type === 'token' && window._tn) {
    window._tn.textContent += d.token;
    document.getElementById('msgs').scrollTop =
      document.getElementById('msgs').scrollHeight;
  }
  if (d.type === 'done') {
    if (window._cur) window._cur.remove();
    if (d.meta && window._div) {
      const m = document.createElement('div');
      m.className   = 'meta';
      m.textContent = d.meta;
      window._div.appendChild(m);
    }
    if (d.seal && window._div) {
      const s = document.createElement('div');
      s.className   = 'seal';
      s.textContent = '⚖️ ' + d.seal;
      window._div.appendChild(s);
    }
    busy = false;
    document.getElementById('sb').disabled = false;
  }
});
</script></body></html>`;
}

class ChatProvider {
  constructor(ctx) { this._ctx = ctx; }
  resolveWebviewView(view) {
    view.webview.options = { enableScripts: true };
    view.webview.html    = getChatHtml();
    view.webview.onDidReceiveMessage(async msg => {
      if (msg.type !== 'chat') return;
      setStatus('⚡ C2...', 'Thinking...');
      try {
        const r     = await ask(msg.prompt, 'rag');
        const words = r.response.split(' ');
        for (const w of words) {
          view.webview.postMessage({ type: 'token', token: w + ' ' });
          await new Promise(res => setTimeout(res, 20));
        }
        view.webview.postMessage({
          type: 'done',
          meta: `⚡ ${r.provider} · ${r.verdict}`,
          seal: r.seal ? r.seal.slice(0, 20) + '...' : ''
        });
        setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
      } catch(e) {
        view.webview.postMessage({ type: 'token', token: `Error: ${e.message}` });
        view.webview.postMessage({ type: 'done', meta: 'error' });
        setStatus('⚡ C2 ✗', 'Error');
      }
    });
  }
}

async function activate(context) {
  outputChannel = vscode.window.createOutputChannel('Charlie 2.0');

  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right, 100);
  statusBarItem.text    = '⚡ C2';
  statusBarItem.tooltip = 'Charlie 2.0 — Sovereign AI';
  statusBarItem.command = 'charlie2.openChat';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'charlie2.chatView', new ChatProvider(context)));

  const commands = [
    ['charlie2.askSelection', async () => {
      const ed  = vscode.window.activeTextEditor;
      const txt = getSelection(ed);
      const inp = await vscode.window.showInputBox({
        prompt: '⚡ Ask Charlie 2.0', placeHolder: 'Question...' });
      if (!inp) return;
      setStatus('⚡ C2...', 'Asking');
      const prompt = txt
        ? `${inp}\n\nCode:\n\`\`\`\n${txt}\n\`\`\``
        : inp;
      const r = await ask(prompt, 'rag');
      showPanel('Answer', r);
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.explainCode', async () => {
      const txt = getSelection(vscode.window.activeTextEditor);
      if (!txt) {
        vscode.window.showWarningMessage('Select code to explain');
        return;
      }
      setStatus('⚡ C2...', 'Explaining');
      const r = await ask(
        `Explain this code clearly:\n\`\`\`\n${txt}\n\`\`\``, 'rag');
      showPanel('Explanation', r);
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.fixCode', async () => {
      const ed  = vscode.window.activeTextEditor;
      const txt = getSelection(ed);
      if (!txt) {
        vscode.window.showWarningMessage('Select code to fix');
        return;
      }
      setStatus('⚡ C2...', 'Fixing');
      const r = await ask(
        `Fix bugs and improve. Return only corrected code:\n\`\`\`\n${txt}\n\`\`\``,
        'rag');
      const a = await vscode.window.showInformationMessage(
        `⚡ Fix ready (${r.provider})`, 'Apply', 'Show');
      if (a === 'Apply' && ed)
        ed.edit(eb => eb.replace(ed.selection, r.response));
      else if (a === 'Show')
        showPanel('Fixed Code', r);
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.generateCode', async () => {
      const desc = await vscode.window.showInputBox({
        prompt: '⚡ Describe code to generate',
        placeHolder: 'FastAPI endpoint with governance logging...' });
      if (!desc) return;
      const lang = vscode.window.activeTextEditor
        ?.document.languageId || 'python';
      setStatus('⚡ C2...', 'Generating');
      const r = await ask(
        `Generate ${lang} code for: ${desc}\nReturn only clean production-ready code.`,
        'rag');
      const a = await vscode.window.showInformationMessage(
        `⚡ Code ready (${r.provider})`, 'Insert', 'Show');
      if (a === 'Insert') {
        const ed = vscode.window.activeTextEditor;
        if (ed) ed.edit(eb => eb.insert(ed.selection.active, r.response));
      } else if (a === 'Show') {
        showPanel('Generated Code', r);
      }
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.reviewCode', async () => {
      const txt = getSelection(vscode.window.activeTextEditor)
        || vscode.window.activeTextEditor?.document.getText()
        || '';
      if (!txt) {
        vscode.window.showWarningMessage('No code to review');
        return;
      }
      setStatus('⚡ C2...', 'Constitutional review');
      const r = await ask(
        `Constitutional code review — security, privacy, dangerous patterns:\n\`\`\`\n${txt.slice(0, 2000)}\n\`\`\``,
        'constitutional');
      showPanel('Constitutional Review', r);
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.debateCode', async () => {
      const txt = getSelection(vscode.window.activeTextEditor);
      if (!txt) {
        vscode.window.showWarningMessage('Select code to debate');
        return;
      }
      setStatus('⚡ C2...', '3-agent debate');
      vscode.window.showInformationMessage('⚡ Debate council starting...');
      const r = await ask(
        `3-agent debate on code quality:\n\`\`\`\n${txt.slice(0, 1000)}\n\`\`\``,
        'debate');
      showPanel('Debate Verdict', r);
      setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
    }],

    ['charlie2.auditChain', async () => {
      setStatus('⚡ C2...', 'Loading governance chain');
      try {
        const audit = await apiGet('/audit');
        const j     = audit.judicial || [];
        const p     = vscode.window.createWebviewPanel(
          'charlie2Audit', '⚡ Governance Chain',
          vscode.ViewColumn.Beside, {});
        p.webview.html = `<!DOCTYPE html><html>
<head><meta charset="UTF-8"><style>
  body{background:#0d1117;color:#e6edf3;font-family:monospace;
       padding:20px;font-size:12px;}
  h2{color:#00d4ff;margin-bottom:16px;}
  .e{background:#161b22;border:1px solid #30363d;border-radius:6px;
     padding:8px 12px;margin-bottom:6px;}
  .b{font-size:9px;font-weight:700;color:#f85149;margin-bottom:2px;}
  .v{display:inline-block;padding:1px 6px;border-radius:8px;
     font-size:9px;margin-left:6px;}
  .APPROVED{background:#1a4731;color:#3fb950;}
  .BLOCKED{background:#3d1a1a;color:#f85149;}
  .h{color:#a371f7;font-size:9px;margin-top:2px;}
</style></head><body>
<h2>⚖️ Governance Chain — ${j.length} judicial records</h2>
${j.slice(0, 50).map(r => `
<div class="e">
  <div class="b">JUDICIAL
    <span class="v ${r.verdict}">${r.verdict}</span>
  </div>
  <div>${(r.event || '').slice(0, 60)}</div>
  <div class="h">[${(r.hash || '').slice(0, 12)}]</div>
</div>`).join('')}
</body></html>`;
        setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
      } catch(e) {
        vscode.window.showErrorMessage(`Charlie 2.0 offline: ${e.message}`);
      }
    }],

    ['charlie2.openChat', async () => {
      vscode.commands.executeCommand(
        'workbench.view.extension.charlie2-sidebar');
    }],

    ['charlie2.zkpProve', async () => {
      setStatus('⚡ C2...', 'Generating ZK proof');
      vscode.window.showInformationMessage('⚡ Generating sovereign proof...');
      try {
        const proof = await apiPost('/zkp/prove', {}, 30000);
        const a = await vscode.window.showInformationMessage(
          `⚡ Seal: ${(proof.sovereign_seal || '').slice(0, 20)}...`,
          'View Full Proof');
        if (a === 'View Full Proof') {
          const p = vscode.window.createWebviewPanel(
            'charlie2ZKP', '⚡ ZK Proof',
            vscode.ViewColumn.Beside, {});
          p.webview.html = `<pre style="background:#0d1117;color:#3fb950;
            padding:20px;font-size:11px">${JSON.stringify(proof, null, 2)}</pre>`;
        }
        setStatus('⚡ C2', 'Charlie 2.0 ONLINE');
      } catch(e) {
        vscode.window.showErrorMessage(`ZK error: ${e.message}`);
      }
    }]
  ];

  commands.forEach(([id, fn]) =>
    context.subscriptions.push(
      vscode.commands.registerCommand(id, fn)));

  checkHealth();
  const timer = setInterval(checkHealth, 30000);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });

  outputChannel.appendLine('⚡ Charlie 2.0 Sovereign AI activated');
  vscode.window.showInformationMessage(
    '⚡ Charlie 2.0 Sovereign AI ready',
    'Open Chat', 'Configure'
  ).then(a => {
    if (a === 'Open Chat')
      vscode.commands.executeCommand('charlie2.openChat');
    if (a === 'Configure')
      vscode.commands.executeCommand(
        'workbench.action.openSettings', 'charlie2');
  });
}

function deactivate() {
  outputChannel?.appendLine('⚡ Charlie 2.0 deactivated');
}

module.exports = { activate, deactivate };
