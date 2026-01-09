/// <reference path="./react-shim.d.ts" />
import * as React from "react";
import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";

// react-shim 在部分环境下不包含 hooks 的类型声明，这里用 any 兜底避免 TS 报错
const useState = (React as any).useState as any;
const useEffect = (React as any).useEffect as any;

type IntentRouterProps = {
  status: "thinking" | "done" | "error";
  user_text?: string;
  intent?: string;
  route?: string;
  raw?: string;
  elapsed_s?: number | null;
  steps?: string[];
  active_step?: number;
};

type WorkflowNode = {
  node_code?: string;
  node_name?: string;
  node_status?: string;
  node_message?: string;
};

type ArticleWorkflowProps = {
  status: "running" | "done" | "error";
  run_id?: string | null;
  thread_id?: string | null;
  current_node?: string | null;
  flow_node_list?: WorkflowNode[];
  error_message?: string | null;
};

type ArticleClarifyProps = {
  status: "need_info" | "done" | "error";
  missing?: string[];
  question?: string;
  topic?: string;
  content_format?: string;
  target_audience?: string;
  tone?: string;
  tone_options?: string[];
};

type MCPOption = {
  code?: string;
  name?: string;
  desc?: string;
};

type SEOTaskEvidence = {
  evidence_path?: string;
  value_summary?: string;
};

type SEOTask = {
  date?: string;
  day_of_week?: string;
  category?: string;
  issue_type?: string;
  title?: string;
  description?: string;
  impact?: number;
  difficulty?: number;
  severity?: string;
  requires_manual_confirmation?: boolean;
  workflow_id?: string;
  params?: Record<string, any>;
  evidence?: SEOTaskEvidence[];
  fix_action?: "article" | "link" | "none";
  fix_prompt?: string;
};

type SEOWeeklyPlanData = {
  site_id?: string;
  week_start?: string;
  week_end?: string;
  tasks?: SEOTask[];
};

type SEOPlannerProps = {
  status: "loading" | "done" | "error";
  step?: string;
  user_text?: string;
  steps?: string[];
  active_step?: number;
  tasks?: SEOWeeklyPlanData | null;
  error_message?: string | null;
};

type MCPWorkflowProps = {
  status: "select" | "confirm" | "running" | "done" | "cancelled" | "error";
  title?: string;
  message?: string;
  options?: MCPOption[];
  selected?: MCPOption | null;
  recommended?: string | null;
  result?: string | null;
  company_name?: string | null;
  logo_url?: string | null;
};

const cssText = `
  .lgui-card { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji"; }
  .lgui-spin { animation: lgui-spin 0.9s linear infinite; }
  @keyframes lgui-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
`;

const Badge: React.FC<{ children?: React.ReactNode; tone?: "slate" | "blue" | "green" | "red" }> = ({
  children,
  tone = "slate",
}) => {
  const tones: Record<string, { bg: string; fg: string; bd: string }> = {
    slate: { bg: "#f1f5f9", fg: "#334155", bd: "#e2e8f0" },
    blue: { bg: "#eff6ff", fg: "#1d4ed8", bd: "#bfdbfe" },
    green: { bg: "#ecfdf5", fg: "#047857", bd: "#a7f3d0" },
    red: { bg: "#fff1f2", fg: "#be123c", bd: "#fecdd3" },
  };
  const t = tones[tone];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        borderRadius: 9999,
        padding: "2px 10px",
        fontSize: 11,
        lineHeight: "16px",
        color: t.fg,
        background: t.bg,
        border: `1px solid ${t.bd}`,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
};

const Spinner: React.FC = () => {
  return (
    <span
      className="lgui-spin"
      style={{
        display: "inline-block",
        width: 12,
        height: 12,
        borderRadius: "50%",
        border: "2px solid #dbeafe",
        borderTopColor: "#2563eb",
      }}
    />
  );
};

const IntentRouterCard: React.FC<IntentRouterProps> = (props) => {
  const statusTone = props.status === "thinking" ? "blue" : props.status === "done" ? "green" : "red";
  const statusLabel =
    props.status === "thinking" ? "正在识别意图…" : props.status === "done" ? "识别完成" : "识别失败";

  const elapsedLabel = (() => {
    const s = props.elapsed_s ?? null;
    if (s == null || Number.isNaN(s)) return null;
    const total = Math.round(s);
    const m = Math.floor(total / 60);
    const r = total % 60;
    if (m > 0) return `已思考 ${m}m ${r}s`;
    return `已思考 ${r}s`;
  })();

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 560,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>
            {elapsedLabel ? <span style={{ marginRight: 10, color: "#64748b" }}>{elapsedLabel}</span> : null}
            意图识别
          </div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={statusTone as any}>
              {props.status === "thinking" ? <Spinner /> : null}
              <span>{statusLabel}</span>
            </Badge>
            <span style={{ fontSize: 12, color: "#64748b" }}>
              路由到：{" "}
              <span style={{ fontWeight: 700, color: "#334155" }}>
                {props.route || (props.status === "thinking" ? "…" : "—")}
              </span>
            </span>
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>router</div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: 12, color: "#334155" }}>
          <span style={{ color: "#64748b" }}>intent：</span>{" "}
          <b>{props.intent || (props.status === "thinking" ? "…" : "—")}</b>
          <span style={{ marginLeft: 10, color: "#64748b" }}>route：</span>{" "}
          <b>{props.route || (props.status === "thinking" ? "…" : "—")}</b>
        </div>
      </div>

      {props.status === "done" ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #bbf7d0",
            background: "#ecfdf5",
            padding: 12,
            fontSize: 12,
            color: "#065f46",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span
            style={{
              width: 18,
              height: 18,
              borderRadius: 9,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              fontWeight: 700,
              background: "#86efac",
              color: "#052e16",
              flex: "0 0 auto",
            }}
          >
            ✓
          </span>
          <span>
            意图识别完成：<b>{props.intent || "—"}</b>，已路由到 <b>{props.route || "—"}</b>。
          </span>
        </div>
      ) : null}

      {props.status === "thinking" ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
            padding: 12,
            fontSize: 12,
            color: "#1e3a8a",
          }}
        >
          正在分析你的输入并选择最合适的处理路径（RAG / 文章生成 / 快捷指令）…
        </div>
      ) : null}

      {(props.user_text || props.raw) ? (
        <details
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #f1f5f9",
            padding: 12,
            background: "#ffffff",
          }}
        >
          <summary style={{ cursor: "pointer", userSelect: "none", fontSize: 11, fontWeight: 700, color: "#64748b" }}>
            更多信息
          </summary>
          {props.user_text ? (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b" }}>用户输入</div>
              <div style={{ marginTop: 6, fontSize: 12, color: "#334155", whiteSpace: "pre-wrap" }}>
                {props.user_text}
              </div>
            </div>
          ) : null}
          {props.raw ? (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b" }}>模型原始输出（调试）</div>
              <pre style={{ marginTop: 6, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, color: "#334155" }}>
                {props.raw}
              </pre>
            </div>
          ) : null}
        </details>
      ) : null}
    </div>
  );
};

