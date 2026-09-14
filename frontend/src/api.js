const API = "";

export async function getMerchant() {
  const r = await fetch(`${API}/merchant`);
  return r.json();
}

export async function getScoreboard(params) {
  const q = new URLSearchParams(params);
  const r = await fetch(`${API}/scoreboard?${q}`);
  return r.json();
}

export async function getBudget() {
  const r = await fetch(`${API}/budget`);
  return r.json();
}

export async function getModel() {
  const r = await fetch(`${API}/model`);
  return r.json();
}

export async function nextPayment() {
  const r = await fetch(`${API}/demo/next`, { method: "POST" });
  if (!r.ok) throw new Error("demo next failed");
  return r.json();
}

export async function resetDemo() {
  const r = await fetch(`${API}/demo/reset`, { method: "POST" });
  return r.json();
}

export async function actOnCue(cueId) {
  const r = await fetch(`${API}/act`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cue_id: cueId }),
  });
  return r.json();
}

export function speakAmount(text) {
  try {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "hi-IN";
    u.rate = 0.95;
    const voices = window.speechSynthesis.getVoices();
    const hi = voices.find((v) => v.lang.startsWith("hi")) || voices.find((v) => /hindi/i.test(v.name));
    if (hi) u.voice = hi;
    window.speechSynthesis.speak(u);
  } catch {
    /* voice is optional */
  }
}
