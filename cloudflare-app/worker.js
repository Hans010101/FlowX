const BAIDU_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime";
const TOUTIAO_URL =
  "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc";
const DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";
const TAVILY_URL = "https://api.tavily.com/search";
const BOCHA_URL = "https://api.bochaai.com/v1/web-search";
const PEXELS_URL = "https://api.pexels.com/v1/search";
const DEFAULT_DAILYHOT_URL = "https://api-hot.imsyy.top";
const DEEPSEEK_MODEL = "deepseek-v4-flash";
const ARTICLE_RETENTION_HOURS = 36;
const ARTICLE_MIN_CHARACTERS = 600;
const ARTICLE_MAX_CHARACTERS = 1000;
const TITLE_SIMILARITY_LIMIT = 0.55;
const HOTSPOT_REQUEST_TIMEOUT_MS = 9000;
const GENERATION_CONCURRENCY = 2;
const WORKERS_AI_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";

const HOT_SOURCES = {
  baidu: { name: "百度", direct: true },
  toutiao: { name: "今日头条", direct: true },
  douyin: { name: "抖音", direct: true },
  weibo: { name: "微博", direct: true },
  zhihu: { name: "知乎", direct: true },
  bilibili: { name: "B站", direct: true },
  "36kr": { name: "36氪", direct: true },
  thepaper: { name: "澎湃", direct: true },
};
const DEFAULT_HOT_SOURCES = Object.keys(HOT_SOURCES);

const TRACKS = {
  minsheng: {
    name: "民生",
    keywords: [
      "养老金",
      "社保",
      "医保",
      "工资",
      "就业",
      "楼市",
      "房价",
      "教育",
      "高考",
      "交通",
      "天气",
      "消费",
      "食品",
      "快递",
      "养老",
      "退休",
      "生育",
      "住房",
      "租房",
      "学生",
      "大学",
      "出行",
      "高温",
      "台风",
      "暴雨",
      "外卖",
      "民生",
    ],
  },
  tiyu: {
    name: "体育",
    keywords: [
      "足球",
      "篮球",
      "世界杯",
      "中超",
      "NBA",
      "奥运",
      "全运会",
      "冠军",
      "比赛",
      "国足",
      "女足",
      "网球",
      "乒乓",
      "羽毛球",
      "排球",
      "全明星",
      "联赛",
      "决赛",
      "运动员",
    ],
  },
  yule: {
    name: "娱乐",
    keywords: [
      "明星",
      "演员",
      "电影",
      "电视剧",
      "综艺",
      "票房",
      "演唱会",
      "娱乐圈",
      "导演",
      "短剧",
      "音乐",
      "歌手",
      "新片",
      "开机",
      "杀青",
      "播出",
    ],
  },
  keji: {
    name: "科技",
    keywords: [
      "AI",
      "人工智能",
      "芯片",
      "手机",
      "苹果",
      "华为",
      "小米",
      "机器人",
      "互联网",
      "发布会",
      "科技",
      "大模型",
      "算力",
      "电池",
      "新能源",
      "自动驾驶",
      "智能",
      "数码",
      "软件",
    ],
  },
  caiqi: {
    name: "财企",
    keywords: [
      "股市",
      "A股",
      "公司",
      "企业",
      "银行",
      "基金",
      "经济",
      "财报",
      "融资",
      "上市",
      "黄金",
      "商业",
      "产业",
      "制造业",
      "零售",
      "品牌",
      "营收",
      "利率",
      "汇率",
      "关税",
    ],
  },
  shishi: {
    name: "时事",
    keywords: [
      "外交",
      "政策",
      "会议",
      "国际",
      "美国",
      "日本",
      "欧洲",
      "联合国",
      "回应",
      "通报",
      "官方",
      "发布",
      "调查",
      "冲突",
      "选举",
      "访问",
      "谈判",
      "安全",
    ],
  },
  jiankang: {
    name: "健康",
    keywords: [
      "健康",
      "医院",
      "医生",
      "疾病",
      "药物",
      "医疗",
      "养生",
      "睡眠",
      "减肥",
      "中暑",
      "疫苗",
      "营养",
      "急救",
      "心理",
      "感染",
    ],
  },
  lishi: {
    name: "历史",
    keywords: ["历史", "古代", "皇帝", "考古", "文物", "博物馆", "遗址"],
  },
  meishi: {
    name: "美食",
    keywords: ["美食", "菜谱", "餐厅", "烹饪", "食材", "火锅", "小吃"],
  },
};

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

function fetchWithTimeout(
  input,
  init = {},
  timeoutMs = HOTSPOT_REQUEST_TIMEOUT_MS,
) {
  return fetch(input, {
    ...init,
    signal: init.signal || AbortSignal.timeout(timeoutMs),
  });
}

function htmlEscape(value) {
  return String(value || "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}

function parseCookies(request) {
  return Object.fromEntries(
    (request.headers.get("Cookie") || "")
      .split(";")
      .map((v) => v.trim())
      .filter(Boolean)
      .map((v) => {
        const i = v.indexOf("=");
        return [v.slice(0, i), decodeURIComponent(v.slice(i + 1))];
      }),
  );
}

function base64Url(bytes) {
  return bytesToBase64(bytes)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function fromBase64Url(value) {
  const normalized = value
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(value.length / 4) * 4, "=");
  return base64ToBytes(normalized);
}

async function hmac(value, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
  return base64Url(
    new Uint8Array(
      await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)),
    ),
  );
}

async function makeSession(user, env) {
  const payload = base64Url(
    new TextEncoder().encode(
      JSON.stringify({
        email: user.email,
        name: user.name || user.email,
        picture: user.picture || "",
        exp: Math.floor(Date.now() / 1000) + 30 * 24 * 3600,
      }),
    ),
  );
  return `${payload}.${await hmac(payload, env.SESSION_SECRET)}`;
}

async function readSession(request, env) {
  const raw = parseCookies(request).flowx_session;
  if (!raw || !env.SESSION_SECRET) return null;
  const [payload, signature] = raw.split(".");
  if (
    !payload ||
    !signature ||
    (await hmac(payload, env.SESSION_SECRET)) !== signature
  )
    return null;
  try {
    const data = JSON.parse(new TextDecoder().decode(fromBase64Url(payload)));
    if (!data.email || data.exp < Date.now() / 1000) return null;
    return data;
  } catch {
    return null;
  }
}

function loginPage(env, error = "") {
  const ready = Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET);
  return new Response(
    `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>登录 · FlowX</title><style>:root{--paper:#F4ECDD;--surface:#FDFAF3;--ink:#2A231E;--soft:#7C7064;--line:#E6DAC6;--brand:#AE352B}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--paper);color:var(--ink);font:15px/1.6 -apple-system,"PingFang SC",sans-serif}.box{width:min(430px,calc(100% - 32px));background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:34px;box-shadow:0 18px 55px #4a321e18}.brand{font:800 30px/1 Georgia,serif;color:var(--brand)}h1{font-size:24px;margin:25px 0 7px}p{color:var(--soft);margin:0 0 24px}.google{display:flex;align-items:center;justify-content:center;gap:11px;width:100%;padding:12px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--ink);font-weight:700;text-decoration:none}.g{font:800 20px Arial;color:#4285f4}.note{font-size:12px;color:var(--soft);margin-top:18px}.err{color:#DE3A32;background:#FBE4E1;padding:9px 11px;border-radius:8px;margin-bottom:14px}</style><main class="box"><div class="brand">FlowX</div><h1>登录内容工作台</h1><p>使用获授权的 Google 账号继续。登录状态将在当前浏览器保持 30 天。</p>${error ? `<div class="err">${htmlEscape(error)}</div>` : ""}${ready ? '<a class="google" href="/auth/login"><span class="g">G</span> 使用 Google 账号登录</a>' : '<div class="err">Google OAuth 尚未完成配置</div>'}<div class="note">仅允许管理员账号访问 · API Key 与稿件数据不会提供给 Google</div></main></html>`,
    {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "no-store",
      },
    },
  );
}

async function verifyGoogleIdToken(token, env) {
  const [headerPart, payloadPart, signaturePart] = token.split(".");
  if (!signaturePart) throw new Error("Google 身份令牌格式无效");
  const header = JSON.parse(
    new TextDecoder().decode(fromBase64Url(headerPart)),
  );
  const payload = JSON.parse(
    new TextDecoder().decode(fromBase64Url(payloadPart)),
  );
  const certs = await (
    await fetch("https://www.googleapis.com/oauth2/v3/certs", {
      cf: { cacheTtl: 3600, cacheEverything: true },
    })
  ).json();
  const jwk = certs.keys?.find((k) => k.kid === header.kid);
  if (!jwk || header.alg !== "RS256") throw new Error("无法验证 Google 签名");
  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const ok = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    key,
    fromBase64Url(signaturePart),
    new TextEncoder().encode(`${headerPart}.${payloadPart}`),
  );
  if (
    !ok ||
    !["accounts.google.com", "https://accounts.google.com"].includes(
      payload.iss,
    ) ||
    payload.aud !== env.GOOGLE_CLIENT_ID ||
    payload.exp < Date.now() / 1000 ||
    !payload.email_verified
  )
    throw new Error("Google 身份验证未通过");
  const allowed = String(env.ALLOWED_EMAILS || "")
    .split(",")
    .map((v) => v.trim().toLowerCase())
    .filter(Boolean);
  if (allowed.length && !allowed.includes(String(payload.email).toLowerCase()))
    throw new Error("该 Google 账号未获 FlowX 访问权限");
  return payload;
}

async function handleAuth(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/auth/login") {
    if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET)
      return loginPage(env);
    const state = base64Url(crypto.getRandomValues(new Uint8Array(24)));
    const redirect = `${url.origin}/auth/callback`;
    const target = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    target.search = new URLSearchParams({
      client_id: env.GOOGLE_CLIENT_ID,
      redirect_uri: redirect,
      response_type: "code",
      scope: "openid email profile",
      state,
      prompt: "select_account",
    }).toString();
    return new Response(null, {
      status: 302,
      headers: {
        Location: target.toString(),
        "Set-Cookie": `flowx_oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`,
      },
    });
  }
  if (url.pathname === "/auth/callback") {
    const cookies = parseCookies(request);
    if (
      !url.searchParams.get("code") ||
      !url.searchParams.get("state") ||
      cookies.flowx_oauth_state !== url.searchParams.get("state")
    )
      return loginPage(env, "登录状态校验失败，请重试");
    try {
      const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          code: url.searchParams.get("code"),
          client_id: env.GOOGLE_CLIENT_ID,
          client_secret: env.GOOGLE_CLIENT_SECRET,
          redirect_uri: `${url.origin}/auth/callback`,
          grant_type: "authorization_code",
        }),
      });
      const tokens = await tokenResponse.json();
      if (!tokenResponse.ok || !tokens.id_token)
        throw new Error(tokens.error_description || "Google 登录交换失败");
      const user = await verifyGoogleIdToken(tokens.id_token, env);
      const session = await makeSession(user, env);
      return new Response(null, {
        status: 302,
        headers: {
          Location: "/",
          "Set-Cookie": `flowx_session=${encodeURIComponent(session)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`,
          "Cache-Control": "no-store",
        },
      });
    } catch (error) {
      return loginPage(env, error.message);
    }
  }
  if (url.pathname === "/auth/logout")
    return new Response(null, {
      status: 302,
      headers: {
        Location: "/",
        "Set-Cookie":
          "flowx_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0",
      },
    });
  return null;
}

