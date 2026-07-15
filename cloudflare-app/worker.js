const BAIDU_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime";
const TOUTIAO_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc";
const DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";
const TAVILY_URL = "https://api.tavily.com/search";

const TRACKS = {
  minsheng: { name: "民生", keywords: ["养老金", "社保", "医保", "工资", "就业", "楼市", "房价", "教育", "高考", "交通", "天气", "消费", "食品", "快递"] },
  tiyu: { name: "体育", keywords: ["足球", "篮球", "世界杯", "中超", "NBA", "奥运", "全运会", "冠军", "比赛", "国足", "女足"] },
  yule: { name: "娱乐", keywords: ["明星", "演员", "电影", "电视剧", "综艺", "票房", "演唱会", "娱乐圈", "导演"] },
  keji: { name: "科技", keywords: ["AI", "人工智能", "芯片", "手机", "苹果", "华为", "小米", "机器人", "互联网", "发布会", "科技"] },
  caiqi: { name: "财企", keywords: ["股市", "A股", "公司", "企业", "银行", "基金", "经济", "财报", "融资", "上市", "黄金"] },
  shishi: { name: "时事", keywords: ["外交", "政策", "会议", "国际", "美国", "日本", "欧洲", "联合国", "回应", "通报"] },
  jiankang: { name: "健康", keywords: ["健康", "医院", "医生", "疾病", "药物", "医疗", "养生", "睡眠", "减肥"] },
  lishi: { name: "历史", keywords: ["历史", "古代", "皇帝", "考古", "文物", "博物馆", "遗址"] },
  meishi: { name: "美食", keywords: ["美食", "菜谱", "餐厅", "烹饪", "食材", "火锅", "小吃"] }
};

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
});

function isBasicAuthorized(request, env) {
  const expected = `Basic ${btoa(`flowx:${env.FLOWX_PASSWORD || ""}`)}`;
  return Boolean(env.FLOWX_PASSWORD) && request.headers.get("Authorization") === expected;
}

function htmlEscape(value) {
  return String(value || "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function parseCookies(request) {
  return Object.fromEntries((request.headers.get("Cookie") || "").split(";").map(v => v.trim()).filter(Boolean).map(v => {
    const i = v.indexOf("=");
    return [v.slice(0, i), decodeURIComponent(v.slice(i + 1))];
  }));
}

function base64Url(bytes) {
  return bytesToBase64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64Url(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  return base64ToBytes(normalized);
}

async function hmac(value, secret) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
  return base64Url(new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value))));
}

async function makeSession(user, env) {
  const payload = base64Url(new TextEncoder().encode(JSON.stringify({
    email: user.email, name: user.name || user.email, picture: user.picture || "",
    exp: Math.floor(Date.now() / 1000) + 30 * 24 * 3600
  })));
  return `${payload}.${await hmac(payload, env.SESSION_SECRET)}`;
}

async function readSession(request, env) {
  const raw = parseCookies(request).flowx_session;
  if (!raw || !env.SESSION_SECRET) return null;
  const [payload, signature] = raw.split(".");
  if (!payload || !signature || await hmac(payload, env.SESSION_SECRET) !== signature) return null;
  try {
    const data = JSON.parse(new TextDecoder().decode(fromBase64Url(payload)));
    if (!data.email || data.exp < Date.now() / 1000) return null;
    return data;
  } catch { return null; }
}

