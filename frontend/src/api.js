async function parseError(r) {
  const text = await r.text()
  try {
    const data = JSON.parse(text)
    if (data && data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  } catch { /* not JSON */ }
  return text || `HTTP ${r.status}`
}

export async function getJSON(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(await parseError(r))
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await parseError(r))
  return r.json()
}
