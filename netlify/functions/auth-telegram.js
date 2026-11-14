// Проверка входа через Telegram Login Widget по алгоритму из документации Telegram:
// secret = SHA256(bot_token); hash = HMAC_SHA256(secret, data_check_string), где
// data_check_string — поля без hash, отсортированные по имени, в виде key=value через \n.
const crypto = require('crypto');
const { sign, json } = require('../lib/session');
exports.checkTelegram = (data, botToken, now = Date.now() / 1000) => {
  const { hash, ...fields } = data || {};
  if (!hash) return false;
  const check = Object.keys(fields).sort().map(k => `${k}=${fields[k]}`).join('\n');
  const secret = crypto.createHash('sha256').update(botToken).digest();
  const good = crypto.createHmac('sha256', secret).update(check).digest('hex');
  if (good.length !== hash.length || !crypto.timingSafeEqual(Buffer.from(good), Buffer.from(hash))) return false;
  return now - Number(fields.auth_date) < 86400; // данные входа действительны сутки
};
exports.handler = async event => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  const data = JSON.parse(event.body || '{}');
  if (!exports.checkTelegram(data, process.env.TELEGRAM_BOT_TOKEN || '')) return json(401, { error: 'invalid Telegram signature' });
  const user = { id: 't' + data.id, name: [data.first_name, data.last_name].filter(Boolean).join(' ') || data.username, username: data.username, picture: data.photo_url, provider: 'Telegram' };
  return json(200, { user, token: sign(user) });
};
