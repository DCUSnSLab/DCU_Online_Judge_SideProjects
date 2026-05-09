const KEY = "lcr-requester";

export function getRequesterId(): string {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id =
      (typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`);
    localStorage.setItem(KEY, id);
  }
  return id;
}

/** Short label for UI ("req-3a7c..", first 6 chars after the prefix). */
export function shortRequesterLabel(id: string = getRequesterId()): string {
  return `req-${id.replace(/-/g, "").slice(0, 6)}`;
}
