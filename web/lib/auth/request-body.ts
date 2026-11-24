export const MAX_FARM_JSON_BYTES = 64 * 1024;

export type JsonObjectResult =
  | { ok: true; value: Record<string, unknown> }
  | { ok: false; status: 400 | 413; reason: string };

/** Read a small JSON object without buffering an unbounded request body. */
export async function readJsonObject(
  request: Request,
  maxBytes = MAX_FARM_JSON_BYTES,
): Promise<JsonObjectResult> {
  const reader = request.body?.getReader();
  if (!reader) return { ok: false, status: 400, reason: "request body is required" };
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) {
        await reader.cancel();
        return { ok: false, status: 413, reason: "request body too large" };
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const parsed: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, status: 400, reason: "JSON object required" };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch {
    return { ok: false, status: 400, reason: "request body was not valid JSON" };
  } finally {
    reader.releaseLock();
  }
}