function bytesToBase64(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function base64ToBytes(value) {
  const s = atob(value);
  return Uint8Array.from(s, (c) => c.charCodeAt(0));
}

async function cryptoKey(secret) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(secret),
  );
  return crypto.subtle.importKey("raw", digest, "AES-GCM", false, [
    "encrypt",
    "decrypt",
  ]);
}

async function encrypt(value, env) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await cryptoKey(env.CONFIG_KEY);
  const cipher = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(value),
  );
  return `${bytesToBase64(iv)}.${bytesToBase64(new Uint8Array(cipher))}`;
}

async function decrypt(value, env) {
  if (!value) return "";
  const [ivPart, cipherPart] = value.split(".");
  const key = await cryptoKey(env.CONFIG_KEY);
  const clear = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: base64ToBytes(ivPart) },
    key,
    base64ToBytes(cipherPart),
  );
  return new TextDecoder().decode(clear);
}

function accountEmail(user) {
  return String(user?.email || "")
    .trim()
    .toLowerCase();
}

async function getConfig(env, email, key) {
  const row = await env.DB.prepare(
    "SELECT value FROM user_config WHERE owner_email=? AND key=?",
  )
    .bind(email, key)
    .first();
  return row ? decrypt(row.value, env) : "";
}

async function setConfig(env, email, key, value) {
  const encrypted = await encrypt(value, env);
  await env.DB.prepare(
    "INSERT INTO user_config(owner_email,key,value,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(owner_email,key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
  )
    .bind(email, key, encrypted)
    .run();
}

function classify(title) {
  const lower = title.toLowerCase();
  let winner = null;
  let best = 0;
  for (const [key, conf] of Object.entries(TRACKS)) {
    const hits = conf.keywords.filter((k) => lower.includes(k.toLowerCase()));
    const score = hits.reduce((n, k) => n + k.length ** 2, 0);
    if (score > best) {
      best = score;
      winner = { key, name: conf.name };
    }
  }
  return winner;
}

function hotNumber(value) {
  const n = Number(String(value ?? "").replace(/[^\d.]/g, ""));
  return Number.isFinite(n) && n > 0 ? n : null;
}

async function fetchDirectSource(source) {
  const headers = { "user-agent": "Mozilla/5.0 Chrome/125 Safari/537.36" };
  const items = [];
  if (source === "baidu") {
    const response = await fetchWithTimeout(BAIDU_URL, { headers });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const rows = data?.data?.cards?.flatMap((c) => c.content || []) || [];
    for (const row of rows.slice(0, 40)) {
      const candidates = [
        row,
        ...(Array.isArray(row?.content) ? row.content : []),
      ];
      for (const candidate of candidates) {
        const title = String(
          candidate?.word || candidate?.query || candidate?.title || "",
        ).trim();
        if (title)
          items.push({
            title,
            source,
            url: candidate.url || candidate.rawUrl || "",
            hot: null,
          });
      }
    }
  } else if (source === "toutiao") {
    const response = await fetchWithTimeout(TOUTIAO_URL, { headers });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const rows = data?.data || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(
        row.Title || row.title || row.QueryWord || "",
      ).trim();
      if (title)
        items.push({
          title,
          source,
          url: row.Url || row.url || "",
          hot: hotNumber(row.HotValue),
        });
    }
  } else if (source === "weibo") {
    const response = await fetchWithTimeout(
      "https://weibo.com/ajax/side/hotSearch",
      {
        headers: { ...headers, referer: "https://weibo.com/" },
      },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data?.realtime || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row.word || row.word_scheme || "").trim();
      if (title)
        items.push({
          title,
          source,
          url: `https://s.weibo.com/weibo?q=${encodeURIComponent(title)}`,
          hot: hotNumber(row.num || row.raw_hot),
        });
    }
  } else if (source === "zhihu") {
    const response = await fetchWithTimeout(
      "https://api.zhihu.com/topstory/hot-lists/total?limit=50",
      { headers },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row?.target?.title || "").trim();
      const questionId = String(row?.target?.url || "")
        .split("/")
        .pop();
      if (title)
        items.push({
          title,
          source,
          url: questionId ? `https://www.zhihu.com/question/${questionId}` : "",
          hot: hotNumber(row.detail_text)
            ? hotNumber(row.detail_text) * 10000
            : null,
        });
    }
  } else if (source === "bilibili") {
    const response = await fetchWithTimeout(
      "https://api.bilibili.com/x/web-interface/popular?ps=30&pn=1",
      {
        headers: {
          ...headers,
          referer: "https://www.bilibili.com/v/popular/all",
        },
      },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data?.list || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row.title || "").trim();
      if (title)
        items.push({
          title,
          source,
          url: `https://www.bilibili.com/video/${row.bvid || row.aid}`,
          hot: hotNumber(row?.stat?.view || row.play || row.video_review),
        });
    }
  } else if (source === "thepaper") {
    const response = await fetchWithTimeout(
      "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar",
      { headers },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data?.hotNews || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row.name || "").trim();
      if (title)
        items.push({
          title,
          source,
          url: `https://www.thepaper.cn/newsDetail_forward_${row.contId}`,
          hot: hotNumber(row.praiseTimes),
        });
    }
  } else if (source === "36kr") {
    const response = await fetchWithTimeout(
      "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot",
      {
        method: "POST",
        headers: {
          ...headers,
          "content-type": "application/json; charset=utf-8",
        },
        body: JSON.stringify({
          partner_id: "wap",
          param: { siteId: 1, platformId: 2 },
          timestamp: Date.now(),
        }),
      },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data?.hotRankList || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row?.templateMaterial?.widgetTitle || "").trim();
      if (title)
        items.push({
          title,
          source,
          url: `https://www.36kr.com/p/${row.itemId}`,
          hot: hotNumber(row?.templateMaterial?.statCollect),
        });
    }
  } else if (source === "douyin") {
    const cookieResponse = await fetchWithTimeout(
      "https://www.douyin.com/passport/general/login_guiding_strategy/?aid=6383",
      { headers },
    );
    const token = (cookieResponse.headers.get("set-cookie") || "").match(
      /passport_csrf_token=([^;]+)/,
    )?.[1];
    const response = await fetchWithTimeout(
      "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1",
      {
        headers: {
          ...headers,
          ...(token ? { cookie: `passport_csrf_token=${token}` } : {}),
        },
      },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = (await response.json())?.data?.word_list || [];
    for (const row of rows.slice(0, 30)) {
      const title = String(row.word || "").trim();
      if (title)
        items.push({
          title,
          source,
          url: `https://www.douyin.com/hot/${row.sentence_id}`,
          hot: hotNumber(row.hot_value),
        });
    }
  }
  if (!items.length) throw new Error("来源未返回数据");
  return items;
}

async function fetchDailyHotSource(baseUrl, source) {
  const response = await fetchWithTimeout(
    `${baseUrl.replace(/\/$/, "")}/${encodeURIComponent(source)}`,
    { headers: { "user-agent": "Mozilla/5.0 Chrome/125 Safari/537.36" } },
  );
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  const rows = Array.isArray(data?.data) ? data.data : [];
  return rows
    .slice(0, 30)
    .map((row) => ({
      title: String(row.title || "").trim(),
      source,
      url: row.url || row.mobileUrl || "",
      hot: hotNumber(row.hot),
    }))
    .filter((row) => row.title);
}

function normalizeTopicTitle(title) {
  return String(title || "")
    .replace(/[\s，。！？、：“”‘’《》()（）【】\-]/g, "")
    .toLowerCase();
}

async function hideTopics(env, email, titles, reason = "manual") {
  const rows = [...new Set((titles || []).map(String).map((title) => title.trim()))]
    .map((title) => ({ title, key: normalizeTopicTitle(title) }))
    .filter((row) => row.key)
    .slice(0, 100);
  if (!rows.length) return 0;
  await env.DB.batch(
    rows.map((row) =>
      env.DB.prepare(
        `INSERT INTO user_hidden_topics(owner_email,topic_key,title,reason,hidden_at)
         VALUES(?,?,?,?,CURRENT_TIMESTAMP)
         ON CONFLICT(owner_email,topic_key) DO UPDATE SET
           title=excluded.title,reason=excluded.reason,hidden_at=CURRENT_TIMESTAMP`,
      ).bind(email, row.key, row.title, reason),
    ),
  );
  return rows.length;
}

async function fetchHotspots(env, email) {
  let enabledSources = DEFAULT_HOT_SOURCES;
  let enabledTracks = Object.keys(TRACKS);
  const storedSources = await getConfig(env, email, "HOTSPOT_SOURCES");
  const storedTracks = await getConfig(env, email, "ENABLED_TRACKS");
  try {
    if (storedSources)
      enabledSources = JSON.parse(storedSources).filter((s) => HOT_SOURCES[s]);
  } catch {}
  try {
    if (storedTracks)
      enabledTracks = JSON.parse(storedTracks).filter((s) => TRACKS[s]);
  } catch {}
  if (!enabledSources.length) enabledSources = ["baidu"];
  const baseUrl =
    (await getConfig(env, email, "DAILYHOT_BASE_URL")) || DEFAULT_DAILYHOT_URL;
  const settled = await Promise.all(
    enabledSources.map(async (source) => {
      try {
        if (HOT_SOURCES[source].direct) {
          try {
            return {
              source,
              ok: true,
              provider: "direct",
              items: await fetchDirectSource(source),
            };
          } catch (directError) {
            const items = await fetchDailyHotSource(baseUrl, source);
            return { source, ok: true, provider: "DailyHotApi", items };
          }
        }
        return {
          source,
          ok: true,
          provider: "DailyHotApi",
          items: await fetchDailyHotSource(baseUrl, source),
        };
      } catch (error) {
        return { source, ok: false, error: error.message, items: [] };
      }
    }),
  );
  const items = settled.flatMap((result) => result.items);
  const expiredHidden = await env.DB.prepare(
    "DELETE FROM user_hidden_topics WHERE owner_email=? AND datetime(hidden_at) <= datetime('now', ?)",
  )
    .bind(email, `-${ARTICLE_RETENTION_HOURS} hours`)
    .run();
  const hiddenRows = await env.DB.prepare(
    "SELECT topic_key FROM user_hidden_topics WHERE owner_email=? AND datetime(hidden_at) > datetime('now', ?)",
  )
    .bind(email, `-${ARTICLE_RETENTION_HOURS} hours`)
    .all();
  const hidden = new Set((hiddenRows.results || []).map((row) => row.topic_key));
  const seen = new Set();
  const tracks = {};
  for (const item of items) {
    const normalized = normalizeTopicTitle(item.title);
    if (!normalized || hidden.has(normalized) || seen.has(normalized)) continue;
    seen.add(normalized);
    const hit = classify(item.title);
    if (!hit || !enabledTracks.includes(hit.key)) continue;
    if (!tracks[hit.key]) tracks[hit.key] = { name: hit.name, items: [] };
    tracks[hit.key].items.push({
      ...item,
      source: HOT_SOURCES[item.source]?.name || item.source,
    });
  }
  return {
    total: items.length,
    available: Object.values(tracks).reduce(
      (total, track) => total + track.items.length,
      0,
    ),
    hidden_active: hidden.size,
    hidden_expired: Number(expiredHidden?.meta?.changes || 0),
    enabled_tracks: enabledTracks.map((key) => TRACKS[key]?.name).filter(Boolean),
    tracks,
    base_url: baseUrl,
    sources: settled.map((result) => ({
      code: result.source,
      name: HOT_SOURCES[result.source].name,
      direct: Boolean(HOT_SOURCES[result.source].direct),
      provider: result.provider || "",
      ok: result.ok,
      count: result.items.length,
    })),
  };
}

