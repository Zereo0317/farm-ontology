/** Read an upstream JSON response without allowing unbounded buffering. */
export async function readBoundedJson<T>(response: Response, maxBytes = 64 * 1024): Promise<T> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("upstream JSON body is missing");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) {
        await reader.cancel();
        throw new Error("upstream JSON response exceeds size limit");
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as T;
  } catch (error) {
    if (error instanceof Error && error.message === "upstream JSON response exceeds size limit") throw error;
    throw new Error("upstream returned invalid JSON");
  } finally {
    reader.releaseLock();
  }
}
