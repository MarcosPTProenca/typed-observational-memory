import { mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type BridgeRequest = Record<string, unknown>;
type BridgeResponse = { ok: boolean; text?: string; error?: string };

const DB = ".pi/tom-memory.sqlite";
const BUDGET = Number(process.env.PI_TOM_CONTEXT_BUDGET ?? 2048);
const TIMEOUT_MS = Number(process.env.PI_TOM_TIMEOUT_MS ?? 30000);

function contentOf(content: unknown): string {
	if (typeof content === "string") return content;
	if (!Array.isArray(content)) return "";
	return content.map((part) => {
		if (typeof part === "string") return part;
		if (part && typeof part === "object" && "text" in part) return String(part.text);
		return "";
	}).join("\n").trim();
}

class PythonBridge {
	private child: ReturnType<typeof spawn> | undefined;
	private buffer = "";
	private busy: Promise<BridgeResponse> = Promise.resolve({ ok: true });
	private resolve: ((result: BridgeResponse) => void) | undefined;
	private timer: ReturnType<typeof setTimeout> | undefined;

	constructor(private readonly cwd: string) {}

	// Never rejects: on timeout/exit/bad-output it resolves { ok: false } so a
	// single failure can't poison the queue or surface as an extension error.
	call(request: BridgeRequest): Promise<BridgeResponse> {
		const run = () => new Promise<BridgeResponse>((resolve) => {
			if (!this.child) this.start();
			this.resolve = resolve;
			this.timer = setTimeout(
				() => this.settle({ ok: false, error: `TOM bridge timed out after ${TIMEOUT_MS}ms` }),
				TIMEOUT_MS,
			);
			try {
				this.child!.stdin!.write(`${JSON.stringify(request)}\n`);
			} catch (error) {
				this.settle({ ok: false, error: String(error) });
			}
		});
		this.busy = this.busy.then(run, run);
		return this.busy;
	}

	private settle(result: BridgeResponse) {
		if (this.timer) clearTimeout(this.timer);
		this.timer = undefined;
		const resolve = this.resolve;
		this.resolve = undefined;
		resolve?.(result);
	}

	close() { this.child?.kill(); this.child = undefined; }

	private start() {
		const interpreter = process.env.PI_TOM_PYTHON ?? (existsSync(join(this.cwd, ".venv/bin/python")) ? join(this.cwd, ".venv/bin/python") : "python3");
		this.child = spawn(interpreter, ["-u", "-m", "tom.pi_bridge", "--db", join(this.cwd, DB)], {
			cwd: this.cwd,
			env: { ...process.env, PYTHONPATH: join(this.cwd, "src"), PI_TOM_OBSERVER: process.env.PI_TOM_OBSERVER ?? "llm", PI_TOM_PROVIDER: process.env.PI_TOM_PROVIDER ?? "kiro", PI_TOM_MODEL: process.env.PI_TOM_MODEL ?? "qwen3-coder-next" },
		});
		this.child.stdout!.on("data", (chunk) => {
			this.buffer += String(chunk);
			let end = this.buffer.indexOf("\n");
			while (end >= 0) {
				const line = this.buffer.slice(0, end);
				this.buffer = this.buffer.slice(end + 1);
				if (line.trim()) {
					try {
						this.settle(JSON.parse(line) as BridgeResponse);
					} catch {
						this.settle({ ok: false, error: "TOM bridge sent malformed output" });
					}
				}
				end = this.buffer.indexOf("\n");
			}
		});
		this.child.on("error", (error) => this.settle({ ok: false, error: String(error) }));
		this.child.on("exit", (code) => {
			this.child = undefined;
			this.buffer = "";
			this.settle({ ok: false, error: `TOM bridge exited (${code})` });
		});
	}
}

export default function tomMemory(pi: ExtensionAPI) {
	let cwd = "";
	let bridge: PythonBridge;
	const sessionId = "pi";

	pi.on("session_start", async (_event, ctx) => {
		cwd = ctx.cwd;
		bridge = new PythonBridge(cwd);
		await mkdir(join(cwd, ".pi"), { recursive: true });
	});

	pi.on("session_shutdown", async () => {
		if (bridge && cwd) {
			await bridge.call({ command: "compact", session_id: sessionId, budget: BUDGET });
			bridge.close();
		}
	});

	pi.on("message_end", async (event) => {
		const message = event.message as { role?: string; content?: unknown };
		const text = contentOf(message.content);
		if (!cwd || !text || !["user", "assistant"].includes(message.role ?? "")) return;
		await bridge.call({
			command: "ingest",
			session_id: sessionId,
			events: [{
				id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
				type: message.role,
				content: text,
			}],
		});
	});

	pi.on("before_agent_start", async (event) => {
		if (!cwd) return;
		const result = await bridge.call({ command: "context", session_id: sessionId, query: event.prompt, budget: BUDGET });
		if (!result.text) return;
		return { systemPrompt: `${event.systemPrompt}\n\n## TOM memory\n${result.text}` };
	});

	pi.on("session_before_compact", async (event) => {
		if (!cwd) return;
		await bridge.call({ command: "compact", session_id: sessionId, budget: BUDGET });
		const context = await bridge.call({ command: "context", session_id: sessionId, query: "", budget: BUDGET });
		return {
			compaction: {
				summary: context.text || "TOM memory compacted; no durable memories were selected.",
				firstKeptEntryId: event.preparation.firstKeptEntryId,
				tokensBefore: event.preparation.tokensBefore,
			},
		};
	});

	pi.registerCommand("tom-memory", {
		description: "Show TOM integration status",
		handler: async (_args, ctx) => ctx.ui.notify(`TOM active: ${join(cwd, DB)}`, "info"),
	});
}