function loginPage(env, error = "") {
  const ready = Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET);
  return new Response(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>登录 · FlowX</title><style>:root{--paper:#F4ECDD;--surface:#FDFAF3;--ink:#2A231E;--soft:#7C7064;--line:#E6DAC6;--brand:#AE352B}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--paper);color:var(--ink);font:15px/1.6 -apple-system,"PingFang SC",sans-serif}.box{width:min(430px,calc(100% - 32px));background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:34px;box-shadow:0 18px 55px #4a321e18}.brand{font:800 30px/1 Georgia,serif;color:var(--brand)}h1{font-size:24px;margin:25px 0 7px}p{color:var(--soft);margin:0 0 24px}.google{display:flex;align-items:center;justify-content:center;gap:11px;width:100%;padding:12px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--ink);font-weight:700;text-decoration:none}.g{font:800 20px Arial;color:#4285f4}.note{font-size:12px;color:var(--soft);margin-top:18px}.err{color:#DE3A32;background:#FBE4E1;padding:9px 11px;border-radius:8px;margin-bottom:14px}</style><main class="box"><div class="brand">FlowX</div><h1>登录内容工作台</h1><p>使用获授权的 Google 账号继续。登录状态将在当前浏览器保持 30 天。</p>${error ? `<div class="err">${htmlEscape(error)}</div>` : ""}${ready ? '<a class="google" href="/auth/login"><span class="g">G</span> 使用 Google 账号登录</a>' : '<div class="err">Google OAuth 尚未完成配置</div>'}<div class="note">仅允许管理员账号访问 · API Key 与稿件数据不会提供给 Google</div></main></html>`, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

async function verifyGoogleIdToken(token, env) {
  const [headerPart, payloadPart, signaturePart] = token.split(".");
  if (!signaturePart) throw new Error("Google 身份令牌格式无效");
  const header = JSON.parse(new TextDecoder().decode(fromBase64Url(headerPart)));
  const payload = JSON.parse(new TextDecoder().decode(fromBase64Url(payloadPart)));
  const certs = await (await fetch("https://www.googleapis.com/oauth2/v3/certs", { cf: { cacheTtl: 3600, cacheEverything: true } })).json();
  const jwk = certs.keys?.find(k => k.kid === header.kid);
  if (!jwk || header.alg !== "RS256") throw new Error("无法验证 Google 签名");
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, fromBase64Url(signaturePart), new TextEncoder().encode(`${headerPart}.${payloadPart}`));
  if (!ok || !["accounts.google.com", "https://accounts.google.com"].includes(payload.iss) || payload.aud !== env.GOOGLE_CLIENT_ID || payload.exp < Date.now() / 1000 || !payload.email_verified) throw new Error("Google 身份验证未通过");
  const allowed = String(env.ALLOWED_EMAILS || "").split(",").map(v => v.trim().toLowerCase()).filter(Boolean);
  if (allowed.length && !allowed.includes(String(payload.email).toLowerCase())) throw new Error("该 Google 账号未获 FlowX 访问权限");
  return payload;
}

async function handleAuth(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/auth/login") {
    if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET) return loginPage(env);
    const state = base64Url(crypto.getRandomValues(new Uint8Array(24)));
    const redirect = `${url.origin}/auth/callback`;
    const target = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    target.search = new URLSearchParams({ client_id: env.GOOGLE_CLIENT_ID, redirect_uri: redirect, response_type: "code", scope: "openid email profile", state, prompt: "select_account" }).toString();
    return new Response(null, { status: 302, headers: { Location: target.toString(), "Set-Cookie": `flowx_oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600` } });
  }
  if (url.pathname === "/auth/callback") {
    const cookies = parseCookies(request);
    if (!url.searchParams.get("code") || !url.searchParams.get("state") || cookies.flowx_oauth_state !== url.searchParams.get("state")) return loginPage(env, "登录状态校验失败，请重试");
    try {
      const tokenResponse = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ code: url.searchParams.get("code"), client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, redirect_uri: `${url.origin}/auth/callback`, grant_type: "authorization_code" }) });
      const tokens = await tokenResponse.json();
      if (!tokenResponse.ok || !tokens.id_token) throw new Error(tokens.error_description || "Google 登录交换失败");
      const user = await verifyGoogleIdToken(tokens.id_token, env);
      const session = await makeSession(user, env);
      return new Response(null, { status: 302, headers: { Location: "/", "Set-Cookie": `flowx_session=${encodeURIComponent(session)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`, "Cache-Control": "no-store" } });
    } catch (error) { return loginPage(env, error.message); }
  }
  if (url.pathname === "/auth/logout") return new Response(null, { status: 302, headers: { Location: "/", "Set-Cookie": "flowx_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0" } });
  return null;
}

function bytesToBase64(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function base64ToBytes(value) {
  const s = atob(value);
  return Uint8Array.from(s, c => c.charCodeAt(0));
}

async function cryptoKey(secret) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(secret));
  return crypto.subtle.importKey("raw", digest, "AES-GCM", false, ["encrypt", "decrypt"]);
}

