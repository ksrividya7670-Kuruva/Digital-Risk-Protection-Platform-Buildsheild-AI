export function notify(message: string, tone: "success" | "error" = "success") {
  window.dispatchEvent(
    new CustomEvent("brandshield:toast", { detail: { message, tone } }),
  );
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

export function displayName(name: string | null, username: string | null) {
  return name || (username ? `@${username.replace(/^@/, "")}` : "Unnamed entity");
}

export function safeWebUrl(value: string | null | undefined) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}