const statusDot = (s?: string) => {
  const st = (s || "").toUpperCase();
  if (st === "RUNNING") return { bg: "#bfdbfe", fg: "#1d4ed8" };
  if (st === "SUCCESS" || st === "SUCCEEDED" || st === "DONE" || st === "COMPLETED")
    return { bg: "#bbf7d0", fg: "#047857" };
  if (st === "FAILED" || st === "ERROR") return { bg: "#fecdd3", fg: "#be123c" };
  return { bg: "#e2e8f0", fg: "#64748b" };
};

const ArticleWorkflowCard: React.FC<ArticleWorkflowProps> = (props) => {
  const badgeTone = props.status === "done" ? "green" : props.status === "error" ? "red" : "blue";
  const badgeLabel = props.status === "done" ? "已完成" : props.status === "error" ? "已失败" : "进行中";
  const nodes = props.flow_node_list || [];
  const current = props.current_node || "";

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 560,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>文章生成工作流</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={badgeTone as any}>
              {props.status === "running" ? <Spinner /> : null}
              <span>{badgeLabel}</span>
            </Badge>
            {props.run_id ? <span style={{ fontSize: 11, color: "#64748b" }}>run_id: {props.run_id}</span> : null}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>article</div>
      </div>

      {nodes.length ? (
        <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #f1f5f9", background: "#f8fafc", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>进度</div>
          <div style={{ display: "grid", gap: 8 }}>
            {nodes.map((n, idx) => {
              const label = n.node_name || n.node_code || `node-${idx + 1}`;
              const dot = statusDot(n.node_status);
              const isCurrent = current && (current === n.node_code || current === n.node_name);
              return (
                <div key={`${n.node_code || label}-${idx}`} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 5,
                      background: dot.bg,
                      border: "1px solid rgba(148,163,184,0.45)",
                      marginTop: 4,
                      flex: "0 0 auto",
                    }}
                    title={n.node_status || ""}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: isCurrent ? 700 : 600, color: isCurrent ? "#0f172a" : "#334155" }}>
                      {label}
                      {isCurrent ? <span style={{ marginLeft: 8, fontSize: 11, color: "#2563eb" }}>当前</span> : null}
                    </div>
                    {n.node_message ? (
                      <div style={{ marginTop: 2, fontSize: 11, color: "#64748b", whiteSpace: "pre-wrap" }}>
                        {n.node_message}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #f1f5f9",
            background: "#f8fafc",
            padding: 12,
            fontSize: 12,
            color: "#64748b",
          }}
        >
          正在等待工作流返回进度信息…
        </div>
      )}

      {props.status === "error" && props.error_message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #fecdd3",
            background: "#fff1f2",
            padding: 12,
            fontSize: 12,
            color: "#9f1239",
          }}
        >
          {props.error_message}
        </div>
      ) : null}
    </div>
  );
};