async function encrypt(value, env) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await cryptoKey(env.CONFIG_KEY);
  const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(value));
  return `${bytesToBase64(iv)}.${bytesToBase64(new Uint8Array(cipher))}`;
}

async function decrypt(value, env) {
  if (!value) return "";
  const [ivPart, cipherPart] = value.split(".");
  const key = await cryptoKey(env.CONFIG_KEY);
  const clear = await crypto.subtle.decrypt({ name: "AES-GCM", iv: base64ToBytes(ivPart) }, key, base64ToBytes(cipherPart));
  return new TextDecoder().decode(clear);
}

async function getConfig(env, key) {
  const row = await env.DB.prepare("SELECT value FROM config WHERE key=?").bind(key).first();
  return row ? decrypt(row.value, env) : "";
}

async function setConfig(env, key, value) {
  const encrypted = await encrypt(value, env);
  await env.DB.prepare("INSERT INTO config(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP")
    .bind(key, encrypted).run();
}

function classify(title) {
  const lower = title.toLowerCase();
  let winner = null;
  let best = 0;
  for (const [key, conf] of Object.entries(TRACKS)) {
    const hits = conf.keywords.filter(k => lower.includes(k.toLowerCase()));
    const score = hits.reduce((n, k) => n + k.length ** 2, 0);
    if (score > best) { best = score; winner = { key, name: conf.name }; }
  }
  return winner;
}

async function fetchHotspots() {
  const headers = { "user-agent": "Mozilla/5.0 Chrome/125 Safari/537.36" };
  const [baidu, toutiao] = await Promise.allSettled([
    fetch(BAIDU_URL, { headers }), fetch(TOUTIAO_URL, { headers })
  ]);
  const items = [];
  if (baidu.status === "fulfilled" && baidu.value.ok) {
    const data = await baidu.value.json();
    const rows = data?.data?.cards?.flatMap(c => c.content || []) || [];
    for (const row of rows.slice(0, 40)) {
      const title = String(row.word || row.query || row.title || "").trim();
      if (title) items.push({ title, source: "百度", url: row.url || row.rawUrl || "", hot: null });
    }
  }
  if (toutiao.status === "fulfilled" && toutiao.value.ok) {
    const data = await toutiao.value.json();
    const rows = data?.data || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row.Title || row.title || row.QueryWord || "").trim();
      if (title) items.push({ title, source: "头条", url: row.Url || row.url || "", hot: Number(row.HotValue || 0) || null });
    }
  }
  const seen = new Set();
  const tracks = {};
  for (const item of items) {
    const normalized = item.title.replace(/[\s，。！？、：“”‘’《》()（）【】\-]/g, "").toLowerCase();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    const hit = classify(item.title);
    if (!hit) continue;
    if (!tracks[hit.key]) tracks[hit.key] = { name: hit.name, items: [] };
    tracks[hit.key].items.push(item);
  }
  return { total: items.length, tracks };
}

async function tavilySearch(query, key) {
  const response = await fetch(TAVILY_URL, {
    method: "POST",
    headers: { "content-type": "application/json", "authorization": `Bearer ${key}` },
    body: JSON.stringify({ query, search_depth: "basic", max_results: 5, include_answer: false, api_key: key })
  });
  if (!response.ok) throw new Error(`Tavily 搜索失败：${response.status}`);
  return (await response.json()).results || [];
}

