'use strict';

/**
 * Cline worker: HTTP apvalkalas aplink `cline` CLI headless režimą.
 * Skirtas kviesti iš n8n (HTTP Request node) ar bet kurio kito orkestratoriaus.
 *
 *   POST /run   { "prompt": "...", "cwd": "projektas", "timeout": 900 }
 *   GET  /healthz
 *
 * Atsakymas: { ok, text, finishReason, iterations, usage, durationMs, model, stderr }
 */

const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { spawn, execFileSync } = require('node:child_process');

const isWin = process.platform === 'win32';

const PORT = Number(process.env.PORT || 7070);
const TOKEN = process.env.WORKER_TOKEN || '';
const CLINE_BIN = process.env.CLINE_BIN || 'cline';
// Windows: ~/.cline (ten tavo prisijungimas), Linux/Docker: /data/cline
const CLINE_CONFIG =
  process.env.CLINE_CONFIG || (isWin ? path.join(os.homedir(), '.cline') : '/data/cline');
const CLINE_DATA =
  process.env.CLINE_DATA_DIR || (isWin ? path.join(os.homedir(), '.cline', 'data') : '/data/cline/data');
const CLINE_PROVIDER = process.env.CLINE_PROVIDER || '';
const CLINE_MODEL = process.env.CLINE_MODEL || '';
const CLINE_API_KEY = process.env.CLINE_API_KEY || '';
const WORKSPACE_ROOT = process.env.WORKSPACE_ROOT || (isWin ? path.join(process.cwd(), 'work') : '/work');
const TASK_TIMEOUT = Number(process.env.TASK_TIMEOUT_SECONDS || 1800);
const RETRIES = Number(process.env.CLINE_RETRIES || 3);
const CLINE_THINKING = process.env.CLINE_THINKING || '';
const MAX_BODY = 1024 * 1024;

// Du autentifikavimo būdai:
//  - 'api-key'        – raktas per CLINE_API_KEY (OpenRouter / Gemini / Anthropic ...)
//  - 'mounted-config' – prisijungta `cline auth` (ClinePass / Cline account) ir
//                       konfigūracija įmontuota į /data/cline
const AUTH_MODE = CLINE_API_KEY ? 'api-key' : 'mounted-config';

// Windows: npm daro cline.cmd/.ps1, kurių negalima paleisti be shell'o.
// Todėl ieškome tikro JS įėjimo taško ir paleidžiame per node – jokių kabučių problemų.
function resolveCliEntry() {
  if (process.env.CLINE_CLI_ENTRY) return process.env.CLINE_CLI_ENTRY;
  const roots = [
    path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'cline'),
    path.join(process.env.LOCALAPPDATA || '', 'npm', 'node_modules', 'cline'),
    '/usr/local/lib/node_modules/cline',
    '/usr/lib/node_modules/cline',
  ];
  for (const dir of roots) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'));
      const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin && (pkg.bin.cline || Object.values(pkg.bin)[0]);
      if (!bin) continue;
      const entry = path.join(dir, bin);
      if (fs.existsSync(entry)) return entry;
    } catch {
      /* bandome toliau */
    }
  }
  return null;
}

const CLINE_ENTRY = resolveCliEntry();

function cliArgv(args) {
  return CLINE_ENTRY ? [process.execPath, [CLINE_ENTRY, ...args]] : [CLINE_BIN, args];
}

let clineVersion = 'nenustatytas';
try {
  const [file, args] = cliArgv(['--version']);
  clineVersion = execFileSync(file, args, {
    encoding: 'utf8',
    timeout: 20000,
    shell: !CLINE_ENTRY && isWin,
    windowsHide: true,
  })
    .trim()
    .split('\n')
    .pop()
    .trim();
} catch {
  clineVersion = 'nepaleidžiamas';
}



// Agentas valgo daug atminties -> vykdome po vieną užduotį.
let chain = Promise.resolve();

