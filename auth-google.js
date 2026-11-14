// Проверка входа через Google: токен ID проверяется на стороне Google (tokeninfo),
// затем сверяются получатель (aud = наш Client ID), издатель и подтверждённость почты.
const { sign, json } = require('../lib/session');
exports.handler = async event => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  const { credential } = JSON.parse(event.body || '{}');
  if (!credential) return json(400, { error: 'credential is required' });
  const r = await fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(credential));
  if (!r.ok) return json(401, { error: 'invalid token' });
  const p = await r.json();
  if (p.aud !== process.env.GOOGLE_CLIENT_ID) return json(401, { error: 'token issued for another app' });
  if (!['accounts.google.com', 'https://accounts.google.com'].includes(p.iss)) return json(401, { error: 'wrong issuer' });
  if (String(p.email_verified) !== 'true') return json(401, { error: 'email not verified' });
  const user = { id: 'g' + p.sub, name: p.name || p.email, email: p.email, picture: p.picture, provider: 'Google' };
  return json(200, { user, token: sign(user) });
};