async function deepseek(messages, key, temperature = 0.7) {
  const response = await fetch(DEEPSEEK_URL, {
    method: "POST",
    headers: { "content-type": "application/json", "authorization": `Bearer ${key}` },
    body: JSON.stringify({ model: "deepseek-chat", messages, temperature, response_format: { type: "json_object" } })
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.error?.message || `DeepSeek 调用失败：${response.status}`);
  const raw = data?.choices?.[0]?.message?.content || "{}";
  return JSON.parse(raw.replace(/^```json\s*|\s*```$/g, ""));
}

async function qualityCheck(article, key) {
  const localProblems = [];
  if (article.title.length > 30) localProblems.push(`标题过长（${article.title.length}字）`);
  if (article.title.length < 8) localProblems.push(`标题过短（${article.title.length}字）`);
  const length = article.body.replace(/\s/g, "").length;
  if (length < 400) localProblems.push(`正文过短（${length}字）`);
  if (length > 1200) localProblems.push(`正文过长（${length}字）`);
  const ai = await deepseek([
    { role: "system", content: "你是中文内容平台资深审稿编辑。只返回JSON。缺来源或未证实的问题只能建议删除、软化或去掉具体数字，禁止建议编造或补充来源。" },
    { role: "user", content: `检查稿件的逻辑、事实一致性、合规和AI味。返回 {\"score\":0到100,\"problems\":[\"问题\"]}。\n标题：${article.title}\n正文：${article.body}` }
  ], key, 0.2);
  const score = Math.max(0, Math.min(100, Math.round(Number(ai.score) || 75) - localProblems.length * 5));
  const problems = [...new Set([...localProblems, ...(Array.isArray(ai.problems) ? ai.problems.map(String) : [])])];
  return { score, level: score >= 80 ? "green" : score >= 60 ? "yellow" : "red", problems };
}

async function articleId(title) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(title));
  return [...new Uint8Array(digest)].slice(0, 8).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function saveArticle(env, article, qc, oldId = null) {
  const id = await articleId(article.title);
  const status = qc.level === "red" ? "待修复" : "未发";
  if (oldId && oldId !== id) await env.DB.prepare("DELETE FROM articles WHERE id=?").bind(oldId).run();
  await env.DB.prepare(`INSERT INTO articles(id,title,body,track,source,status,qc_score,qc_level,qc_problems,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET title=excluded.title,body=excluded.body,track=excluded.track,source=excluded.source,status=excluded.status,qc_score=excluded.qc_score,qc_level=excluded.qc_level,qc_problems=excluded.qc_problems,updated_at=CURRENT_TIMESTAMP`)
    .bind(id, article.title, article.body, article.track || "", article.source || "", status, qc.score, qc.level, JSON.stringify(qc.problems)).run();
  return { id, ...article, status, qc_score: qc.score, qc_level: qc.level, qc_problems: qc.problems };
}

async function generateOne(item, env) {
  const deepseekKey = await getConfig(env, "DEEPSEEK_API_KEY");
  const tavilyKey = await getConfig(env, "TAVILY_API_KEY");
  if (!deepseekKey || !tavilyKey) throw new Error("请先在设置中配置 DeepSeek 与 Tavily API Key");
  const search = await tavilySearch(item.title, tavilyKey);
  const material = search.map((r, i) => `【资料${i + 1}】${r.title || ""}\n${r.content || ""}`).join("\n\n");
  const track = TRACKS[item.track_key]?.name || item.track || "综合";
  const draft = await deepseek([
    { role: "system", content: `你是中文内容平台资深作者，当前赛道是${track}。只返回JSON。事实必须来自所给资料；资料不足时只能做分析，不能编造数字、机构、日期和来源。` },
    { role: "user", content: `围绕选题写一篇约600到900字的中文文章。标题完整、有信息量、不超过30字。返回 {\"title\":\"\",\"body\":\"\"}。\n选题：${item.title}\n${material}` }
  ], deepseekKey, 0.8);
  const article = { title: String(draft.title || item.title).trim().slice(0, 60), body: String(draft.body || "").trim(), track, source: item.source || "" };
  if (article.body.length < 50) throw new Error("模型返回正文过短");
  const qc = await qualityCheck(article, deepseekKey);
  return saveArticle(env, article, qc);
}

