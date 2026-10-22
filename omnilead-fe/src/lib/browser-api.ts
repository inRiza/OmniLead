import { request } from "./api";

export type BrowserChannel = "instagram" | "facebook" | "whatsapp" | "email";
export interface BrowserStep {
  id: string;
  operation: "click" | "type" | "press" | "navigate";
  reason: string;
  observation: string;
  x: number;
  y: number;
  text: string;
  key: string;
  url: string;
  target_label: string;
  target_ref: string;
}
export interface BrowserSession {
  status: string;
  engine: "openclaw";
  auth: { stage: "none" | "credentials" | "username" | "password" | "verification" | "manual"; message: string };
  chat: { id: string; role: "user" | "assistant"; text: string; at: number }[];
  queued_task: string;
  headless: boolean;
  channel: BrowserChannel;
  task: string;
  account_label: string;
  image_base64: string;
  image_revision: number;
  page_url: string;
  pending: BrowserStep | null;
  observation: string;
  result: string;
  error: string;
  steps: number;
  history: { id: string; at: number; operation: string; label: string }[];
  extracted: { id: string; handle: string; name: string; text: string; page_url: string } | null;
}
export interface BrowserState { enabled: boolean; session: BrowserSession | null }
export interface ManualControl {
  operation: "click" | "type" | "press" | "inbox";
  image_revision: number;
  x?: number; y?: number; text?: string;
  key?: "Enter" | "Tab" | "Escape" | "ArrowDown" | "ArrowUp" | "Backspace" | "PageDown" | "PageUp" | "ControlOrMeta+A";
}
const post = (path: string, body = {}) => request<BrowserState>(`/browser-agent/${path}`, {
  method: "POST", body: JSON.stringify(body),
});
export const browserApi = {
  state: () => request<BrowserState>("/browser-agent"),
  open: (channel: BrowserChannel) => post("open", { channel }),
  run: (task: string, account_label: string, allow_screenshot_to_model: boolean) =>
    post("run", { task, account_label, allow_screenshot_to_model }),
  capture: () => post("capture"),
  reopen: () => post("reopen"),
  chat: (message: string, channel: BrowserChannel, account_label: string, allow_screenshot_to_model: boolean) =>
    post("chat", { message, channel, account_label, allow_screenshot_to_model }),
  login: (body: { username: string; password: string; code: string; image_revision: number; confirmed: boolean }) => post("login", body),
  manual: (command: ManualControl) => post("manual", command),
  approve: (proposal_id: string) => post("approve", { proposal_id }),
  stop: () => post("stop"),
  close: () => post("close"),
  extract: (allow_screenshot_to_model: boolean) => post("extract", { allow_screenshot_to_model }),
  importMessage: (body: { extraction_id: string; account_label: string; handle: string; name: string; text: string; confirmed_incoming: boolean }) =>
    request<{ event_id: string; duplicate: boolean }>("/browser-agent/import", { method: "POST", body: JSON.stringify(body) }),
};
