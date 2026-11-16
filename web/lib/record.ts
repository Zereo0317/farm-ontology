import { spawn } from "node:child_process";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

export async function callRecord(payload: unknown): Promise<{ status: number; body: unknown }> {
  const child = spawn("python", ["-m", "farm_ontology.page_io"], {
    cwd: repoRoot,
    env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
    stdio: ["pipe", "pipe", "pipe"],
  });
  let out = "";
  let err = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    out += chunk;
  });
  child.stderr.on("data", (chunk) => {
    err += chunk;
  });
  const closed = new Promise<number>((resolve, reject) => {
    child.on("error", reject);
    child.on("close", (code) => resolve(code ?? 1));
  });
  child.stdin.write(JSON.stringify(payload));
  child.stdin.end();
  const code = await closed;
  if (!out.trim()) {
    return { status: 500, body: { error: err.trim() || "the record bridge returned nothing" } };
  }
  let body: unknown;
  try {
    body = JSON.parse(out);
  } catch {
    return { status: 500, body: { error: err.trim() || "the record bridge did not return JSON" } };
  }
  return { status: code === 0 ? 200 : 400, body };
}
