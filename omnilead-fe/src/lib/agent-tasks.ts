import type { Channel } from "./types";
import type { ChatEvent } from "./chat";

export type TaskSchedule = "manual" | "once" | "every_15m" | "hourly" | "daily" | "weekly";
export type TaskStatus = "todo" | "scheduled" | "running" | "done" | "blocked" | "paused";
export interface TaskInput {
  title: string;
  instruction: string;
  channels: Channel[];
  schedule: TaskSchedule;
  at?: string | null;
  time?: string;
  weekday?: number;
}
export interface AgentTask extends TaskInput {
  id: string;
  revision: number;
  status: TaskStatus;
  next_run_at: string | null;
  cron: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
  last_run_at: string | null;
  result: string;
  events: ChatEvent[];
}
export interface TaskBoard {
  tasks: AgentTask[];
  scheduler: "local" | "external";
  timezone: string;
  supported_channels: Channel[];
}
export const scheduleLabels: Record<TaskSchedule, string> = {
  manual: "Tanpa jadwal", once: "Sekali", every_15m: "Setiap 15 menit", hourly: "Setiap jam", daily: "Setiap hari", weekly: "Setiap minggu",
};
export const taskStatusLabels: Record<TaskStatus, string> = {
  todo: "To-do", scheduled: "Terjadwal", running: "Dikerjakan", done: "Selesai", blocked: "Perlu perhatian", paused: "Dijeda",
};
export function taskDate(value: string | null) {
  if (!value) return "Belum dijadwalkan";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Waktu tidak tersedia";
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" }).format(date) + " WIB";
}