async function handleApi(request, env, user) {
  const url = new URL(request.url);
  const path = url.pathname;
  if (path === "/api/health") return json({ ok: true, service: "FlowX Cloud", region: request.cf?.colo || "unknown" });
  if (path === "/api/me") return json({ user, session_days: 30, auth: user?.emergency ? "basic" : "google" });

  if (path === "/api/settings" && request.method === "GET") {
    const rows = await env.DB.prepare("SELECT key FROM config").all();
    const keys = new Set((rows.results || []).map(r => r.key));
    return json({ keys: { deepseek: keys.has("DEEPSEEK_API_KEY"), tavily: keys.has("TAVILY_API_KEY") } });
  }
  if (path === "/api/settings/keys" && request.method === "POST") {
    const body = await request.json();
    if (String(body.deepseek || "").trim()) await setConfig(env, "DEEPSEEK_API_KEY", String(body.deepseek).trim());
    if (String(body.tavily || "").trim()) await setConfig(env, "TAVILY_API_KEY", String(body.tavily).trim());
    return json({ ok: true });
  }
  if (path === "/api/hotspots" && request.method === "POST") return json(await fetchHotspots());
  if (path === "/api/generate" && request.method === "POST") {
    const body = await request.json();
    const items = Array.isArray(body.items) ? body.items.slice(0, 5) : [];
    if (!items.length) return json({ error: "至少选择一个选题" }, 400);
    const results = [];
    for (const item of items) {
      try { results.push({ ok: true, ...(await generateOne(item, env)) }); }
      catch (error) { results.push({ ok: false, title: item.title, error: error.message }); }
    }
    return json({ results });
  }
  if (path === "/api/articles" && request.method === "GET") {
    const rows = await env.DB.prepare("SELECT * FROM articles ORDER BY created_at DESC LIMIT 500").all();
    return json({ articles: rows.results || [] });
  }
  const articleMatch = path.match(/^\/api\/articles\/([a-f0-9]+)$/);
  if (articleMatch && request.method === "PUT") {
    const old = await env.DB.prepare("SELECT * FROM articles WHERE id=?").bind(articleMatch[1]).first();
    if (!old) return json({ error: "稿件不存在" }, 404);
    const body = await request.json();
    const article = { title: String(body.title || "").trim(), body: String(body.body || "").trim(), track: old.track, source: old.source };
    if (article.title.length < 4 || article.body.length < 50) return json({ error: "标题至少4字，正文至少50字" }, 400);
    const key = await getConfig(env, "DEEPSEEK_API_KEY");
    const qc = await qualityCheck(article, key);
    return json({ ok: true, ...(await saveArticle(env, article, qc, articleMatch[1])) });
  }
  if (articleMatch && request.method === "DELETE") {
    await env.DB.prepare("DELETE FROM articles WHERE id=?").bind(articleMatch[1]).run();
    return json({ ok: true });
  }
  const statusMatch = path.match(/^\/api\/articles\/([a-f0-9]+)\/status$/);
  if (statusMatch && request.method === "POST") {
    const body = await request.json();
    if (!["未发", "已发", "待修复"].includes(body.status)) return json({ error: "状态无效" }, 400);
    await env.DB.prepare("UPDATE articles SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?").bind(body.status, statusMatch[1]).run();
    return json({ ok: true });
  }
  if (path === "/api/revise" && request.method === "POST") {
    const body = await request.json();
    const old = await env.DB.prepare("SELECT * FROM articles WHERE id=?").bind(body.id).first();
    if (!old) return json({ error: "稿件不存在" }, 404);
    const key = await getConfig(env, "DEEPSEEK_API_KEY");
    const problems = JSON.parse(old.qc_problems || "[]");
    const revised = await deepseek([
      { role: "system", content: "你是中文内容编辑。只返回JSON。根据问题修订稿件；缺来源只能删除、软化或去掉具体数字，绝不新增来源、机构、日期或数字。" },
      { role: "user", content: `返回 {\"title\":\"\",\"body\":\"\"}。\n问题：${problems.join("；")}\n标题：${old.title}\n正文：${old.body}` }
    ], key, 0.4);
    const article = { title: String(revised.title || old.title).trim(), body: String(revised.body || old.body).trim(), track: old.track, source: old.source };
    const qc = await qualityCheck(article, key);
    return json({ ok: true, ...(await saveArticle(env, article, qc, old.id)) });
  }
  return json({ error: "Not found" }, 404);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname.startsWith("/auth/")) return await handleAuth(request, env);
      let user = await readSession(request, env);
      if (!user && isBasicAuthorized(request, env)) user = { email: "emergency@flowx.local", name: "Emergency Admin", picture: "", emergency: true };
      if (!user) return url.pathname.startsWith("/api/") ? json({ error: "请先使用 Google 账号登录", login: "/auth/login" }, 401) : loginPage(env);
      if (url.pathname.startsWith("/api/")) return await handleApi(request, env, user);
      return env.ASSETS.fetch(request);
    } catch (error) {
      return json({ error: error.message || "服务器错误" }, 500);
    }
  }
};