async function tavilySearch(query, key) {
  const response = await fetch(TAVILY_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      query,
      search_depth: "basic",
      max_results: 5,
      include_answer: false,
      api_key: key,
    }),
  });
  if (!response.ok) throw new Error(`Tavily 搜索失败：${response.status}`);
  return (await response.json()).results || [];
}

async function bochaSearch(query, key) {
  const response = await fetch(BOCHA_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      query,
      summary: true,
      count: 5,
      freshness: "oneWeek",
    }),
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data?.message || `博查搜索失败：${response.status}`);
  return (data?.data?.webPages?.value || []).slice(0, 5).map((row) => ({
    title: row.name || "",
    content: row.summary || row.snippet || "",
    url: row.url || "",
  }));
}

async function searchWithFallback(query, tavilyKey, bochaKey) {
  let first = [];
  if (tavilyKey) {
    try {
      first = await tavilySearch(query, tavilyKey);
    } catch {}
    const chars = first.reduce(
      (n, row) => n + String(row.content || "").length,
      0,
    );
    if (first.length >= 3 && chars >= 300)
      return { results: first, provider: "Tavily" };
  }
  if (bochaKey) {
    try {
      const fallback = await bochaSearch(query, bochaKey);
      if (fallback.length) return { results: fallback, provider: "博查" };
    } catch {}
  }
  return { results: first, provider: tavilyKey ? "Tavily" : "无可用搜索源" };
}

function normalizeImageUrls(value, coverUrl = "") {
  let values = Array.isArray(value) ? value : [];
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      values = Array.isArray(parsed) ? parsed : [value];
    } catch {
      values = [value];
    }
  }
  const unique = [];
  for (const candidate of [coverUrl, ...values]) {
    try {
      const url = new URL(String(candidate || "").trim());
      if (url.protocol !== "https:" || unique.includes(url.href)) continue;
      unique.push(url.href);
      if (unique.length === 3) break;
    } catch {}
  }
  return unique;
}

function normalizeImageQueries(value) {
  if (!Array.isArray(value)) return [];
  return [
    ...new Set(
      value
        .map((query) => String(query || "").trim().replace(/\s+/g, " "))
        .filter((query) => query.length >= 3 && query.length <= 80),
    ),
  ].slice(0, 3);
}

async function imageSearchQueries(article, deepseekKey, env, usage = null) {
  const supplied = normalizeImageQueries(article.image_queries);
  if (supplied.length >= 2) return supplied;
  let queries = supplied;
  if (deepseekKey || env?.AI) {
    try {
      const result = await runBasicJsonModel(
        [
          {
            role: "system",
            content:
              "Return JSON only. Create exactly 3 specific English Pexels stock-photo searches for the article. Each query must use 2-6 concrete visual terms and stay faithful to the event, named subject, location and industry in the supplied text. Cover three distinct visual angles. If an exact news image is unlikely, use a truthful scene-level representation of the same topic. Never use generic filler such as news, background, abstract, business or technology alone. Return {\"queries\":[\"\", \"\", \"\"]}.",
          },
          {
            role: "user",
            content:
              "Title: " +
              String(article.title || "") +
              "\nTrack: " +
              String(article.track || "") +
              "\nEditorial angle: " +
              String(article.writing_angle || "") +
              "\nArticle excerpt: " +
              stripHighlightMarkup(article.body).slice(0, 1200),
          },
        ],
        deepseekKey,
        0.2,
        env,
        usage,
      );
      queries = normalizeImageQueries(result.queries);
    } catch {}
  }
  if (queries.length) return queries;
  return normalizeImageQueries([
    article.track === "体育"
      ? String(article.title || "") + " sports competition"
      : String(article.title || ""),
  ]);
}

async function pexelsSearch(query, pexelsKey, page = 1) {
  try {
    const url = new URL(PEXELS_URL);
    url.search = new URLSearchParams({
      query,
      per_page: "5",
      page: String(Math.max(1, Math.min(3, Number(page) || 1))),
      orientation: "landscape",
    }).toString();
    const response = await fetch(url, {
      headers: { Authorization: pexelsKey },
    });
    if (!response.ok) return [];
    return ((await response.json())?.photos || []).map((photo) => ({
      id: String(photo.id || ""),
      query,
      alt: String(photo.alt || "").slice(0, 240),
      url:
        photo?.src?.large2x ||
        photo?.src?.large ||
        photo?.src?.medium ||
        "",
    }));
  } catch {
    return [];
  }
}

async function rankPexelsCandidates(
  article,
  candidates,
  deepseekKey,
  env,
  usage = null,
) {
  if ((!deepseekKey && !env?.AI) || candidates.length < 2) return [];
  try {
    const result = await runBasicJsonModel(
      [
        {
          role: "system",
          content:
            "Return JSON only. Select 2-3 Pexels photos that are clearly relevant to the supplied Chinese article. Judge using each search query and photo alt text. Prefer different visual angles tied to the event subject, place or industry. Reject generic filler, misleading people/places and any image that could imply an unsupported exact event. If fewer than 2 are genuinely relevant, return only the relevant ones. Return {\"selected_ids\":[\"\"]}.",
        },
        {
          role: "user",
          content:
            "Article title: " +
            String(article.title || "") +
            "\nTrack: " +
            String(article.track || "") +
            "\nEditorial angle: " +
            String(article.writing_angle || "") +
            "\nArticle excerpt: " +
            stripHighlightMarkup(article.body).slice(0, 900) +
            "\nCandidates: " +
            JSON.stringify(
              candidates.map(({ id, query, alt }) => ({ id, query, alt })),
            ),
        },
      ],
      deepseekKey,
      0.1,
      env,
      usage,
    );
    const selectedIds = new Set(
      (Array.isArray(result.selected_ids) ? result.selected_ids : [])
        .map(String)
        .slice(0, 3),
    );
    return candidates.filter((candidate) => selectedIds.has(candidate.id));
  } catch {
    return [];
  }
}

async function pexelsImages(
  article,
  pexelsKey,
  deepseekKey,
  env,
  page = 1,
  usage = null,
) {
  if (!pexelsKey) return normalizeImageUrls([], article.cover_url);
  const queries = await imageSearchQueries(
    article,
    deepseekKey,
    env,
    usage,
  );
  const groups = await Promise.all(
    queries.map((query) => pexelsSearch(query, pexelsKey, page)),
  );
  const candidates = [];
  const candidateIds = new Set();
  for (const photo of groups.flatMap((group) => group.slice(0, 3))) {
    if (!photo.url || candidateIds.has(photo.id)) continue;
    candidates.push(photo);
    candidateIds.add(photo.id);
  }
  const ranked = await rankPexelsCandidates(
    article,
    candidates,
    deepseekKey,
    env,
    usage,
  );
  if (ranked.length)
    return normalizeImageUrls(ranked.map((photo) => photo.url));

  const selected = [];
  const usedIds = new Set();
  for (const group of groups) {
    const photo = group.find(
      (candidate) =>
        candidate.url &&
        !usedIds.has(candidate.id) &&
        !selected.includes(candidate.url),
    );
    if (!photo) continue;
    selected.push(photo.url);
    usedIds.add(photo.id);
  }
  if (selected.length < 3) {
    for (const photo of groups.flat()) {
      if (
        !photo.url ||
        usedIds.has(photo.id) ||
        selected.includes(photo.url)
      )
        continue;
      selected.push(photo.url);
      usedIds.add(photo.id);
      if (selected.length === 3) break;
    }
  }
  return normalizeImageUrls(selected);
}

const API_KEY_CONFIG = {
  deepseek: { config: "DEEPSEEK_API_KEY", name: "DeepSeek" },
  tavily: { config: "TAVILY_API_KEY", name: "Tavily" },
  bocha: { config: "BOCHA_API_KEY", name: "博查" },
  pexels: { config: "PEXELS_API_KEY", name: "Pexels" },
};

async function validateApiKey(provider, key) {
  const label = API_KEY_CONFIG[provider]?.name || provider;
  if (!key) return { ok: false, provider, message: "未配置" };
  try {
    let response;
    let responseData = null;
    if (provider === "deepseek") {
      response = await fetch(DEEPSEEK_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${key}`,
        },
        body: JSON.stringify({
          model: DEEPSEEK_MODEL,
          messages: [{ role: "user", content: '只返回 JSON：{"ok":true}' }],
          thinking: { type: "disabled" },
          temperature: 0,
          max_tokens: 12,
          response_format: { type: "json_object" },
        }),
      });
      responseData = await response.clone().json().catch(() => null);
    } else if (provider === "tavily") {
      response = await fetch(TAVILY_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${key}`,
        },
        body: JSON.stringify({
          query: "FlowX API connection test",
          search_depth: "basic",
          max_results: 1,
          include_answer: false,
          api_key: key,
        }),
      });
    } else if (provider === "bocha") {
      response = await fetch(BOCHA_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${key}`,
        },
        body: JSON.stringify({ query: "FlowX", summary: false, count: 1 }),
      });
    } else if (provider === "pexels") {
      response = await fetch(`${PEXELS_URL}?query=nature&per_page=1`, {
        headers: { Authorization: key },
      });
    }
    if (response?.ok) return { ok: true, provider, message: "连接正常" };
    const status = response?.status || 0;
    const message =
      provider === "deepseek" && status === 402
        ? "余额不足或账户欠费"
        : status === 401 || status === 403
        ? "Key 无效或无权限"
        : status === 429
          ? "额度或频率已受限"
          : responseData?.error?.message ||
            `连接失败（HTTP ${status || "未知"}）`;
    return { ok: false, provider, message };
  } catch {
    return { ok: false, provider, message: `${label} 网络连接失败` };
  }
}

async function validateStoredApiKeys(env, email) {
  return Promise.all(
    Object.entries(API_KEY_CONFIG).map(async ([provider, config]) =>
      validateApiKey(provider, await getConfig(env, email, config.config)),
    ),
  );
}

function parseJsonModelResponse(raw) {
  const source = String(raw || "")
    .replace(/<think>[\s\S]*?<\/think>/g, "")
    .replace(/^```json\s*|\s*```$/g, "")
    .trim();
  try {
    return JSON.parse(source || "{}");
  } catch {
    const start = source.indexOf("{");
    const end = source.lastIndexOf("}");
    if (start >= 0 && end > start)
      return JSON.parse(source.slice(start, end + 1));
    throw new Error("模型没有返回有效 JSON");
  }
}

function providerErrorMessage(status, data) {
  if (status === 401 || status === 403)
    return "DeepSeek Key 无效，请到设置中重新填写并测试连接";
  if (status === 402)
    return "DeepSeek 余额不足或账户欠费";
  if (status === 429) return "DeepSeek 请求过于频繁或额度已受限";
  return data?.error?.message || `DeepSeek 调用失败：HTTP ${status}`;
}

async function runDeepSeekJson(messages, key, temperature = 0.7, usage = null) {
  if (!key) throw new Error("DeepSeek 未配置");
  let lastError = new Error("DeepSeek 调用失败");
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        DEEPSEEK_URL,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${key}`,
          },
          body: JSON.stringify({
            model: DEEPSEEK_MODEL,
            messages,
            thinking: { type: "disabled" },
            temperature,
            response_format: { type: "json_object" },
          }),
        },
        45000,
      );
      const data = await response.json();
      if (response.ok) {
        if (usage) usage.deepseek = Number(usage.deepseek || 0) + 1;
        return parseJsonModelResponse(
          data?.choices?.[0]?.message?.content || "{}",
        );
      }
      lastError = new Error(providerErrorMessage(response.status, data));
      if (
        attempt === 0 &&
        (response.status === 429 || response.status >= 500)
      ) {
        await new Promise((resolve) => setTimeout(resolve, 700));
        continue;
      }
      break;
    } catch (error) {
      lastError = error;
      if (attempt === 0) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        continue;
      }
    }
  }
  throw lastError;
}