const ArticleClarifyCard: React.FC<ArticleClarifyProps> = (props) => {
  const streamCtx = useStreamContext?.() as any;

  // 发送消息的辅助函数（复制 MCPWorkflowCard 的实现，保证在 agent-chat-ui / Studio 都能工作）
  const sendMessage = (text: string) => {
    const win = window as any;
    const globalFns = ["__LANGGRAPH_SEND_MESSAGE__", "__LANGGRAPH_SEND__", "sendMessage", "sendChatMessage"];
    for (const fn of globalFns) {
      if (typeof win[fn] === "function") {
        try {
          win[fn](text);
          return;
        } catch {}
      }
    }

    window.dispatchEvent(new CustomEvent("langgraph:send", { detail: { text } }));

    const selectors = ["textarea", 'input[type="text"]'];
    for (const sel of selectors) {
      const input = document.querySelector(sel) as HTMLInputElement | HTMLTextAreaElement | null;
      if (!input) continue;

      const proto = input.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (setter) setter.call(input, text);
      else input.value = text;

      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));

      setTimeout(() => {
        const form = input.closest("form");
        const submitBtn =
          (form?.querySelector('button[type="submit"]') as HTMLButtonElement | null) ||
          (form?.querySelector('button:not([type="button"])') as HTMLButtonElement | null) ||
          (document.querySelector('button[type="submit"]') as HTMLButtonElement | null);
        if (submitBtn) {
          submitBtn.click();
          return;
        }
        if (form) {
          const f = form as any;
          if (typeof f.requestSubmit === "function") f.requestSubmit();
          else f.submit();
          return;
        }
        input.dispatchEvent(
          new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true })
        );
        input.dispatchEvent(
          new KeyboardEvent("keypress", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true })
        );
        input.dispatchEvent(
          new KeyboardEvent("keyup", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true })
        );
      }, 50);

      return;
    }
  };

  const [topic, setTopic] = useState(props.topic || "");
  const [contentFormat, setContentFormat] = useState(props.content_format || "");
  const [audience, setAudience] = useState(props.target_audience || "");
  const [tone, setTone] = useState(props.tone || "");
  const [submitting, setSubmitting] = useState(false);

  // 当后端在多轮中更新已收集字段时，自动带入到表单
  useEffect(() => setTopic(props.topic || ""), [props.topic]);
  useEffect(() => setContentFormat(props.content_format || ""), [props.content_format]);
  useEffect(() => setAudience(props.target_audience || ""), [props.target_audience]);
  useEffect(() => setTone(props.tone || ""), [props.tone]);
  // 当后端推送了新一轮澄清/进入工作流后，解除按钮禁用
  useEffect(() => setSubmitting(false), [props.question, JSON.stringify(props.missing || [])]);

  const toneOptions =
    props.tone_options && props.tone_options.length > 0 ? props.tone_options : ["Professional", "严谨正式", "活泼亲和"];

  const handleSubmit = () => {
    if (submitting) return;
    setSubmitting(true);
    const payload = {
      topic: topic || "",
      content_format: contentFormat || "",
      target_audience: audience || "",
      tone: tone || "",
    };
    const payloadJson = JSON.stringify(payload);
    
    // 构造语义化文本（给用户看）+ 隐藏 JSON（给程序看）
    const displayContent = 
      `已完善文章信息：\n` +
      `- 主题：${payload.topic}\n` +
      `- 格式：${payload.content_format}\n` +
      `- 受众：${payload.target_audience}\n` +
      `- 风格：${payload.tone}\n\n` +
      `<!-- ${payloadJson} -->`;

    // Generative UI 推荐：直接通过 useStreamContext().submit() 继续对话（不需要 interrupt/resume）
    if (streamCtx && typeof streamCtx.submit === "function") {
      const newMessage = {
        // 兼容不同运行时：有的用 role，有的用 type
        role: "user",
        type: "human",
        content: displayContent,
      };
      try {
        streamCtx.submit({ messages: [newMessage] });
        return;
      } catch {}
    }

    // 兜底：无法 submit 时，也发送带隐藏数据的文本
    sendMessage(displayContent);
  };

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 560,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>文章生成：补充必要信息</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone="blue">
              <span>{props.status === "need_info" ? "需要澄清" : props.status}</span>
            </Badge>
            {props.missing && props.missing.length ? (
              <span style={{ fontSize: 12, color: "#64748b" }}>
                缺失：<b>{props.missing.join(", ")}</b>
              </span>
            ) : null}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>article</div>
      </div>

      {props.question ? (
        <div style={{ marginTop: 12, fontSize: 12, color: "#334155", whiteSpace: "pre-wrap" }}>{props.question}</div>
      ) : null}

      <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>topic（主题/标题）</div>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如：公司发布 2026 年新品耳机"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13 }}
          />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>content_format（内容格式/栏目）</div>
          <input
            value={contentFormat}
            onChange={(e) => setContentFormat(e.target.value)}
            placeholder="例如：新闻中心"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13 }}
          />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>target_audience（目标受众）</div>
          <input
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="例如：读者和投资者"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13 }}
          />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>Content style（tone）</div>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: 10,
              border: "1px solid #e2e8f0",
              fontSize: 13,
              background: "#fff",
            }}
          >
            <option value="">请选择…</option>
            {toneOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              borderRadius: 10,
              border: "1px solid #2563eb",
              background: submitting ? "#93c5fd" : "#2563eb",
              color: "#fff",
              padding: "10px 12px",
              fontSize: 13,
              fontWeight: 700,
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.9 : 1,
            }}
          >
            {submitting ? "已提交…" : "提交并继续"}
          </button>
        </div>
      </div>
    </div>
  );
};

