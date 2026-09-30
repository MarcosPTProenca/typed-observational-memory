#!/usr/bin/env node
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const child = spawn(process.env.KIRO_CLI_CHAT || `${process.env.HOME}/.local/bin/kiro-cli-chat`, [
  "acp", "--agent-engine", "rust", "--trust-all-tools",
], { stdio: ["pipe", "pipe", "inherit"] });
const lines = createInterface({ input: child.stdout });
let nextId = 1;
const pending = new Map();
let sessionId;
let output = "";

lines.on("line", (line) => {
  let message;
  try { message = JSON.parse(line); } catch { return; }
  if (message.method === "session/update") {
    const update = message.params?.update;
    if (update?.sessionUpdate === "agent_message_chunk" && update.content?.type === "text") {
      output += update.content.text || "";
    }
    return;
  }
  const waiter = pending.get(message.id);
  if (!waiter) return;
  pending.delete(message.id);
  if (message.error) waiter.reject(new Error(message.error.message || "Kiro ACP error"));
  else waiter.resolve(message.result);
});

function request(method, params) {
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
}

async function start() {
  await request("initialize", {
    protocolVersion: 1,
    clientCapabilities: { fs: { readTextFile: false, writeTextFile: false }, terminal: false },
    clientInfo: { name: "tom-pi-bridge", version: "0.1.0" },
  });
  const session = await request("session/new", { cwd: process.cwd(), mcpServers: [] });
  sessionId = session.sessionId;
}

async function main() {
  await start();
  const input = createInterface({ input: process.stdin });
  for await (const line of input) {
    if (!line.trim()) continue;
    try {
      const requestBody = JSON.parse(line);
      output = "";
      await request("session/set_model", { sessionId, modelId: requestBody.model || "qwen3-coder-next" });
      await request("session/prompt", { sessionId, prompt: [{ type: "text", text: requestBody.prompt }] });
      process.stdout.write(JSON.stringify({ id: requestBody.id, answer: output }) + "\n");
    } catch (error) {
      process.stdout.write(JSON.stringify({ id: null, error: String(error) }) + "\n");
    }
  }
}

main().catch((error) => { console.error(error); process.exit(1); });