async function runBasicJsonModel(
  messages,
  key,
  temperature = 0.7,
  env = null,
  usage = null,
) {
  let workersAiError = env?.AI
    ? null
    : new Error("Cloudflare Workers AI 未绑定");
  if (env?.AI) {
    try {
      const result = await env.AI.run(WORKERS_AI_MODEL, {
        messages,
        temperature,
        max_tokens: 4096,
        response_format: { type: "json_object" },
      });
      const parsed = parseJsonModelResponse(result?.response || result);
      if (usage) usage.workers_ai = Number(usage.workers_ai || 0) + 1;
      return parsed;
    } catch (error) {
      workersAiError = error;
      console.warn(
        JSON.stringify({
          event: "flowx_model_fallback",
          from: "cloudflare_workers_ai",
          to: "deepseek",
          error: error.message || "未知错误",
        }),
      );
    }
  }

  try {
    return await runDeepSeekJson(messages, key, temperature, usage);
  } catch (deepseekError) {
    throw new Error(
      `Cloudflare Workers AI 基础任务未成功：${workersAiError?.message || "未知错误"}；DeepSeek 基础任务兜底也未成功：${deepseekError.message || "未知错误"}`,
    );
  }
}

function stripHighlightMarkup(body) {
  return String(body || "").replace(/\*\*([^*\n]+)\*\*/g, "$1");
}

function stripSectionLabel(text, labelPattern) {
  return String(text || "")
    .replace(labelPattern, "")
    .trim();
}

function introSplitPoint(text) {
  if (text.length <= 100) return text.length;
  let split = 0;
  for (const match of text.matchAll(/[。！？]/g)) {
    const position = match.index + 1;
    if (position > 100) break;
    if (position >= 40) split = position;
  }
  return split || 100;
}

function ensureArticleStructure(body) {
  const plain = stripHighlightMarkup(body).trim();
  if (!plain) return "";
  const paragraphs = plain
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  const first = stripSectionLabel(
    paragraphs.shift() || "",
    /^(?:【?导语】?|内容提要|摘要)\s*[：:]?\s*/,
  );
  const splitAt = introSplitPoint(first);
  const intro = first.slice(0, splitAt).trim();
  const introRemainder = first.slice(splitAt).trim();
  if (introRemainder) paragraphs.unshift(introRemainder);

  let expert = paragraphs.length ? paragraphs.pop() : "";
  expert = stripSectionLabel(
    expert,
    /^(?:【?专家点评】?|行业点评|专家评论|总结评论|总结与展望|专家认为|专家指出|专家表示|业内专家认为)\s*[，,:：]?\s*/,
  );
  if (expert && !/^(?:客观看来|长远来看|长远看来|在我看来|更值得关注的是)[，,:：]/.test(expert)) {
    const opening = /未来|长期|长远|趋势|接下来/.test(expert)
      ? "长远来看，"
      : /影响|风险|变化|数据|竞争|机会/.test(expert)
        ? "客观看来，"
        : "在我看来，";
    expert = opening + expert;
  }
  const middle = paragraphs.filter(Boolean);
  return [
    `导语：${intro}`,
    ...middle,
    expert,
  ]
    .filter((part) => part.replace(/^导语[：:]\s*/, "").trim())
    .join("\n\n");
}

function articleStructure(body) {
  const paragraphs = stripHighlightMarkup(body)
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  const introMatch = (paragraphs[0] || "").match(/^导语[：:]\s*([\s\S]*)$/);
  const expertMatch = (paragraphs.at(-1) || "").match(
    /^(?:客观看来|长远来看|长远看来|在我看来|更值得关注的是)[，,:：]\s*([\s\S]*)$/,
  );
  const content = paragraphs
    .join("")
    .replace(/^导语[：:]/, "")
    .replace(/\s/g, "");
  return {
    length: content.length,
    intro: String(introMatch?.[1] || "").replace(/\s/g, ""),
    expert: String(expertMatch?.[1] || "").replace(/\s/g, ""),
  };
}

function insertAnalysisBeforeClosing(body, addition) {
  const structured = ensureArticleStructure(body);
  const paragraphs = structured
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  const closing = paragraphs.length > 1 ? paragraphs.pop() : "";
  const cleanAddition = stripHighlightMarkup(addition)
    .replace(
      /^(?:【?补充分析】?|补充正文|正文补充|导语|结语|总结)\s*[：:]?\s*/,
      "",
    )
    .trim();
  if (!cleanAddition) return structured;
  return [...paragraphs, cleanAddition, closing].filter(Boolean).join("\n\n");
}

async function expandDraftToMinimum(
  draft,
  material,
  track,
  key,
  usage,
  originalMessages,
) {
  let body = ensureArticleStructure(draft.body);
  for (
    let attempt = 0;
    attempt < 2 && articleStructure(body).length < ARTICLE_MIN_CHARACTERS;
    attempt += 1
  ) {
    const missing = ARTICLE_MIN_CHARACTERS - articleStructure(body).length;
    const expanded = await runDeepSeekJson(
      [
        {
          role: "system",
          content: `你是中文内容平台资深编辑，只返回JSON。当前${track}稿件篇幅不足。只补充能支撑文章核心观点的事实分析，不要重写导语，不要写结语，不要虚构资料外的数字、日期、人物、机构或结论。禁止逐句改写资料、堆砌背景或重复已有正文，要补足影响链条、利益关系、反常识之处或趋势信号。`,
        },
        {
          role: "user",
          content: `稿件还缺至少${Math.max(220, missing + 100)}个中文汉字。围绕已有观点补足最有价值的一层分析，返回 {\"addition\":\"\"}。\n已有正文：${stripHighlightMarkup(body).slice(0, 2000)}\n资料：${material.slice(0, 3600)}`,
        },
      ],
      key,
      0.45,
      usage,
    );
    body = insertAnalysisBeforeClosing(
      body,
      expanded.addition || expanded.body || "",
    );
  }
  if (articleStructure(body).length >= ARTICLE_MIN_CHARACTERS)
    return { ...draft, body };
  console.warn(
    JSON.stringify({
      event: "flowx_deepseek_draft_retry",
      model: DEEPSEEK_MODEL,
      reason: `article_below_${ARTICLE_MIN_CHARACTERS}_characters`,
    }),
  );
  return runDeepSeekJson(originalMessages, key, 0.8, usage);
}

async function repairDraftIntegrity(
  draft,
  material,
  track,
  key,
  usage,
  originalMessages,
) {
  let current = draft;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    current = await expandDraftToMinimum(
      current,
      material,
      track,
      key,
      usage,
      originalMessages,
    );
    const body = finalizeArticleBody(current.body);
    const unsupportedNumbers = unsupportedArabicNumbers(body, material);
    const verbatimMatches = longVerbatimMatches(body, material);
    if (!unsupportedNumbers.length && !verbatimMatches.length)
      return { ...current, body };

    current = {
      ...current,
      ...(await runDeepSeekJson(
        [
          {
            role: "system",
            content: `你是中文内容平台的原创性与事实编辑，只返回JSON。保持${track}稿件已经确定的核心角度，但必须整体重新组织有问题的段落，不能用同义词逐句替换。删除资料中不存在的数字、比例、金额、日期、统计区间和测算，不得添加任何新数字。与资料连续重复的表达要改成基于事实的独立分析。全文仍须为600到1000字，保留100字内导语、2到3层观点推进、自然观点收束及3到6处 **重点内容**。`,
          },
          {
            role: "user",
            content: `发现的问题：${[
              unsupportedNumbers.length
                ? `资料外数字：${unsupportedNumbers.join("、")}`
                : "",
              verbatimMatches.length
                ? `${verbatimMatches.length}处连续表达与资料重复`
                : "",
            ]
              .filter(Boolean)
              .join("；")}\n当前角度：${String(current.angle || "")}\n当前标题：${String(current.title || "")}\n当前正文：${body}\n参考资料：${material.slice(0, 4200)}\n返回 {"angle":"","title":"","body":""}。`,
          },
        ],
        key,
        0.45,
        usage,
      )),
    };
  }
  return current;
}

function shortenParagraph(text, limit) {
  const source = String(text || "").trim();
  if (source.length <= limit) return source;
  if (limit <= 0) return "";
  const candidate = source.slice(0, Math.max(1, limit - 1)).trimEnd();
  const minimumBoundary = Math.min(60, Math.floor(candidate.length * 0.6));
  let boundary = 0;
  for (const match of candidate.matchAll(/[。！？；]/g)) {
    const position = match.index + 1;
    if (position >= minimumBoundary) boundary = position;
  }
  const shortened = (boundary ? candidate.slice(0, boundary) : candidate)
    .replace(/[，、：；\s]+$/g, "")
    .trim();
  return shortened && !/[。！？]$/.test(shortened)
    ? `${shortened}。`
    : shortened;
}

function enforceArticleMaxLength(body, maxLength = ARTICLE_MAX_CHARACTERS) {
  const structured = ensureArticleStructure(body);
  if (articleStructure(structured).length <= maxLength) return structured;

  const paragraphs = structured
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  const intro = paragraphs.shift() || "";
  let expert = paragraphs.pop() || "";
  expert = shortenParagraph(expert, 280);

  const fixedLength = articleStructure(`${intro}\n\n${expert}`).length;
  let remaining = Math.max(0, maxLength - fixedLength);
  const middle = [];
  for (const paragraph of paragraphs) {
    const paragraphLength = paragraph.replace(/\s/g, "").length;
    if (paragraphLength <= remaining) {
      middle.push(paragraph);
      remaining -= paragraphLength;
      continue;
    }
    const shortened = shortenParagraph(paragraph, remaining);
    if (shortened) middle.push(shortened);
    break;
  }

  let result = [intro, ...middle, expert].filter(Boolean).join("\n\n");
  while (articleStructure(result).length > maxLength) {
    const overflow = articleStructure(result).length - maxLength;
    if (middle.length) {
      const last = middle.length - 1;
      middle[last] = shortenParagraph(
        middle[last],
        Math.max(0, middle[last].length - overflow - 1),
      );
      if (!middle[last]) middle.pop();
    } else {
      expert = shortenParagraph(
        expert,
        Math.max(80, expert.length - overflow - 1),
      );
    }
    result = [intro, ...middle, expert].filter(Boolean).join("\n\n");
  }
  return result;
}

function finalizeArticleBody(body) {
  return ensureHighlights(enforceArticleMaxLength(body));
}