const MCPWorkflowCard: React.FC<MCPWorkflowProps> = (props) => {
  const tone =
    props.status === "done"
      ? "green"
      : props.status === "error"
        ? "red"
        : props.status === "running"
          ? "blue"
          : props.status === "cancelled"
            ? "slate"
            : props.status === "confirm"
              ? "blue"
              : "slate";
  const labelMap: Record<string, string> = {
    select: "请选择",
    confirm: "待确认",
    running: "执行中",
    done: "已完成",
    cancelled: "已取消",
    error: "失败",
  };

  // 发送消息的辅助函数
  const sendMessage = (text: string) => {
    const win = window as any;

    // 方法1: 尝试调用全局注入的发送函数
    const globalFns = [
      "__LANGGRAPH_SEND_MESSAGE__",
      "__LANGGRAPH_SEND__",
      "sendMessage",
      "sendChatMessage",
    ];
    for (const fn of globalFns) {
      if (typeof win[fn] === "function") {
        try { win[fn](text); return; } catch {}
      }
    }

    // 方法2: 触发自定义事件
    window.dispatchEvent(new CustomEvent("langgraph:send", { detail: { text } }));

    // 方法3: 操作 DOM - 设置值后点击提交按钮
    const selectors = [
      'textarea',
      'input[type="text"]',
    ];

    for (const sel of selectors) {
      const input = document.querySelector(sel) as HTMLInputElement | HTMLTextAreaElement | null;
      if (!input) continue;

      // 设置值（兼容 React 受控组件）
      const proto = input.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (setter) setter.call(input, text);
      else input.value = text;

      // 触发事件让 React 感知
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));

      // 延迟后尝试提交
      setTimeout(() => {
        // 优先找提交按钮并点击
        const form = input.closest("form");
        const submitBtn = form?.querySelector('button[type="submit"]') as HTMLButtonElement | null
          || form?.querySelector('button:not([type="button"])') as HTMLButtonElement | null
          || document.querySelector('button[type="submit"]') as HTMLButtonElement | null;

        if (submitBtn) {
          submitBtn.click();
          return;
        }

        // 找不到按钮就提交表单
        if (form) {
          if (form.requestSubmit) form.requestSubmit();
          else form.submit();
          return;
        }

        // 最后尝试回车
        input.dispatchEvent(new KeyboardEvent("keydown", {
          key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true
        }));
        input.dispatchEvent(new KeyboardEvent("keypress", {
          key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true
        }));
        input.dispatchEvent(new KeyboardEvent("keyup", {
          key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true
        }));
      }, 50);

      return;
    }
  };

  // 恢复 interrupt 的函数
  const resumeInterrupt = (value: any) => {
    const win = window as any;
    
    // 方法1: 使用 LangGraph Studio 注入的全局函数
    if (typeof win.__LANGGRAPH_RESUME__ === "function") {
      try { win.__LANGGRAPH_RESUME__(value); return; } catch {}
    }
    
    // 方法2: 使用 Agent Chat UI 的 resume 函数
    const resumeFns = ["resumeThread", "resume", "sendResume"];
    for (const fn of resumeFns) {
      if (typeof win[fn] === "function") {
        try { win[fn](value); return; } catch {}
      }
    }
    
    // 方法3: 发送自定义事件
    window.dispatchEvent(new CustomEvent("langgraph:resume", { detail: value }));
    
    // 方法4: 兜底 - 发送文本消息
    sendMessage(value?.confirmed ? "确认" : "取消");
  };

  const handleConfirm = () => resumeInterrupt({ confirmed: true });
  const handleCancel = () => resumeInterrupt({ confirmed: false });

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 560,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{props.title || "后台操作"}</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={tone as any}>
              {props.status === "running" ? <Spinner /> : null}
              <span>{labelMap[props.status] || props.status}</span>
            </Badge>
            {props.selected?.name || props.selected?.code ? (
              <span style={{ fontSize: 12, color: "#64748b" }}>
                已选：<b>{props.selected?.name || props.selected?.code}</b>
              </span>
            ) : null}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>shortcut</div>
      </div>

      {props.message ? (
        <div style={{ marginTop: 12, fontSize: 12, color: "#334155" }}>{props.message}</div>
      ) : null}

      {props.options?.length ? (
        <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #f1f5f9", background: "#f8fafc", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>可选操作</div>
          <div style={{ display: "grid", gap: 8 }}>
            {props.options.map((o, idx) => (
              <div
                key={`${o.code || o.name}-${idx}`}
                onClick={props.status === "select" ? () => sendMessage(String(idx + 1)) : undefined}
                style={{
                  fontSize: 12,
                  color: "#334155",
                  padding: props.status === "select" ? "8px 10px" : undefined,
                  borderRadius: props.status === "select" ? 6 : undefined,
                  cursor: props.status === "select" ? "pointer" : "default",
                  transition: "background 0.15s",
                  background: props.status === "select" ? "transparent" : undefined,
                }}
                onMouseOver={props.status === "select" ? (e) => (e.currentTarget.style.background = "#e2e8f0") : undefined}
                onMouseOut={props.status === "select" ? (e) => (e.currentTarget.style.background = "transparent") : undefined}
              >
                <b>{idx + 1}. {o.name || o.code || "操作"}</b>
                {props.recommended && o.code === props.recommended ? (
                  <span style={{ marginLeft: 8, fontSize: 11, color: "#2563eb", fontWeight: 700 }}>推荐</span>
                ) : null}
                {o.desc ? <span style={{ marginLeft: 8, color: "#64748b" }}>{o.desc}</span> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 确认状态时显示确认/取消按钮 */}
      {props.status === "confirm" ? (
        <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
          <button
            type="button"
            onClick={handleConfirm}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 8,
              border: "none",
              background: "#2563eb",
              color: "#ffffff",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              transition: "background 0.15s",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#1d4ed8")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#2563eb")}
          >
            ✓ 确认执行
          </button>
          <button
            type="button"
            onClick={handleCancel}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 8,
              border: "1px solid #e2e8f0",
              background: "#ffffff",
              color: "#64748b",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              transition: "background 0.15s, border-color 0.15s",
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "#f8fafc";
              e.currentTarget.style.borderColor = "#cbd5e1";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "#ffffff";
              e.currentTarget.style.borderColor = "#e2e8f0";
            }}
          >
            ✗ 取消
          </button>
        </div>
      ) : null}

      {props.result ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #bbf7d0",
            background: "#ecfdf5",
            padding: 12,
            fontSize: 12,
            color: "#065f46",
            whiteSpace: "pre-wrap",
          }}
        >
          {props.result}
        </div>
      ) : null}
    </div>
  );
};

const severityColor = (s?: string) => {
  if (s === "critical") return { bg: "#fef2f2", fg: "#dc2626", bd: "#fecaca" };
  if (s === "warning") return { bg: "#fffbeb", fg: "#d97706", bd: "#fde68a" };
  return { bg: "#f0fdf4", fg: "#16a34a", bd: "#bbf7d0" };
};

const categoryColor = (c?: string) => {
  const colors: Record<string, { bg: string; fg: string }> = {
    Indexing: { bg: "#dbeafe", fg: "#1d4ed8" },
    OnPage: { bg: "#fef3c7", fg: "#b45309" },
    Performance: { bg: "#fce7f3", fg: "#be185d" },
    Content: { bg: "#d1fae5", fg: "#047857" },
    StructuredData: { bg: "#e0e7ff", fg: "#4338ca" },
  };
  return colors[c || ""] || { bg: "#f1f5f9", fg: "#64748b" };
};

