#!/usr/bin/env node
import readline from "node:readline";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";

const require = createRequire(import.meta.url);
const packageRoot = process.env.TOM_PI_PACKAGE_ROOT || execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
const { ModelRuntime } = await import(`${packageRoot}/@earendil-works/pi-coding-agent/dist/index.js`);
const runtime = await ModelRuntime.create({ refreshOnCreate: false });
const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let request;
  try {
    request = JSON.parse(line);
    if (!Number.isInteger(request.id) || typeof request.prompt !== "string") {
      throw new Error("request must contain integer id and string prompt");
    }
  } catch (error) {
    process.stdout.write(JSON.stringify({ id: null, error: `Invalid request: ${String(error)}` }) + "\n");
    continue;
  }
  try {
    const provider = request.provider || process.env.PI_PROVIDER || "openai-codex";
    const model = runtime.getModel(provider, request.model || process.env.PI_MODEL || "gpt-5.6-luna");
    if (!model) throw new Error("Codex model not found in pi model catalog");
    const response = await runtime.completeSimple(model, {
      systemPrompt: request.systemPrompt,
      messages: [{ role: "user", content: request.prompt, timestamp: Date.now() }],
      tools: [],
      timeoutMs: Number(process.env.TOM_CODEX_TIMEOUT_MS || 120000),
      maxRetries: 0,
    });
    const answer = response.content
      .filter((part) => part.type === "text")
      .map((part) => part.text)
      .join("");
    if (response.stopReason === "error" || response.stopReason === "aborted") {
      throw new Error(response.errorMessage || `Provider stopped with ${response.stopReason}`);
    }
    process.stdout.write(JSON.stringify({
      id: request.id,
      answer,
      usage: response.usage ?? null,
      model: response.model,
      provider: response.provider,
      responseId: response.responseId ?? null,
      stopReason: response.stopReason,
    }) + "\n");
  } catch (error) {
    process.stdout.write(JSON.stringify({ id: request.id, error: String(error) }) + "\n");
  }
}