function ensureHighlights(body) {
  const source = String(body || "").trim();
  const existing = [...source.matchAll(/\*\*([^*\n]{4,160})\*\*/g)];
  if (existing.length >= 3 && existing.length <= 6) return source;
  if (existing.length > 6) {
    let kept = 0;
    return source.replace(/\*\*([^*\n]+)\*\*/g, (_, text) =>
      kept++ < 6 ? `**${text}**` : text,
    );
  }

  const plain = stripHighlightMarkup(source);
  const candidates = [...plain.matchAll(/[^。！？\n]+[。！？]?/g)]
    .map((match, order) => {
      const raw = match[0];
      const leading = raw.length - raw.trimStart().length;
      const text = raw.trim();
      if (text.length < 16 || text.length > 120) return null;
      if (/^(?:导语[：:]|客观看来[，,:：]|长远来看[，,:：]|长远看来[，,:：]|在我看来[，,:：]|更值得关注的是[，,:：])/.test(text))
        return null;
      let score = 0;
      if (/\d|%|％|万|亿|元|年|月|日/.test(text)) score += 4;
      if (/核心|关键|重点|最重要|意味着|因此|由此|结论|需要|应当|必须|建议|避免|将会|预计|数据显示|值得注意/.test(text))
        score += 3;
      if (/但是|然而|同时|其中|相比|超过|下降|增长|影响|风险|机会/.test(text))
        score += 2;
      return { start: match.index + leading, text, score, order };
    })
    .filter(Boolean);
  const desired = Math.min(5, Math.max(3, Math.ceil(candidates.length / 3)));
  const ranked = [...candidates].sort(
    (a, b) => b.score - a.score || a.start - b.start,
  );
  const picked = [];
  for (const candidate of ranked) {
    if (picked.some((item) => Math.abs(item.order - candidate.order) <= 1))
      continue;
    picked.push(candidate);
    if (picked.length >= desired) break;
  }
  for (const candidate of ranked) {
    if (picked.length >= Math.min(3, candidates.length)) break;
    if (!picked.includes(candidate)) picked.push(candidate);
  }
  const selected = picked.sort((a, b) => b.start - a.start);
  let highlighted = plain;
  for (const item of selected) {
    highlighted =
      highlighted.slice(0, item.start) +
      `**${item.text}**` +
      highlighted.slice(item.start + item.text.length);
  }
  return highlighted;
}