const SEOPlannerCard: React.FC<SEOPlannerProps> = (props) => {
  const badgeTone = props.status === "done" ? "green" : props.status === "error" ? "red" : "blue";
  const badgeLabel = props.status === "done" ? "已完成" : props.status === "error" ? "已失败" : "分析中";
  const tasks = props.tasks?.tasks || [];
  const steps = props.steps || [];

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 640,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>SEO 周任务规划</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={badgeTone as any}>
              {props.status === "loading" ? <Spinner /> : null}
              <span>{badgeLabel}</span>
            </Badge>
            {props.tasks?.week_start && props.tasks?.week_end ? (
              <span style={{ fontSize: 11, color: "#64748b" }}>
                {props.tasks.week_start} ~ {props.tasks.week_end}
              </span>
            ) : null}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>seo</div>
      </div>

      {/* 进度步骤 */}
      {props.status === "loading" && steps.length > 0 ? (
        <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #f1f5f9", background: "#f8fafc", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>分析进度</div>
          <div style={{ display: "grid", gap: 6 }}>
            {steps.map((step, idx) => {
              const isActive = (props.active_step || 1) === idx + 1;
              const isDone = (props.active_step || 1) > idx + 1;
              return (
                <div key={idx} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: 9,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 10,
                      fontWeight: 700,
                      background: isDone ? "#86efac" : isActive ? "#bfdbfe" : "#e2e8f0",
                      color: isDone ? "#052e16" : isActive ? "#1d4ed8" : "#64748b",
                      flex: "0 0 auto",
                    }}
                  >
                    {isDone ? "✓" : isActive ? <Spinner /> : idx + 1}
                  </span>
                  <span style={{ fontSize: 12, color: isActive ? "#0f172a" : "#64748b", fontWeight: isActive ? 600 : 400 }}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* 任务列表 */}
      {props.status === "done" && tasks.length > 0 ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>
            本周任务（{tasks.length} 条）
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {tasks.map((task, idx) => {
              const sev = severityColor(task.severity);
              const cat = categoryColor(task.category);
              return (
                <div
                  key={idx}
                  style={{
                    borderRadius: 10,
                    border: `1px solid ${sev.bd}`,
                    background: "#ffffff",
                    padding: 12,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                            background: cat.bg,
                            color: cat.fg,
                          }}
                        >
                          {task.category}
                        </span>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                            background: sev.bg,
                            color: sev.fg,
                          }}
                        >
                          {task.severity}
                        </span>
                        {task.requires_manual_confirmation ? (
                          <span style={{ fontSize: 10, color: "#dc2626" }}>⚠ 需确认</span>
                        ) : null}
                      </div>
                      <div style={{ marginTop: 6, fontSize: 13, fontWeight: 600, color: "#0f172a" }}>
                        {task.title}
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: "#64748b" }}>
                        {task.description}
                      </div>
                    </div>
                    <div style={{ textAlign: "right", flex: "0 0 auto" }}>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{task.date}</div>
                      <div style={{ fontSize: 10, color: "#94a3b8" }}>{task.day_of_week}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 8, display: "flex", gap: 12, fontSize: 11, color: "#64748b" }}>
                    <span>影响: {"★".repeat(task.impact || 0)}{"☆".repeat(5 - (task.impact || 0))}</span>
                    <span>难度: {"★".repeat(task.difficulty || 0)}{"☆".repeat(5 - (task.difficulty || 0))}</span>
                  </div>
                  {task.evidence?.length ? (
                    <details style={{ marginTop: 8 }}>
                      <summary style={{ cursor: "pointer", fontSize: 11, color: "#64748b" }}>
                        查看证据 ({task.evidence.length})
                      </summary>
                      <div style={{ marginTop: 6, fontSize: 11, color: "#475569" }}>
                        {task.evidence.map((ev, evIdx) => (
                          <div key={evIdx} style={{ marginTop: 4 }}>
                            <code style={{ background: "#f1f5f9", padding: "1px 4px", borderRadius: 3, fontSize: 10 }}>
                              {ev.evidence_path}
                            </code>
                            <span style={{ marginLeft: 6 }}>{ev.value_summary}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  ) : null}

                  {/* 修复按钮 */}
                  <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                    {task.fix_action === "article" ? (
                      <button
                        style={{
                          padding: "6px 12px",
                          borderRadius: 6,
                          border: "none",
                          background: "#3b82f6",
                          color: "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                        data-action="article"
                        data-prompt={task.fix_prompt || task.title}
                        onClick={() => {
                          // 直接使用 fix_prompt 作为完整的需求描述
                          const chatMessage = task.fix_prompt || `针对"${task.title}"问题，创建相关内容进行优化。`;
                          
                          // 方式1: 触发自定义事件（供外部监听）
                          const event = new CustomEvent("copilot:send", { 
                            detail: { 
                              message: chatMessage, 
                              intent: "article_task",
                              task_info: {
                                issue_type: task.issue_type,
                                category: task.category,
                                title: task.title,
                              }
                            } 
                          });
                          window.dispatchEvent(event);
                          
                          // 方式2: 尝试找到 LangGraph Studio 的输入框并提交
                          try {
                            // 查找输入框（LangGraph Studio 使用 textarea）
                            const textarea = document.querySelector('textarea[placeholder*="input"], textarea[name="input"], form textarea') as HTMLTextAreaElement;
                            if (textarea) {
                              // 设置输入框的值
                              const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
                              if (nativeInputValueSetter) {
                                nativeInputValueSetter.call(textarea, chatMessage);
                              } else {
                                textarea.value = chatMessage;
                              }
                              // 触发 input 事件让 React 感知变化
                              textarea.dispatchEvent(new Event('input', { bubbles: true }));
                              
                              // 查找并点击提交按钮
                              const form = textarea.closest('form');
                              const submitBtn = form?.querySelector('button[type="submit"]') || document.querySelector('button[aria-label*="Submit"], button[aria-label*="send"]');
                              if (submitBtn) {
                                setTimeout(() => (submitBtn as HTMLButtonElement).click(), 100);
                              }
                            }
                          } catch (e) {
                            console.log('[SEO] 自动填充失败，请手动输入:', chatMessage);
                          }
                        }}
                      >
                        <span>✏️</span>
                        <span>生成内容</span>
                      </button>
                    ) : (
                      <a
                        href="#"
                        style={{
                          padding: "6px 12px",
                          borderRadius: 6,
                          border: "1px solid #e2e8f0",
                          background: "#f8fafc",
                          color: "#64748b",
                          fontSize: 12,
                          fontWeight: 600,
                          textDecoration: "none",
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                        onClick={(e) => e.preventDefault()}
                      >
                        <span>🔧</span>
                        <span>修复</span>
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* 错误信息 */}
      {props.status === "error" && props.error_message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #fecdd3",
            background: "#fff1f2",
            padding: 12,
            fontSize: 12,
            color: "#9f1239",
          }}
        >
          {props.error_message}
        </div>
      ) : null}
    </div>
  );
};

// ============ 站点报告组件 ============

type SiteReportProps = {
  status: "loading" | "done" | "error";
  step?: string;
  user_text?: string;
  message?: string;
  steps?: string[];
  active_step?: number;
  report?: {
    site_id?: string;
    report_type?: "overview" | "traffic" | "content" | "engagement" | "performance";
    report_type_name?: string;
    summary?: {
      total_visits?: number;
      total_unique_visitors?: number;
      total_page_views?: number;
      avg_session_duration?: number;
      bounce_rate?: number;
      pages_per_session?: number;
    } | null;
    charts?: {
      // 图表由外部前端项目的组件渲染，这里不再定义强约束结构
      daily_visits?: any;
      traffic_sources?: any;
      top_pages?: any;
      device_stats?: any;
      user_engagement?: any;
    };
    data_quality?: {
      notes?: string[];
      warnings?: string[];
      window_days?: number | null;
      property_id?: string | null;
    } | null;
    insights?: {
      one_liner?: string;
      evidence?: string[];
      hypotheses?: { text?: string; confidence?: "high" | "medium" | "low"; next_step?: string }[];
    } | null;
    actions?: {
      id?: string;
      title?: string;
      why?: string;
      effort?: "low" | "medium" | "high";
      impact?: "low" | "medium" | "high";
      success_metric?: { metric?: string; window_days?: number; target?: string };
    }[] | null;
    todos?: {
      id?: string;
      title?: string;
      description?: string;
      success_metric?: { metric?: string; window_days?: number; target?: string };
    }[] | null;
    trace?: {
      todo_summary?: string;
      used_todos?: string[];
    } | null;
    step_outputs?: { step?: string; result?: string; evidence_ref?: string | null }[] | null;
    content?: {
      total_articles?: number;
      published_this_week?: number;
      draft_count?: number;
      scheduled_count?: number;
    } | null;
    performance?: {
      avg_load_time_ms?: number;
      lcp_ms?: number;
      fid_ms?: number;
      cls?: number;
      ttfb_ms?: number;
      uptime_percentage?: number;
      error_rate?: number;
    } | null;
  } | null;
  error_message?: string | null;
};

// 报告类型图标和颜色
const reportTypeStyles: Record<string, { icon: string; color: string; bg: string }> = {
  overview: { icon: "📊", color: "#3b82f6", bg: "linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%)" },
  traffic: { icon: "📈", color: "#10b981", bg: "linear-gradient(135deg, #ecfdf5 0%, #f0fdfa 100%)" },
  content: { icon: "📝", color: "#8b5cf6", bg: "linear-gradient(135deg, #f5f3ff 0%, #faf5ff 100%)" },
  engagement: { icon: "💬", color: "#f59e0b", bg: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)" },
  performance: { icon: "⚡", color: "#ef4444", bg: "linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%)" },
};

// 站点报告卡片
const SiteReportCard: React.FC<SiteReportProps> = (props) => {
  const badgeTone = props.status === "done" ? "green" : props.status === "error" ? "red" : "blue";
  const badgeLabel = props.status === "done" ? "已完成" : props.status === "error" ? "已失败" : "生成中";
  const steps = props.steps || [];
  const report = props.report;
  const summary = report?.summary;
  const dataQuality = report?.data_quality || null;
  const insights = report?.insights || null;
  const actions = report?.actions || null;
  const todos = report?.todos || null;
  const trace = report?.trace || null;
  const stepOutputs = report?.step_outputs || null;
  const reportType = report?.report_type || "overview";
  const reportTypeName = report?.report_type_name || "综合概览";
  const typeStyle = reportTypeStyles[reportType] || reportTypeStyles.overview;

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 720,
      }}
    >
      <style>{cssText}</style>

      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>
            {typeStyle.icon} {reportTypeName}报告
          </div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={badgeTone as any}>
              {props.status === "loading" ? <Spinner /> : null}
              <span>{badgeLabel}</span>
            </Badge>
            {report?.site_id ? (
              <span style={{ fontSize: 11, color: "#64748b" }}>站点: {report.site_id}</span>
            ) : null}
            {props.status === "done" && reportType !== "overview" ? (
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: typeStyle.color + "15",
                  color: typeStyle.color,
                  fontWeight: 600,
                }}
              >
                {reportTypeName}
              </span>
            ) : null}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>report</div>
      </div>

      {/* 进度步骤 */}
      {props.status === "loading" && steps.length > 0 ? (
        <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #f1f5f9", background: "#f8fafc", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>生成进度</div>
          <div style={{ display: "grid", gap: 6 }}>
            {steps.map((step, idx) => {
              const isActive = (props.active_step || 1) === idx + 1;
              const isDone = (props.active_step || 1) > idx + 1;
              return (
                <div key={idx} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: 9,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 10,
                      fontWeight: 700,
                      background: isDone ? "#86efac" : isActive ? "#bfdbfe" : "#e2e8f0",
                      color: isDone ? "#052e16" : isActive ? "#1d4ed8" : "#64748b",
                      flex: "0 0 auto",
                    }}
                  >
                    {isDone ? "✓" : isActive ? <Spinner /> : idx + 1}
                  </span>
                  <span style={{ fontSize: 12, color: isActive ? "#0f172a" : "#64748b", fontWeight: isActive ? 600 : 400 }}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* 生成过程提示 */}
      {props.status === "loading" && props.message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
            padding: 12,
            fontSize: 12,
            color: "#1e3a8a",
            whiteSpace: "pre-wrap",
          }}
        >
          {props.message}
        </div>
      ) : null}

      {/* 概览指标 - 流量相关 */}
      {props.status === "done" && summary && (reportType === "overview" || reportType === "traffic") ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>📈 流量指标</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 10,
              padding: 12,
              background: typeStyle.bg,
              borderRadius: 12,
              border: "1px solid #e2e8f0",
            }}
          >
            {summary.total_visits != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1d4ed8" }}>
                  {(summary.total_visits || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>总访问量</div>
              </div>
            ) : null}
            {summary.total_unique_visitors != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#047857" }}>
                  {(summary.total_unique_visitors || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>独立访客</div>
              </div>
            ) : null}
            {summary.total_page_views != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#7c3aed" }}>
                  {(summary.total_page_views || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>页面浏览</div>
              </div>
            ) : null}
            {summary.avg_session_duration != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "#334155" }}>
                  {Math.floor((summary.avg_session_duration || 0) / 60)}分{(summary.avg_session_duration || 0) % 60}秒
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>平均时长</div>
              </div>
            ) : null}
            {summary.bounce_rate != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "#334155" }}>{summary.bounce_rate || 0}%</div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>跳出率</div>
              </div>
            ) : null}
            {summary.pages_per_session != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "#334155" }}>{summary.pages_per_session || 0}</div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>页面/会话</div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 互动指标 - engagement 类型专用 */}
      {props.status === "done" && summary && reportType === "engagement" ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>💬 互动指标</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 10,
              padding: 12,
              background: typeStyle.bg,
              borderRadius: 12,
              border: "1px solid #e2e8f0",
            }}
          >
            {summary.avg_session_duration != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: typeStyle.color }}>
                  {Math.floor((summary.avg_session_duration || 0) / 60)}分{(summary.avg_session_duration || 0) % 60}秒
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>平均停留</div>
              </div>
            ) : null}
            {summary.bounce_rate != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: typeStyle.color }}>{summary.bounce_rate || 0}%</div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>跳出率</div>
              </div>
            ) : null}
            {summary.pages_per_session != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: typeStyle.color }}>{summary.pages_per_session || 0}</div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>页面/会话</div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 性能指标 - performance 类型专用 */}
      {props.status === "done" && report?.performance && (reportType === "overview" || reportType === "performance") ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>⚡ 性能指标</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: reportType === "performance" ? "repeat(4, 1fr)" : "repeat(3, 1fr)",
              gap: 10,
              padding: 12,
              background: reportType === "performance" ? typeStyle.bg : "#f8fafc",
              borderRadius: 12,
              border: "1px solid #e2e8f0",
            }}
          >
            {report.performance.avg_load_time_ms != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: report.performance.avg_load_time_ms > 2000 ? "#ef4444" : "#10b981" }}>
                  {(report.performance.avg_load_time_ms / 1000).toFixed(2)}s
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>加载时间</div>
              </div>
            ) : null}
            {report.performance.lcp_ms != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: report.performance.lcp_ms > 2500 ? "#ef4444" : "#10b981" }}>
                  {(report.performance.lcp_ms / 1000).toFixed(2)}s
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>LCP</div>
              </div>
            ) : null}
            {report.performance.fid_ms != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: report.performance.fid_ms > 100 ? "#f59e0b" : "#10b981" }}>
                  {report.performance.fid_ms}ms
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>FID</div>
              </div>
            ) : null}
            {report.performance.cls != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: report.performance.cls > 0.1 ? "#f59e0b" : "#10b981" }}>
                  {report.performance.cls}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>CLS</div>
              </div>
            ) : null}
            {report.performance.uptime_percentage != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "#10b981" }}>
                  {report.performance.uptime_percentage}%
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>可用率</div>
              </div>
            ) : null}
            {report.performance.error_rate != null ? (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: report.performance.error_rate > 1 ? "#ef4444" : "#10b981" }}>
                  {report.performance.error_rate}%
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>错误率</div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 图表区域：已迁移到外部前端项目的图表组件 */}

      {/* 数据质量提示（允许在 loading 阶段展示阶段性结果） */}
      {props.status !== "error" && dataQuality && (dataQuality.warnings?.length || dataQuality.notes?.length) ? (
        <div style={{ marginTop: 12 }}>
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              background: "#f8fafc",
              padding: 12,
              fontSize: 12,
              color: "#334155",
            }}
          >
            {dataQuality.warnings?.length ? (
              <div style={{ marginBottom: dataQuality.notes?.length ? 10 : 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#9f1239", marginBottom: 6 }}>Warnings</div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {dataQuality.warnings.map((w, idx) => (
                    <li key={idx} style={{ marginTop: idx ? 4 : 0 }}>
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {dataQuality.notes?.length ? (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 6 }}>Notes</div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {dataQuality.notes.map((n, idx) => (
                    <li key={idx} style={{ marginTop: idx ? 4 : 0 }}>
                      {n}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 分析轨迹（基于 Todo 步骤） */}
      {props.status !== "error" && trace && (trace.todo_summary || (trace.used_todos && trace.used_todos.length)) ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>🧭 分析轨迹</div>
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              background: "#ffffff",
              padding: 12,
              fontSize: 12,
              color: "#334155",
            }}
          >
            {trace.todo_summary ? <div style={{ fontWeight: 600 }}>{trace.todo_summary}</div> : null}
            {trace.used_todos?.length ? (
              <ul style={{ margin: "10px 0 0 0", paddingLeft: 18 }}>
                {trace.used_todos.map((t, idx) => (
                  <li key={idx} style={{ marginTop: idx ? 4 : 0 }}>
                    {t}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 逐步产出（每个 Todo 步骤的具体结果） */}
      {props.status !== "error" && stepOutputs && stepOutputs.length > 0 ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>🧾 步骤产出</div>
          <div style={{ display: "grid", gap: 8 }}>
            {stepOutputs.map((s, idx) => (
              <div
                key={idx}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  padding: 12,
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>
                  {idx + 1}. {s.step || "—"}
                </div>
                {s.result ? (
                  <div style={{ marginTop: 6, fontSize: 12, color: "#334155", whiteSpace: "pre-wrap" }}>{s.result}</div>
                ) : null}
                {s.evidence_ref ? (
                  <div style={{ marginTop: 6, fontSize: 11, color: "#64748b" }}>证据引用：{s.evidence_ref}</div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 解读与洞察 */}
      {props.status !== "error" && insights && (insights.one_liner || insights.evidence?.length || insights.hypotheses?.length) ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>🔎 解读</div>
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              background: "#ffffff",
              padding: 12,
            }}
          >
            {insights.one_liner ? (
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>{insights.one_liner}</div>
            ) : null}
            {insights.evidence?.length ? (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 6 }}>证据点</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#334155" }}>
                  {insights.evidence.map((e, idx) => (
                    <li key={idx} style={{ marginTop: idx ? 4 : 0 }}>
                      {e}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {insights.hypotheses?.length ? (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 6 }}>假设（待验证）</div>
                <div style={{ display: "grid", gap: 8 }}>
                  {insights.hypotheses.map((h, idx) => (
                    <div
                      key={idx}
                      style={{
                        borderRadius: 10,
                        border: "1px solid #f1f5f9",
                        background: "#f8fafc",
                        padding: 10,
                        fontSize: 12,
                        color: "#334155",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                        <div style={{ fontWeight: 600 }}>{h.text || "—"}</div>
                        {h.confidence ? <span style={{ fontSize: 11, color: "#64748b" }}>{h.confidence}</span> : null}
                      </div>
                      {h.next_step ? (
                        <div style={{ marginTop: 4, fontSize: 11, color: "#64748b" }}>验证：{h.next_step}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 建议动作（仅展示） */}
      {props.status !== "error" && actions && actions.length > 0 ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>✅ 建议动作</div>
          <div style={{ display: "grid", gap: 8 }}>
            {actions.map((a, idx) => (
              <div
                key={a.id || idx}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  padding: 12,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>{a.title || "—"}</div>
                {a.why ? <div style={{ marginTop: 6, fontSize: 12, color: "#334155" }}>{a.why}</div> : null}
                {(a.impact || a.effort || a.success_metric?.metric) ? (
                  <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {a.impact ? <Badge tone="green">impact: {a.impact}</Badge> : null}
                    {a.effort ? <Badge tone="slate">effort: {a.effort}</Badge> : null}
                    {a.success_metric?.metric ? (
                      <Badge tone="blue">
                        metric: {a.success_metric.metric}
                        {a.success_metric.window_days ? ` (${a.success_metric.window_days}d)` : ""}
                      </Badge>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 内容统计 */}
      {props.status === "done" && report?.content ? (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>📝 内容统计</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 8,
              padding: 12,
              background: "#f8fafc",
              borderRadius: 10,
              border: "1px solid #e2e8f0",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#334155" }}>{report.content.total_articles || 0}</div>
              <div style={{ fontSize: 10, color: "#64748b" }}>文章总数</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#10b981" }}>+{report.content.published_this_week || 0}</div>
              <div style={{ fontSize: 10, color: "#64748b" }}>本周发布</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#f59e0b" }}>{report.content.draft_count || 0}</div>
              <div style={{ fontSize: 10, color: "#64748b" }}>草稿</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#8b5cf6" }}>{report.content.scheduled_count || 0}</div>
              <div style={{ fontSize: 10, color: "#64748b" }}>定时发布</div>
            </div>
          </div>
        </div>
      ) : null}

      {/* 错误信息 */}
      {props.status === "error" && props.error_message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #fecdd3",
            background: "#fff1f2",
            padding: 12,
            fontSize: 12,
            color: "#9f1239",
          }}
        >
          {props.error_message}
        </div>
      ) : null}
    </div>
  );
};

// ============ Report v2：三张卡（进度 / 图表 / 洞察）===========
type ReportProgressProps = {
  status: "loading" | "done" | "error";
  step?: string;
  user_text?: string;
  steps?: string[];
  active_step?: number;
  message?: string;
  error_message?: string | null;
};

const ReportProgressCard: React.FC<ReportProgressProps> = (props) => {
  const badgeTone = props.status === "done" ? "green" : props.status === "error" ? "red" : "blue";
  const badgeLabel = props.status === "done" ? "已完成" : props.status === "error" ? "已失败" : "生成中";
  const steps = props.steps || [];

  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 720,
      }}
    >
      <style>{cssText}</style>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>📊 网站数据报告</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={badgeTone as any}>
              {props.status === "loading" ? <Spinner /> : null}
              <span>{badgeLabel}</span>
            </Badge>
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>report</div>
      </div>

      {props.status === "loading" && steps.length > 0 ? (
        <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #f1f5f9", background: "#f8fafc", padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>生成进度</div>
          <div style={{ display: "grid", gap: 6 }}>
            {steps.map((step, idx) => {
              const isActive = (props.active_step || 1) === idx + 1;
              const isDone = (props.active_step || 1) > idx + 1;
              return (
                <div key={idx} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: 9,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 10,
                      fontWeight: 700,
                      background: isDone ? "#86efac" : isActive ? "#bfdbfe" : "#e2e8f0",
                      color: isDone ? "#052e16" : isActive ? "#1d4ed8" : "#64748b",
                      flex: "0 0 auto",
                    }}
                  >
                    {isDone ? "✓" : isActive ? <Spinner /> : idx + 1}
                  </span>
                  <span style={{ fontSize: 12, color: isActive ? "#0f172a" : "#64748b", fontWeight: isActive ? 600 : 400 }}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {props.message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #bfdbfe",
            background: "#eff6ff",
            padding: 12,
            fontSize: 12,
            color: "#1e3a8a",
            whiteSpace: "pre-wrap",
          }}
        >
          {props.message}
        </div>
      ) : null}

      {props.status === "error" && props.error_message ? (
        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: "1px solid #fecdd3",
            background: "#fff1f2",
            padding: 12,
            fontSize: 12,
            color: "#9f1239",
            whiteSpace: "pre-wrap",
          }}
        >
          {props.error_message}
        </div>
      ) : null}
    </div>
  );
};

type ReportChartsProps = {
  status: "loading" | "done" | "error";
  message?: string;
  report?: {
    summary?: any;
    charts?: any;
  } | null;
};

const ReportChartsCard: React.FC<ReportChartsProps> = (props) => {
  const report = props.report || null;
  return (
    <div
      className="lgui-card"
      style={{
        borderRadius: 14,
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        padding: 14,
        fontSize: 13,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        maxWidth: 720,
      }}
    >
      <style>{cssText}</style>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>📈 图表</div>
          {props.message ? <div style={{ marginTop: 6, fontSize: 12, color: "#64748b" }}>{props.message}</div> : null}
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: "#94a3b8" }}>charts</div>
      </div>
      {/* 本仓库内不渲染具体图表（图表已在 agentchatui 外层项目渲染），这里只做占位避免重复“报告卡”。 */}
      <div style={{ marginTop: 12, fontSize: 12, color: "#64748b" }}>
        {report?.charts ? "已生成图表数据（由前端图表组件渲染）。" : "等待图表数据…"}
      </div>
    </div>
  );
};

type ReportInsightsProps = {
  status: "loading" | "done" | "error";
  message?: string;
  report?: any;
};

const ReportInsightsCard: React.FC<ReportInsightsProps> = (props) => {
  // 复用 SiteReportCard 的洞察展示逻辑：直接把 report 当成 SiteReportProps.report 的子集
  const fake: SiteReportProps = {
    status: props.status === "error" ? "error" : props.status === "done" ? "done" : "loading",
    message: props.message,
    report: props.report || null,
  } as any;
  return <SiteReportCard {...fake} />;
};

// 默认导出组件映射表，key 必须和 push_ui_message 里的 name 一致
const ComponentMap = {
  intent_router: IntentRouterCard,
  article_workflow: ArticleWorkflowCard,
  article_clarify: ArticleClarifyCard,
  mcp_workflow: MCPWorkflowCard,
  seo_planner: SEOPlannerCard,
  site_report: SiteReportCard,
  report_progress: ReportProgressCard,
  report_charts: ReportChartsCard,
  report_insights: ReportInsightsCard,
  // 兼容旧名字：如果后端仍 push "card"，也能渲染为新版卡片
  card: IntentRouterCard as any,
};

export default ComponentMap;


