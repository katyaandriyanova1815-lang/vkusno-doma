// Подписанная сессия: base64url(JSON) + "." + HMAC-SHA256 с секретом SESSION_SECRET.
const crypto = require('crypto');
const b64 = s => Buffer.from(s).toString('base64url');
const secret = () => { if (!process.env.SESSION_SECRET) throw new Error('SESSION_SECRET is not set'); return process.env.SESSION_SECRET; };
exports.sign = (user, days = 30) => {
  const body = b64(JSON.stringify({ user, exp: Math.floor(Date.now() / 1000) + days * 86400 }));
  return body + '.' + crypto.createHmac('sha256', secret()).update(body).digest('base64url');
};
exports.verify = token => {
  const [body, sig] = String(token).split('.');
  const good = crypto.createHmac('sha256', secret()).update(body || '').digest('base64url');
  if (!sig || sig.length !== good.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good))) return null;
  const data = JSON.parse(Buffer.from(body, 'base64url').toString());
  return data.exp > Date.now() / 1000 ? data.user : null;
};
exports.json = (status, obj) => ({ statusCode: status, headers: { 'Content-Type': 'application/json; charset=utf-8' }, body: JSON.stringify(obj) });