function normalizeTitleText(title) {
  return String(title || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function titleBigrams(title) {
  const normalized = normalizeTitleText(title);
  if (normalized.length < 2) return new Set(normalized ? [normalized] : []);
  return new Set(
    Array.from(
      { length: normalized.length - 1 },
      (_, index) => normalized.slice(index, index + 2),
    ),
  );
}

function titleSimilarity(candidate, sourceTitle) {
  const candidateText = normalizeTitleText(candidate);
  const sourceText = normalizeTitleText(sourceTitle);
  if (!candidateText || !sourceText) return 0;
  if (candidateText === sourceText) return 1;
  const candidateBigrams = titleBigrams(candidateText);
  const sourceBigrams = titleBigrams(sourceText);
  let intersection = 0;
  for (const gram of candidateBigrams) {
    if (sourceBigrams.has(gram)) intersection += 1;
  }
  const union = new Set([...candidateBigrams, ...sourceBigrams]).size || 1;
  const jaccard = intersection / union;
  const containment =
    candidateText.includes(sourceText) || sourceText.includes(candidateText)
      ? Math.min(candidateText.length, sourceText.length) /
        Math.max(candidateText.length, sourceText.length)
      : 0;
  return Math.max(jaccard, containment * 0.9);
}

function titleAppealScore(title) {
  let score = 0;
  if (/[？?：:]/.test(title)) score += 2;
  if (/\d|%|％/.test(title)) score += 1;
  if (/背后|为何|不只是|真正|关键|意味着|拐点|信号|代价|机会|谁在|怎么/.test(title))
    score += 3;
  if (/重磅|震惊|突发|最新消息|引发关注|网友热议|冲上热搜/.test(title))
    score -= 4;
  return score;
}

function rankedTitleCandidates(draft, sourceTitle) {
  const alternatives = Array.isArray(draft.alternative_titles)
    ? draft.alternative_titles
    : [];
  return [
    ...new Set(
      [draft.title, ...alternatives]
        .map((title) => String(title || "").trim())
        .filter((title) => title.length >= 8 && title.length <= 30),
    ),
  ]
    .map((title) => ({
      title,
      similarity: titleSimilarity(title, sourceTitle),
      appeal: titleAppealScore(title),
    }))
    .sort((a, b) => {
      const aSafe = a.similarity <= TITLE_SIMILARITY_LIMIT;
      const bSafe = b.similarity <= TITLE_SIMILARITY_LIMIT;
      if (aSafe !== bSafe) return aSafe ? -1 : 1;
      if (aSafe)
        return (
          b.appeal - a.appeal ||
          a.similarity - b.similarity ||
          a.title.length - b.title.length
        );
      return a.similarity - b.similarity || b.appeal - a.appeal;
    });
}

async function ensureDistinctTitle(
  draft,
  sourceTitle,
  key,
  usage = null,
) {
  let candidates = rankedTitleCandidates(draft, sourceTitle);
  if (candidates[0]?.similarity <= TITLE_SIMILARITY_LIMIT)
    return {
      ...draft,
      title: candidates[0].title,
      title_similarity: Number(candidates[0].similarity.toFixed(3)),
    };

  const rewritten = await runDeepSeekJson(
    [
      {
        role: "system",
        content:
          "你是内容平台标题编辑，只返回JSON。标题必须准确但不能复制、缩写或同义替换热点原标题。围绕文章独特观点重新命名，优先使用反差、影响、问题、信号、利益关系或未来变化制造阅读动力；不使用“重磅”“震惊”“引发关注”“网友热议”等模板化词语，不夸大、不写标题党，控制在8到30字。",
      },
      {
        role: "user",
        content: `热点原标题：${sourceTitle}\n文章角度：${String(draft.angle || "")}\n正文摘要：${stripHighlightMarkup(draft.body).slice(0, 600)}\n返回 {"title":"","alternative_titles":["",""]}。`,
      },
    ],
    key,
    0.75,
    usage,
  );
  candidates = rankedTitleCandidates(
    {
      title: rewritten.title,
      alternative_titles: [
        ...(Array.isArray(rewritten.alternative_titles)
          ? rewritten.alternative_titles
          : []),
        ...candidates.map((candidate) => candidate.title),
      ],
    },
    sourceTitle,
  );
  const selected = candidates[0];
  return {
    ...draft,
    title: selected?.title || String(draft.title || sourceTitle).slice(0, 30),
    title_similarity: Number(
      (selected ? selected.similarity : 1).toFixed(3),
    ),
  };
}

function longVerbatimMatches(body, sourceMaterial) {
  const source = normalizeTitleText(sourceMaterial);
  if (!source) return [];
  return [
    ...new Set(
      stripHighlightMarkup(body)
        .split(/[。！？\n]/)
        .map((sentence) => sentence.trim())
        .filter((sentence) => normalizeTitleText(sentence).length >= 24)
        .filter((sentence) =>
          source.includes(normalizeTitleText(sentence)),
        ),
    ),
  ].slice(0, 3);
}

function unsupportedArabicNumbers(body, sourceMaterial) {
  const sourceNumbers = new Set(
    String(sourceMaterial || "").match(/\d+(?:\.\d+)?/g) || [],
  );
  return [
    ...new Set(
      (stripHighlightMarkup(body).match(/\d+(?:\.\d+)?/g) || []).filter(
        (number) => !sourceNumbers.has(number),
      ),
    ),
  ].slice(0, 6);
}

function actualAiProblems(value) {
  const statements = Array.isArray(value) ? value.map(String) : [];
  return statements.filter((statement) => {
    const hasDefect =
      /但|不过|问题|不足|缺|未提供|无来源|建议|风险|错误|不一致|复述|同义|过于|编造|夸大|空泛|AI味明显/.test(
        statement,
      );
    const positiveOnly =
      /符合要求|差异明显|有吸引力|有独特观点|逻辑清晰|事实一致|无明显AI味|未使用|给出有增量/.test(
        statement,
      );
    return hasDefect || !positiveOnly;
  });
}

async function qualityCheck(article, key, env, usage = null) {
  const localProblems = [];
  const structureProblems = [];
  if (article.title.length > 30)
    localProblems.push(`标题过长（${article.title.length}字）`);
  if (article.title.length < 8)
    localProblems.push(`标题过短（${article.title.length}字）`);
  if (/重磅|震惊|突发|最新消息|引发关注|网友热议|冲上热搜/.test(article.title))
    localProblems.push("标题使用模板化或夸张表达，吸引力不够自然");
  if (article.origin_title) {
    const similarity = titleSimilarity(article.title, article.origin_title);
    if (similarity > TITLE_SIMILARITY_LIMIT)
      structureProblems.push(
        `标题与热点原标题过于相似（相似度${Math.round(similarity * 100)}%），需要换一个观点角度`,
      );
    if (String(article.writing_angle || "").trim().length < 8)
      structureProblems.push("缺少明确、具体的差异化写作角度");
  }
  const verbatimMatches = longVerbatimMatches(
    article.body,
    article.source_material || "",
  );
  if (verbatimMatches.length)
    structureProblems.push(
      `正文存在${verbatimMatches.length}处与参考资料连续重复24字以上的表达，需要重新组织语言和论证`,
    );
  const unsupportedNumbers = unsupportedArabicNumbers(
    article.body,
    article.source_material || "",
  );
  if (article.source_material && unsupportedNumbers.length)
    structureProblems.push(
      `正文出现参考资料未提供的数字：${unsupportedNumbers.join("、")}，需要删除或改为不带数字的审慎分析`,
    );
  const structure = articleStructure(article.body);
  if (structure.length < ARTICLE_MIN_CHARACTERS)
    structureProblems.push(
      `正文过短（${structure.length}字，要求${ARTICLE_MIN_CHARACTERS}—${ARTICLE_MAX_CHARACTERS}字）`,
    );
  if (structure.length > ARTICLE_MAX_CHARACTERS)
    structureProblems.push(
      `正文过长（${structure.length}字，上限${ARTICLE_MAX_CHARACTERS}字）`,
    );
  if (!structure.intro)
    structureProblems.push("缺少文章导语");
  else if (structure.intro.length > 100)
    structureProblems.push(`导语过长（${structure.intro.length}字，要求100字以内）`);
  if (!structure.expert)
    structureProblems.push("缺少文章末尾的自然观点点评");
  else if (structure.expert.length < 60)
    structureProblems.push(`末尾观点点评过短（${structure.expert.length}字）`);
  if (/专家认为|专家指出|专家表示|业内专家|专家点评/.test(article.body))
    structureProblems.push("末尾观点表达过于学术化，请改用“客观看来”“长远来看 / 长远看来”或“在我看来”等自然表达");
  localProblems.push(...structureProblems);
  const highlightCount = [
    ...String(article.body || "").matchAll(/\*\*([^*\n]{4,160})\*\*/g),
  ].length;
  if (highlightCount < 3)
    localProblems.push(`核心信息加粗不足（当前${highlightCount}处）`);
  if (highlightCount > 6)
    localProblems.push(`核心信息加粗过多（当前${highlightCount}处）`);
  const ai = await runBasicJsonModel(
    [
      {
        role: "system",
        content:
          "你是中文内容平台资深审稿编辑。只返回JSON。正文中的 **...** 是重点加粗标记，不属于事实内容。重点检查稿件是否有清晰、具体、贯穿全文的独特观点，是否只是对热点报道逐段复述、调整语序或做同义词替换；检查标题是否与热点原标题有明显差异且准确、有阅读动力；检查正文是否围绕一个核心判断，用2到3层事实和分析推进，而不是罗列素材或空泛总结。首段导语须在100字内呈现核心观点；末段须以“客观看来”“长远来看”“长远看来”“在我看来”或“更值得关注的是”等自然语气给出有增量的判断。禁止使用“专家认为”“专家指出”“专家表示”“业内专家”“专家点评”等学术化表达。缺来源或未证实的问题只能建议删除、软化或去掉具体数字，禁止建议编造或补充来源。problems 数组只填写真实缺陷；符合要求的项目不要写入 problems。若没有问题，返回空数组。",
      },
      {
        role: "user",
        content: `检查稿件的差异化、观点价值、标题吸引力、逻辑、事实一致性、合规和AI味。请将稿件与参考资料比较，发现沿用资料句式、叙事顺序或逐段同义改写时明确指出。机器计算的标题相似度不超过55%时，不要报告“标题与热点原标题相似”。返回 {\"score\":0到100,\"problems\":[\"问题\"]}。\n热点原标题：${article.origin_title || "未提供"}\n机器标题相似度：${Math.round(Number(article.title_similarity || 0) * 100)}%\n选定角度：${article.writing_angle || "未提供"}\n稿件标题：${article.title}\n正文：${article.body}\n参考资料：${String(article.source_material || "未提供").slice(0, 3600)}`,
      },
    ],
    key,
    0.2,
    env,
    usage,
  );
  const adjustedScore = Math.max(
    0,
    Math.min(
      100,
      Math.round(Number(ai.score) || 75) - localProblems.length * 5,
    ),
  );
  const aiProblems = actualAiProblems(ai.problems);
  const severeAiProblems = aiProblems.filter((problem) =>
    /未提供来源|缺少来源|无来源|事实错误|事实不一致|编造|夸大|伪原创|逐段复述|同义改写|标题.*相似/.test(
      problem,
    ),
  );
  const score = structureProblems.length || severeAiProblems.length
    ? Math.min(59, adjustedScore)
    : adjustedScore;
  const problems = [
    ...new Set([
      ...localProblems,
      ...aiProblems,
    ]),
  ];
  return {
    score,
    level: score >= 80 ? "green" : score >= 60 ? "yellow" : "red",
    problems,
  };
}

async function articleId(title) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(title),
  );
  return [...new Uint8Array(digest)]
    .slice(0, 8)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function saveArticle(
  env,
  email,
  article,
  qc,
  oldId = null,
  originalCreatedAt = null,
) {
  article.body = finalizeArticleBody(article.body);
  if (articleStructure(article.body).length > ARTICLE_MAX_CHARACTERS)
    throw new Error(`正文不得超过${ARTICLE_MAX_CHARACTERS}字`);
  const id = await articleId(article.title);
  const status = qc.level === "red" ? "待修复" : "未发";
  article.image_urls = normalizeImageUrls(
    article.image_urls,
    article.cover_url,
  );
  article.cover_url = article.image_urls[0] || "";
  if (oldId && oldId !== id)
    await env.DB.prepare(
      "DELETE FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, oldId)
      .run();
  await env.DB.prepare(
    `INSERT INTO user_articles(owner_email,id,title,body,track,source,cover_url,image_urls,status,qc_score,qc_level,qc_problems,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,COALESCE(?,CURRENT_TIMESTAMP),CURRENT_TIMESTAMP)
    ON CONFLICT(owner_email,id) DO UPDATE SET title=excluded.title,body=excluded.body,track=excluded.track,source=excluded.source,cover_url=excluded.cover_url,image_urls=excluded.image_urls,status=excluded.status,qc_score=excluded.qc_score,qc_level=excluded.qc_level,qc_problems=excluded.qc_problems,updated_at=CURRENT_TIMESTAMP`,
  )
    .bind(
      email,
      id,
      article.title,
      article.body,
      article.track || "",
      article.source || "",
      article.cover_url || "",
      JSON.stringify(normalizeImageUrls(article.image_urls, article.cover_url)),
      status,
      qc.score,
      qc.level,
      JSON.stringify(qc.problems),
      originalCreatedAt,
    )
    .run();
  const { source_material: _sourceMaterial, ...publicArticle } = article;
  return {
    id,
    ...publicArticle,
    status,
    qc_score: qc.score,
    qc_level: qc.level,
    qc_problems: qc.problems,
  };
}

async function purgeExpiredContent(env) {
  const cutoff = `-${ARTICLE_RETENTION_HOURS} hours`;
  const results = await env.DB.batch([
    env.DB.prepare(
      `DELETE FROM user_publications
       WHERE NOT EXISTS (
         SELECT 1 FROM user_articles current
         WHERE current.owner_email=user_publications.owner_email
           AND current.id=user_publications.article_id
       ) OR EXISTS (
         SELECT 1 FROM user_articles a
         WHERE a.owner_email=user_publications.owner_email
           AND a.id=user_publications.article_id
           AND datetime(a.created_at) <= datetime('now', ?)
       )`,
    ).bind(cutoff),
    env.DB.prepare(
      `DELETE FROM user_publish_jobs
       WHERE NOT EXISTS (
         SELECT 1 FROM user_articles current
         WHERE current.owner_email=user_publish_jobs.owner_email
           AND current.id=user_publish_jobs.article_id
       ) OR EXISTS (
         SELECT 1 FROM user_articles a
         WHERE a.owner_email=user_publish_jobs.owner_email
           AND a.id=user_publish_jobs.article_id
           AND datetime(a.created_at) <= datetime('now', ?)
       )`,
    ).bind(cutoff),
    env.DB.prepare(
      "DELETE FROM user_articles WHERE datetime(created_at) <= datetime('now', ?)",
    ).bind(cutoff),
    env.DB.prepare(
      "DELETE FROM articles WHERE datetime(created_at) <= datetime('now', ?)",
    ).bind(cutoff),
    env.DB.prepare(
      "DELETE FROM user_hidden_topics WHERE datetime(hidden_at) <= datetime('now', ?)",
    ).bind(cutoff),
  ]);
  return results.reduce(
    (total, result) => total + Number(result?.meta?.changes || 0),
    0,
  );
}

async function generationStage(stage, action) {
  try {
    return await action();
  } catch (error) {
    const wrapped = new Error(`${stage}失败：${error.message || "未知错误"}`);
    wrapped.stage = stage;
    throw wrapped;
  }
}

function buildDraftMessages(topicTitle, track, material) {
  return [
    {
      role: "system",
      content: `你是有鲜明判断力的中文内容作者，当前赛道是${track}，只返回JSON。你的任务不是洗稿、伪原创或同义改写：事实来自资料，但标题、文章结构、段落次序和表达路径必须重新建立，严禁沿用任一来源的标题模板、叙事顺序、句式或逐段复述。先比较全部资料，从以下方向中选择最有增量且最适合本事件的一种切入：被忽视的利益关系、反常识变化、对普通人的实际影响、行业拐点、隐藏成本、竞争格局、政策执行落差或未来信号。用一句明确的核心观点统领全文，再用2到3层事实与分析推进；不能只总结“发生了什么”，必须回答“为什么值得关注、影响谁、接下来可能怎样”。事实不足时只能做有边界的分析，不能编造数字、机构、日期和来源；资料没有出现的比例、金额、日期、统计区间或测算结果一律不得写入，也不得自行换算或估算。正文净字数必须为600到1000个中文汉字，任何情况下不得超过1000字，建议控制在700到900字。首段必须以“导语：”开头，在100字内同时呈现事件和文章核心观点。末段体现${track}行业判断，可根据内容以“客观看来，”“长远来看，”“长远看来，”“在我看来，”或“更值得关注的是，”自然开头，给出有增量的总结、影响判断或趋势预测。严禁使用“专家认为”“专家指出”“专家表示”“业内专家”“专家点评”等学术化表达。推断必须明确为分析或预测。正文只将3到6处最重要的结论、关键数字或核心信息用 **重点内容** 标记，禁止整段加粗和空泛强调。`,
    },
    {
      role: "user",
      content: `热点原标题是“${topicTitle}”。先确定一个与现有报道明显不同、但有资料支撑的写作角度，再写一篇600到1000字、有观点、有阅读动力的完整中文文章。标题要准确、新颖、有吸引力，不能复制、缩写或同义替换热点原标题；同时给出两个同样准确但角度不同的备选标题，全部控制在8到30字，不使用“重磅”“震惊”“引发关注”“网友热议”等模板词。正文依次为100字内导语、围绕核心观点推进的2到3层事实与分析、自然语气的观点收束。不要按资料顺序复述，不要写成信息汇编。返回 {\"angle\":\"\",\"title\":\"\",\"alternative_titles\":[\"\",\"\"],\"body\":\"\"}。\n${material}`,
    },
  ];
}

async function generateOne(item, env, email) {
  const deepseekKey = await getConfig(env, email, "DEEPSEEK_API_KEY");
  const tavilyKey = await getConfig(env, email, "TAVILY_API_KEY");
  const bochaKey = await getConfig(env, email, "BOCHA_API_KEY");
  const pexelsKey = await getConfig(env, email, "PEXELS_API_KEY");
  if (!deepseekKey)
    throw new Error("请先在设置中配置并验证 DeepSeek 写稿 Key");
  if (!tavilyKey && !bochaKey)
    throw new Error("请至少配置并验证 Tavily 或博查搜索 Key");
  const draftingUsage = { workers_ai: 0, deepseek: 0 };
  const basicUsage = { workers_ai: 0, deepseek: 0 };
  const search = await generationStage("素材检索", () =>
    searchWithFallback(item.title, tavilyKey, bochaKey),
  );
  const material = search.results
    .map((r, i) => `【资料${i + 1}】${r.title || ""}\n${r.content || ""}`)
    .join("\n\n");
  if (!material.trim())
    throw new Error("搜索源没有返回可用素材，请检查 Tavily 或博查 Key");
  const track = TRACKS[item.track_key]?.name || item.track || "综合";
  const draftMessages = buildDraftMessages(item.title, track, material);
  let draft = await generationStage("正文生成", () =>
    runDeepSeekJson(
      draftMessages,
      deepseekKey,
      0.8,
      draftingUsage,
    ),
  );
  draft = await generationStage("正文扩写", () =>
    expandDraftToMinimum(
      draft,
      material,
      track,
      deepseekKey,
      draftingUsage,
      draftMessages,
    ),
  );
  draft = await generationStage("原创性复核", () =>
    repairDraftIntegrity(
      draft,
      material,
      track,
      deepseekKey,
      draftingUsage,
      draftMessages,
    ),
  );
  draft = await generationStage("差异化标题", () =>
    ensureDistinctTitle(draft, item.title, deepseekKey, draftingUsage),
  );
  const article = {
    title: String(draft.title || item.title)
      .trim()
      .slice(0, 60),
    body: finalizeArticleBody(draft.body),
    track,
    source: item.source || "",
    origin_title: item.title,
    writing_angle: String(draft.angle || "").trim().slice(0, 180),
    title_similarity: Number(draft.title_similarity || 0),
    source_material: material.slice(0, 4800),
    research_provider: search.provider,
    image_queries: [],
  };
  if (article.body.length < 50) throw new Error("模型返回正文过短");
  const qc = await generationStage("质量检查", () =>
    qualityCheck(article, deepseekKey, env, basicUsage),
  );
  article.image_urls = await pexelsImages(
    article,
    pexelsKey,
    deepseekKey,
    env,
    1,
    basicUsage,
  );
  article.cover_url = article.image_urls[0] || "";
  return {
    ...(await saveArticle(env, email, article, qc)),
    model_usage: {
      drafting: draftingUsage,
      basic: basicUsage,
    },
  };
}

async function handleApi(request, env, user) {
  const url = new URL(request.url);
  const path = url.pathname;
  const email = accountEmail(user);
  const contentMutation =
    request.method !== "GET" &&
    (/^\/api\/articles(?:\/|$)/.test(path) ||
      path === "/api/revise" ||
      path === "/api/publications" ||
      /^\/api\/publish-jobs(?:\/|$)/.test(path));
  if ((path === "/api/articles" && request.method === "GET") || contentMutation)
    await purgeExpiredContent(env);
  if (path === "/api/health")
    return json({
      ok: true,
      service: "FlowX Cloud",
      region: request.cf?.colo || "unknown",
    });
  if (path === "/api/me")
    return json({
      user,
      session_days: 30,
      auth: user?.emergency ? "basic" : "google",
    });

  if (path === "/api/settings" && request.method === "GET") {
    const rows = await env.DB.prepare(
      "SELECT key FROM user_config WHERE owner_email=?",
    )
      .bind(email)
      .all();
    const keys = new Set((rows.results || []).map((r) => r.key));
    let sources = DEFAULT_HOT_SOURCES;
    let tracks = Object.keys(TRACKS);
    try {
      sources =
        JSON.parse(
          (await getConfig(env, email, "HOTSPOT_SOURCES")) || "null",
        ) || sources;
    } catch {}
    try {
      tracks =
        JSON.parse((await getConfig(env, email, "ENABLED_TRACKS")) || "null") ||
        tracks;
    } catch {}
    return json({
      keys: {
        deepseek: keys.has("DEEPSEEK_API_KEY"),
        tavily: keys.has("TAVILY_API_KEY"),
        bocha: keys.has("BOCHA_API_KEY"),
        pexels: keys.has("PEXELS_API_KEY"),
      },
      hotspot: {
        sources,
        all_sources: Object.entries(HOT_SOURCES).map(([code, conf]) => ({
          code,
          name: conf.name,
          direct: Boolean(conf.direct),
        })),
        base_url:
          (await getConfig(env, email, "DAILYHOT_BASE_URL")) ||
          DEFAULT_DAILYHOT_URL,
      },
      tracks: Object.entries(TRACKS).map(([key, conf]) => ({
        key,
        name: conf.name,
        enabled: tracks.includes(key),
        keywords: conf.keywords,
      })),
    });
  }
  if (path === "/api/settings/keys" && request.method === "POST") {
    const body = await request.json();
    const submitted = Object.fromEntries(
      Object.keys(API_KEY_CONFIG)
        .map((provider) => [provider, String(body[provider] || "").trim()])
        .filter(([, value]) => value),
    );
    if (!Object.keys(submitted).length)
      return json({ error: "请至少填写一个需要更新的 Key" }, 400);
    const tests = await Promise.all(
      Object.entries(submitted).map(([provider, key]) =>
        validateApiKey(provider, key),
      ),
    );
    const invalid = tests.filter((test) => !test.ok);
    if (invalid.length)
      return json(
        {
          error: invalid
            .map(
              (test) =>
                `${API_KEY_CONFIG[test.provider].name}：${test.message}`,
            )
            .join("；"),
          tests,
        },
        400,
      );
    for (const [provider, key] of Object.entries(submitted))
      await setConfig(env, email, API_KEY_CONFIG[provider].config, key);
    return json({ ok: true, tests });
  }
  if (path === "/api/settings/test" && request.method === "POST")
    return json({ tests: await validateStoredApiKeys(env, email) });
  if (path === "/api/settings/preferences" && request.method === "POST") {
    const body = await request.json();
    if (Array.isArray(body.sources)) {
      const sources = DEFAULT_HOT_SOURCES.filter((code) =>
        body.sources.includes(code),
      );
      if (!sources.length) return json({ error: "至少保留一个热点来源" }, 400);
      await setConfig(env, email, "HOTSPOT_SOURCES", JSON.stringify(sources));
    }
    if (Array.isArray(body.tracks)) {
      const tracks = Object.keys(TRACKS).filter((code) =>
        body.tracks.includes(code),
      );
      if (!tracks.length) return json({ error: "至少保留一个赛道" }, 400);
      await setConfig(env, email, "ENABLED_TRACKS", JSON.stringify(tracks));
    }
    if (typeof body.base_url === "string") {
      try {
        const base = new URL(body.base_url.trim() || DEFAULT_DAILYHOT_URL);
        if (base.protocol !== "https:") throw new Error();
        await setConfig(
          env,
          email,
          "DAILYHOT_BASE_URL",
          base.origin + base.pathname.replace(/\/$/, ""),
        );
      } catch {
        return json({ error: "聚合服务地址必须是有效的 HTTPS URL" }, 400);
      }
    }
    return json({ ok: true });
  }
  if (path === "/api/hotspots" && request.method === "POST")
    return json(await fetchHotspots(env, email));
  if (path === "/api/hotspots/hide" && request.method === "POST") {
    const body = await request.json();
    const titles = Array.isArray(body.titles) ? body.titles : [];
    if (!titles.length) return json({ error: "请选择需要删除的热点" }, 400);
    const hidden = await hideTopics(env, email, titles, "manual");
    return json({ ok: true, hidden });
  }
  if (path === "/api/generate" && request.method === "POST") {
    const body = await request.json();
    const items = Array.isArray(body.items) ? body.items.slice(0, 20) : [];
    if (!items.length) return json({ error: "至少选择一个选题" }, 400);
    const results = new Array(items.length);
    let cursor = 0;
    const workerCount = Math.min(GENERATION_CONCURRENCY, items.length);
    await Promise.all(
      Array.from({ length: workerCount }, async () => {
        while (true) {
          const index = cursor++;
          if (index >= items.length) return;
          const item = items[index];
          try {
            results[index] = {
              ok: true,
              ...(await generateOne(item, env, email)),
            };
            await hideTopics(env, email, [item.title], "generated");
          } catch (error) {
            console.error(
              JSON.stringify({
                event: "flowx_generation_failed",
                owner: email,
                title: String(item.title || "").slice(0, 120),
                stage: error.stage || "生成",
                error: error.message || "未知错误",
              }),
            );
            results[index] = {
              ok: false,
              title: item.title,
              stage: error.stage || "生成",
              error: error.message,
            };
          }
        }
      }),
    );
    const modelUsage = results.reduce(
      (total, result) => {
        for (const task of ["drafting", "basic"]) {
          total[task].workers_ai += Number(
            result?.model_usage?.[task]?.workers_ai || 0,
          );
          total[task].deepseek += Number(
            result?.model_usage?.[task]?.deepseek || 0,
          );
        }
        return total;
      },
      {
        drafting: { workers_ai: 0, deepseek: 0 },
        basic: { workers_ai: 0, deepseek: 0 },
      },
    );
    return json({
      results,
      model_policy: {
        drafting: "deepseek",
        basic: "cloudflare_workers_ai",
      },
      basic_deepseek_fallback_used: modelUsage.basic.deepseek > 0,
      model_usage: modelUsage,
    });
  }
  if (path === "/api/articles" && request.method === "GET") {
    const rows = await env.DB.prepare(
      "SELECT *,datetime(created_at,'+36 hours') AS expires_at FROM user_articles WHERE owner_email=? ORDER BY created_at DESC LIMIT 500",
    )
      .bind(email)
      .all();
    return json({
      articles: (rows.results || []).map((article) => ({
        ...article,
        image_urls: normalizeImageUrls(
          article.image_urls,
          article.cover_url,
        ),
      })),
    });
  }
  if (path === "/api/publications" && request.method === "GET") {
    const rows = await env.DB.prepare(
      "SELECT article_id,platform,status,error,draft_link,updated_at FROM user_publications WHERE owner_email=? ORDER BY updated_at DESC LIMIT 1500",
    )
      .bind(email)
      .all();
    return json({ publications: rows.results || [] });
  }
  if (path === "/api/publications" && request.method === "POST") {
    const body = await request.json();
    const articleId = String(body.article_id || "").trim();
    const allowedPlatforms = new Set(["toutiao", "baijiahao", "zhihu"]);
    const allowedStatuses = new Set(["pending", "uploading", "done", "failed"]);
    const results = Array.isArray(body.results) ? body.results.slice(0, 3) : [];
    if (!/^[a-f0-9]+$/.test(articleId) || !results.length)
      return json({ error: "发布结果格式无效" }, 400);
    const article = await env.DB.prepare(
      "SELECT id FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, articleId)
      .first();
    if (!article) return json({ error: "稿件不存在" }, 404);
    const normalizedResults = results
      .map((result) => ({
        platform: String(result.platform || ""),
        status: String(result.status || "pending"),
        error: String(result.error || "").slice(0, 500),
        draftLink: String(result.draft_link || "").slice(0, 1000),
      }))
      .filter(
        (result) =>
          allowedPlatforms.has(result.platform) &&
          allowedStatuses.has(result.status),
      );
    const statements = normalizedResults.map((result) =>
      env.DB.prepare(
        `INSERT INTO user_publications(owner_email,article_id,platform,status,error,draft_link,updated_at)
         VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)
         ON CONFLICT(owner_email,article_id,platform) DO UPDATE SET
           status=excluded.status,error=excluded.error,draft_link=excluded.draft_link,updated_at=CURRENT_TIMESTAMP`,
      ).bind(
        email,
        articleId,
        result.platform,
        result.status,
        result.error,
        result.draftLink,
      ),
    );
    if (!statements.length) return json({ error: "没有可保存的平台结果" }, 400);
    if (normalizedResults.some((result) => result.status === "done"))
      statements.push(
        env.DB.prepare(
          "UPDATE user_articles SET status='已发',updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND id=?",
        ).bind(email, articleId),
      );
    await env.DB.batch(statements);
    return json({ ok: true });
  }
  if (path === "/api/publish-jobs" && request.method === "GET") {
    await env.DB.prepare(
      "UPDATE user_publish_jobs SET status='queued',error='上次执行中断，已重新排队',updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND status='running' AND updated_at < datetime('now','-3 minutes')",
    )
      .bind(email)
      .run();
    const rows = await env.DB.prepare(
      "SELECT id,article_id,platform,status,attempts,error,draft_link,created_at,updated_at FROM user_publish_jobs WHERE owner_email=? ORDER BY created_at DESC LIMIT 200",
    )
      .bind(email)
      .all();
    return json({ jobs: rows.results || [] });
  }
  if (path === "/api/publish-jobs" && request.method === "POST") {
    const body = await request.json();
    const articleIds = [
      ...new Set(
        (Array.isArray(body.article_ids)
          ? body.article_ids
          : [body.article_id]
        )
          .map((id) => String(id || "").trim())
          .filter((id) => /^[a-f0-9]+$/.test(id)),
      ),
    ].slice(0, 20);
    const allowedPlatforms = new Set(["toutiao", "baijiahao", "zhihu"]);
    const platforms = [
      ...new Set(
        (Array.isArray(body.platforms) ? body.platforms : [])
          .map(String)
          .filter((platform) => allowedPlatforms.has(platform)),
      ),
    ];
    if (!articleIds.length || !platforms.length)
      return json({ error: "请选择有效稿件和发布平台" }, 400);
    const placeholders = articleIds.map(() => "?").join(",");
    const articleRows = await env.DB.prepare(
      `SELECT id,status,qc_level,body FROM user_articles WHERE owner_email=? AND id IN (${placeholders})`,
    )
      .bind(email, ...articleIds)
      .all();
    const validArticles = articleRows.results || [];
    if (validArticles.length !== articleIds.length)
      return json({ error: "部分稿件不存在，请刷新后重试" }, 404);
    if (
      validArticles.some(
        (article) => article.status === "待修复" || article.qc_level === "red",
      )
    )
      return json({ error: "红档稿件不能进入发布队列" }, 400);
    if (validArticles.some((article) => article.status === "已发"))
      return json(
        { error: "部分稿件已发布；如需再次同步，请先将其改回未发" },
        400,
      );
    if (
      validArticles.some(
        (article) =>
          articleStructure(article.body).length > ARTICLE_MAX_CHARACTERS,
      )
    )
      return json(
        { error: `正文超过${ARTICLE_MAX_CHARACTERS}字，请先点击“稿件修改”后再发布` },
        400,
      );
    const platformPlaceholders = platforms.map(() => "?").join(",");
    const existingRows = await env.DB.prepare(
      `SELECT id,article_id,platform,status,attempts,error,draft_link,created_at,updated_at
       FROM user_publish_jobs
       WHERE owner_email=?
         AND article_id IN (${placeholders})
         AND platform IN (${platformPlaceholders})
         AND status IN ('queued','running')`,
    )
      .bind(email, ...articleIds, ...platforms)
      .all();
    const existingJobs = existingRows.results || [];
    const existingPairs = new Set(
      existingJobs.map((job) => `${job.article_id}:${job.platform}`),
    );
    const queueStartedAt = Date.now();
    const jobs = articleIds.flatMap((articleId, articleIndex) =>
      platforms
        .filter(
          (platform) => !existingPairs.has(`${articleId}:${platform}`),
        )
        .map((platform) => ({
          id: crypto.randomUUID(),
          article_id: articleId,
          platform,
          status: "queued",
          attempts: 0,
          error: "",
          draft_link: "",
          created_at: new Date(queueStartedAt + articleIndex).toISOString(),
          updated_at: new Date(queueStartedAt + articleIndex).toISOString(),
        })),
    );
    let createdCount = 0;
    if (jobs.length) {
      const insertResults = await env.DB.batch(
        jobs.map((job) =>
          env.DB.prepare(
            "INSERT OR IGNORE INTO user_publish_jobs(owner_email,id,article_id,platform,status,attempts,error,draft_link,created_at,updated_at) VALUES(?,?,?,?,?,0,'','',?,CURRENT_TIMESTAMP)",
          ).bind(
            email,
            job.id,
            job.article_id,
            job.platform,
            job.status,
            job.created_at,
          ),
        ),
      );
      createdCount = insertResults.reduce(
        (total, result) => total + Number(result.meta?.changes || 0),
        0,
      );
    }
    const activeRows = await env.DB.prepare(
      `SELECT id,article_id,platform,status,attempts,error,draft_link,created_at,updated_at
       FROM user_publish_jobs
       WHERE owner_email=?
         AND article_id IN (${placeholders})
         AND platform IN (${platformPlaceholders})
         AND status IN ('queued','running')`,
    )
      .bind(email, ...articleIds, ...platforms)
      .all();
    const allJobs = (activeRows.results || []).sort((a, b) => {
      const articleOrder =
        articleIds.indexOf(a.article_id) - articleIds.indexOf(b.article_id);
      return (
        articleOrder ||
        platforms.indexOf(a.platform) - platforms.indexOf(b.platform)
      );
    });
    return json({
      ok: true,
      jobs: allJobs,
      article_ids: articleIds,
      created_count: createdCount,
      reused_count: allJobs.length - createdCount,
    });
  }
  const publishJobMatch = path.match(
    /^\/api\/publish-jobs\/([0-9a-f-]+)(?:\/(retry))?$/,
  );
  if (publishJobMatch && request.method === "POST") {
    const jobId = publishJobMatch[1];
    const retry = publishJobMatch[2] === "retry";
    const job = await env.DB.prepare(
      "SELECT id,article_id,status FROM user_publish_jobs WHERE owner_email=? AND id=?",
    )
      .bind(email, jobId)
      .first();
    if (!job) return json({ error: "发布任务不存在" }, 404);
    if (retry) {
      await env.DB.prepare(
        "UPDATE user_publish_jobs SET status='queued',error='',draft_link='',updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND id=?",
      )
        .bind(email, jobId)
        .run();
      return json({ ok: true });
    }
    const body = await request.json();
    const allowedStatuses = new Set(["queued", "running", "done", "failed"]);
    const status = String(body.status || "");
    if (!allowedStatuses.has(status)) return json({ error: "任务状态无效" }, 400);
    const error = String(body.error || "").slice(0, 500);
    const draftLink = String(body.draft_link || "").slice(0, 1000);
    const updateJob = env.DB.prepare(
      `UPDATE user_publish_jobs SET status=?,error=?,draft_link=?,
       attempts=attempts+CASE WHEN ?='running' AND status!='running' THEN 1 ELSE 0 END,
       updated_at=CURRENT_TIMESTAMP
       WHERE owner_email=? AND id=?`,
    ).bind(status, error, draftLink, status, email, jobId);
    if (status === "done")
      await env.DB.batch([
        updateJob,
        env.DB.prepare(
          "UPDATE user_articles SET status='已发',updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND id=?",
        ).bind(email, job.article_id),
      ]);
    else await updateJob.run();
    return json({ ok: true });
  }
  const articleMatch = path.match(/^\/api\/articles\/([a-f0-9]+)$/);
  if (articleMatch && request.method === "PUT") {
    const old = await env.DB.prepare(
      "SELECT * FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, articleMatch[1])
      .first();
    if (!old) return json({ error: "稿件不存在" }, 404);
    const body = await request.json();
    const article = {
      title: String(body.title || "").trim(),
      body: finalizeArticleBody(body.body),
      track: old.track,
      source: old.source,
      cover_url: old.cover_url || "",
      image_urls: normalizeImageUrls(old.image_urls, old.cover_url),
    };
    if (article.title.length < 4 || article.body.length < 50)
      return json({ error: "标题至少4字，正文至少50字" }, 400);
    const key = await getConfig(env, email, "DEEPSEEK_API_KEY");
    const qc = await qualityCheck(article, key, env);
    return json({
      ok: true,
      ...(await saveArticle(
        env,
        email,
        article,
        qc,
        articleMatch[1],
        old.created_at,
      )),
    });
  }
  if (articleMatch && request.method === "DELETE") {
    await env.DB.prepare(
      "DELETE FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, articleMatch[1])
      .run();
    return json({ ok: true });
  }
  const coverMatch = path.match(
    /^\/api\/articles\/([a-f0-9]+)\/(?:images|cover)$/,
  );
  if (coverMatch && request.method === "POST") {
    const article = await env.DB.prepare(
      "SELECT id,title,body,track,source,cover_url,image_urls FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, coverMatch[1])
      .first();
    if (!article) return json({ error: "稿件不存在" }, 404);
    const pexelsKey = await getConfig(env, email, "PEXELS_API_KEY");
    if (!pexelsKey)
      return json({ error: "请先在设置中配置并验证 Pexels Key" }, 400);
    const deepseekKey = await getConfig(env, email, "DEEPSEEK_API_KEY");
    const imageUrls = await pexelsImages(
      article,
      pexelsKey,
      deepseekKey,
      env,
      1 + Math.floor(Math.random() * 3),
    );
    if (!imageUrls.length)
      return json({ error: "Pexels 暂未返回与主题相关的配图，请重试" }, 502);
    const coverUrl = imageUrls[0];
    await env.DB.prepare(
      "UPDATE user_articles SET cover_url=?,image_urls=?,updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND id=?",
    )
      .bind(coverUrl, JSON.stringify(imageUrls), email, article.id)
      .run();
    return json({ ok: true, cover_url: coverUrl, image_urls: imageUrls });
  }
  const statusMatch = path.match(/^\/api\/articles\/([a-f0-9]+)\/status$/);
  if (statusMatch && request.method === "POST") {
    const body = await request.json();
    if (!["未发", "已发", "待修复"].includes(body.status))
      return json({ error: "状态无效" }, 400);
    await env.DB.prepare(
      "UPDATE user_articles SET status=?,updated_at=CURRENT_TIMESTAMP WHERE owner_email=? AND id=?",
    )
      .bind(body.status, email, statusMatch[1])
      .run();
    return json({ ok: true });
  }
  if (path === "/api/revise" && request.method === "POST") {
    const body = await request.json();
    const old = await env.DB.prepare(
      "SELECT * FROM user_articles WHERE owner_email=? AND id=?",
    )
      .bind(email, body.id)
      .first();
    if (!old) return json({ error: "稿件不存在" }, 404);
    const key = await getConfig(env, email, "DEEPSEEK_API_KEY");
    if (!key)
      return json({ error: "请先在设置中配置并验证 DeepSeek 写稿 Key" }, 400);
    const problems = JSON.parse(old.qc_problems || "[]");
    const revisionMessages = [
      {
        role: "system",
        content:
          `你是有鲜明判断力的中文内容编辑，只返回JSON。根据问题重新组织稿件，不做逐句修补、同义替换或段落换序。先提炼一个更具体、更有增量的核心观点，再围绕该观点重建标题、导语和2到3层论证。缺来源只能删除、软化或去掉具体数字，绝不新增来源、机构、日期或数字；无法从原稿事实确认的比例、金额、日期、统计区间或测算结果必须删除，不得自行换算或估算。正文净字数必须为600到1000字，任何情况下不得超过1000字，建议控制在700到900字。标题须准确、新颖、有阅读动力，不使用“重磅”“震惊”“引发关注”“网友热议”等模板词。首段必须以“导语：”开头，在100字以内呈现事件和核心观点。末段要体现${old.track || "相关"}行业判断，给出有增量的总结、影响分析或趋势预测，但不要自称专家；根据内容以“客观看来，”“长远来看，”“长远看来，”“在我看来，”或“更值得关注的是，”自然开头。严禁使用“专家认为”“专家指出”“专家表示”“业内专家”“专家点评”等学术化表达。推断必须明确为分析或预测。只用 **重点内容** 标记3到6处最重要的结论、关键数字或核心信息，禁止整段加粗和空泛强调。`,
      },
      {
        role: "user",
        content: `完成事实修订，将全文调整为600到1000字，强化差异化角度、标题吸引力、核心观点、导语、论证推进、自然观点收束和重点加粗。返回 {\"angle\":\"\",\"title\":\"\",\"body\":\"\"}。\n问题：${problems.join("；")}\n原标题：${old.title}\n正文：${old.body}`,
      },
    ];
    let revised = await runDeepSeekJson(
      revisionMessages,
      key,
      0.4,
    );
    revised = await ensureDistinctTitle(revised, old.title, key);
    revised = await expandDraftToMinimum(
      revised,
      stripHighlightMarkup(old.body),
      old.track || "相关",
      key,
      null,
      revisionMessages,
    );
    const article = {
      title: String(revised.title || old.title).trim(),
      body: finalizeArticleBody(revised.body || old.body),
      track: old.track,
      source: old.source,
      origin_title: old.title,
      writing_angle: String(revised.angle || "").trim().slice(0, 180),
      title_similarity: Number(revised.title_similarity || 0),
      cover_url: old.cover_url || "",
      image_urls: normalizeImageUrls(old.image_urls, old.cover_url),
    };
    const qc = await qualityCheck(article, key, env);
    return json({
      ok: true,
      ...(await saveArticle(
        env,
        email,
        article,
        qc,
        old.id,
        old.created_at,
      )),
    });
  }
  return json({ error: "Not found" }, 404);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname.startsWith("/auth/"))
        return await handleAuth(request, env);
      const user = await readSession(request, env);
      if (!user)
        return url.pathname.startsWith("/api/")
          ? json(
              { error: "请先使用 Google 账号登录", login: "/auth/login" },
              401,
            )
          : loginPage(env);
      if (url.pathname.startsWith("/api/"))
        return await handleApi(request, env, user);
      return env.ASSETS.fetch(request);
    } catch (error) {
      return json({ error: error.message || "服务器错误" }, 500);
    }
  },
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(
      purgeExpiredContent(env).catch((error) =>
        console.error("FlowX 36-hour retention cleanup failed", error),
      ),
    );
  },
};
