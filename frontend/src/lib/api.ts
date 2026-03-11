const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    console.error(`[apiPost] Network error: ${path}`, e);
    throw new Error(`サーバーに接続できません (${API_BASE}${path})`);
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(`[apiPost] HTTP ${res.status}: ${path}`, text);
    throw new Error(`API error: ${res.status} - ${text || res.statusText}`);
  }
  return res.json();
}

export async function apiStreamChat(
  path: string,
  body: unknown,
  onChunk: (text: string) => void,
  onError: (error: string) => void,
  onDone: () => void,
) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) { onError(`API error: ${res.status}`); return; }
  const reader = res.body?.getReader();
  if (!reader) { onError("No stream"); return; }
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") { onDone(); return; }
      try {
        const evt = JSON.parse(payload);
        if (evt.error) { onError(evt.error); return; }
        if (evt.text) onChunk(evt.text);
      } catch { /* skip */ }
    }
  }
  onDone();
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