function enqueue(job) {
  const run = chain.then(job, job);
  chain = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

function resolveCwd(rawCwd) {
  const root = path.resolve(WORKSPACE_ROOT);
  const target = path.resolve(root, rawCwd || '.');
  if (target !== root && !target.startsWith(root + path.sep)) {
    throw new Error(`cwd turi būti ${root} viduje`);
  }
  if (!fs.existsSync(target)) fs.mkdirSync(target, { recursive: true });
  return target;
}

function buildArgs(prompt, cwd, timeout) {
  const args = [
    '--json',
    '--auto-approve',
    'true',
    '--config',
    CLINE_CONFIG,
    '--data-dir',
    CLINE_DATA,
    '-c',
    cwd,
    '-t',
    String(timeout),
    '--retries',
    String(RETRIES),
  ];
  if (CLINE_PROVIDER) args.push('-P', CLINE_PROVIDER);
  if (CLINE_MODEL) args.push('-m', CLINE_MODEL);
  if (CLINE_API_KEY) args.push('-k', CLINE_API_KEY);
  if (CLINE_THINKING) args.push('--thinking', CLINE_THINKING);
  args.push(prompt);
  return args;
}

function runCline({ prompt, cwd, timeout }) {
  return new Promise((resolve) => {
    const started = Date.now();
    const args = buildArgs(prompt, cwd, timeout);
    const [cliFile, cliArgs] = cliArgv(args);
    const child = spawn(cliFile, cliArgs, {
      cwd,
      env: { ...process.env, CI: '1', NO_COLOR: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
      // atskira procesų grupė (Linux): timeout'as nužudo ir agento paleistus vaikus
      detached: !isWin,
      windowsHide: true,
      shell: !CLINE_ENTRY && isWin,
    });

    let stderr = '';
    let result = null;
    let agentError = null;
    let killedByTimeout = false;
    let settled = false;
    let timer;

    const finish = (payload) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(payload);
    };

    const killTree = () => {
      if (isWin) {
        try {
          spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true });
        } catch {
          /* jau mirė */
        }
        return;
      }
      try {
        process.kill(-child.pid, 'SIGKILL');
      } catch {
        try {
          child.kill('SIGKILL');
        } catch {
          /* jau mirė */
        }
      }
    };

    timer = setTimeout(() => {
      killedByTimeout = true;
      killTree();
      finish({ ok: false, error: `timeout po ${timeout}s`, stderr: stderr.slice(-4000) });
    }, timeout * 1000);

    const buffers = { stdout: '', stderr: '' };

    // Cline rašo NDJSON į stdout, o klaidas – į stderr kaip {"type":"error",...}.
    const handleLine = (line, fromStderr) => {
      if (!line) return;
      let event = null;
      try {
        event = JSON.parse(line);
      } catch {
        event = null; // --verbose ar kiti ne-JSON intarpai
      }
      if (!event || !event.type) {
        if (fromStderr) stderr += `${line}\n`;
        return;
      }
      if (event.type === 'run_result') {
        result = event;
      } else if (event.type === 'agent_event' && event.event && event.event.type === 'error') {
        agentError = event.event.message || event.event.text || 'agent error';
      } else if (event.type === 'error') {
        agentError = event.message || 'error';
      }
    };

    const onData = (name, fromStderr) => (chunk) => {
      let buffer = buffers[name] + chunk.toString('utf8');
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        handleLine(buffer.slice(0, newlineIndex).trim(), fromStderr);
        buffer = buffer.slice(newlineIndex + 1);
      }
      buffers[name] = buffer;
    };

    child.stdout.on('data', onData('stdout', false));
    child.stderr.on('data', onData('stderr', true));

    child.on('error', (err) => {
      finish({ ok: false, error: `nepavyko paleisti ${CLINE_BIN}: ${err.message}` });
    });

    child.on('close', (code) => {
      // paskutinė eilutė be "\n" pabaigoje
      handleLine(buffers.stdout.trim(), false);
      handleLine(buffers.stderr.trim(), true);
      if (killedByTimeout) {
        return finish({ ok: false, error: `timeout po ${timeout}s`, stderr: stderr.slice(-4000) });
      }
      if (!result) {
        return finish({
          ok: false,
          error: agentError || 'agentas negrąžino run_result',
          exitCode: code,
          stderr: stderr.slice(-4000),
        });
      }
      finish({
        ok: code === 0 && result.finishReason === 'completed',
        exitCode: code,
        finishReason: result.finishReason || null,
        text: result.text || '',
        iterations: result.iterations != null ? result.iterations : null,
        usage: result.usage || null,
        model: result.model || null,
        durationMs: result.durationMs != null ? result.durationMs : Date.now() - started,
        error: result.finishReason === 'completed' ? undefined : agentError || `finishReason=${result.finishReason}`,
        stderr: stderr ? stderr.slice(-4000) : undefined,
      });
    });
  });
}


function send(res, status, payload) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        reject(new Error('body per didelis'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error('neteisingas JSON'));
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  if (req.method === 'GET' && url.pathname === '/healthz') {
    return send(res, 200, {
      ok: true,
      cline: CLINE_BIN,
      clineEntry: CLINE_ENTRY || '(bin iš PATH)',
      clineVersion,
      authMode: AUTH_MODE,
      provider: CLINE_PROVIDER || '(iš įmontuotos konfigūracijos)',
      model: CLINE_MODEL || '(iš įmontuotos konfigūracijos)',
      thinking: CLINE_THINKING || 'provider default',
      workspaceRoot: WORKSPACE_ROOT,
      timeoutSeconds: TASK_TIMEOUT,
    });
  }

  if (req.method !== 'POST' || url.pathname !== '/run') {
    return send(res, 404, { ok: false, error: 'not found' });
  }

  if (TOKEN && req.headers['x-worker-token'] !== TOKEN) {
    return send(res, 401, { ok: false, error: 'unauthorized' });
  }

  let body;
  try {
    body = await readBody(req);
  } catch (err) {
    return send(res, 400, { ok: false, error: err.message });
  }

  const prompt = typeof body.prompt === 'string' ? body.prompt.trim() : '';
  if (!prompt) return send(res, 400, { ok: false, error: 'prompt (string) privalomas' });

  let cwd;
  try {
    cwd = resolveCwd(body.cwd);
  } catch (err) {
    return send(res, 400, { ok: false, error: err.message });
  }

  const timeout = Number(body.timeout) > 0 ? Number(body.timeout) : TASK_TIMEOUT;
  try {
    const result = await enqueue(() => runCline({ prompt, cwd, timeout }));
    return send(res, result.ok ? 200 : 500, result);
  } catch (err) {
    return send(res, 500, { ok: false, error: err.message });
  }
});

server.listen(PORT, () => {
  console.log(`cline-worker klausosi :${PORT} (bin=${CLINE_BIN}, root=${WORKSPACE_ROOT})`);
});
