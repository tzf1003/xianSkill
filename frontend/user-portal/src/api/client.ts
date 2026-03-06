/**
 * API 客户端 — 封装对后端 /api/v1/public/* 的调用
 */

const BASE = '/api/v1/public'

// ── 项目选项类型 ──────────────────────────────────────────────────────
export interface ProjectOptionChoice {
  id: string
  label: string
  icon?: string
  description?: string
  prompt_addition?: string
}

export interface ProjectOptionGroup {
  id: string
  label: string
  description?: string
  type: 'toggle' | 'single_choice'
  default: boolean | string
  icon?: string
  prompt_addition?: string   // toggle 类型用
  choices?: ProjectOptionChoice[]  // single_choice 类型用
}

export interface ProjectInfo {
  id: string
  name: string
  slug: string
  description: string | null
  cover_url: string | null
  type: string
  options: { option_groups: ProjectOptionGroup[] } | null
  enabled: boolean
  created_at: string
}

export interface TokenInfo {
  token: string
  skill: { id: string; name: string; description: string | null; project_id: string | null }
  sku_name: string
  /** 'auto' | 'human' */
  delivery_mode: string
  human_sla_hours: number | null
  total_uses: number
  remaining: number
  status: string
  expires_at: string | null
  /** 最新 Job 摘要，用于显示人工处理进度 */
  latest_job: {
    id: string
    status: string
    created_at: string
    finished_at: string | null
    assets: AssetOut[]
  } | null
  /** 若 skill 绑定了项目，则返回项目信息 */
  project: ProjectInfo | null
}

export interface UploadOut {
  object_key: string
  input_hash: string
}

export interface AssetOut {
  id: string
  filename: string
  storage_key: string
  content_type: string | null
  size_bytes: number | null
  download_url: string
}

export interface JobOut {
  id: string
  status: string
  inputs: Record<string, unknown> | null
  result: Record<string, unknown> | null
  error: string | null
  log_text: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  assets: AssetOut[]
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  const json = await res.json()
  if (json.code !== 0) throw new Error(json.message ?? `HTTP ${res.status}`)
  return json.data as T
}

export function getTokenInfo(token: string): Promise<TokenInfo> {
  return request<TokenInfo>(`${BASE}/token/${token}`)
}

export function uploadFile(token: string, file: File): Promise<UploadOut> {
  const form = new FormData()
  form.append('token', token)
  form.append('file', file)
  return request<UploadOut>(`${BASE}/upload`, { method: 'POST', body: form })
}

export function submitJob(
  token: string,
  imageKey: string,
  opts?: {
    idempotencyKey?: string
    selectedOptions?: string[]
    userNote?: string
  },
): Promise<JobOut> {
  return request<JobOut>(`${BASE}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      idempotency_key: opts?.idempotencyKey,
      inputs: {
        image_key: imageKey,
        selected_options: opts?.selectedOptions ?? [],
        user_note: opts?.userNote ?? '',
      },
    }),
  })
}

export function getJobStatus(jobId: string): Promise<JobOut> {
  return request<JobOut>(`${BASE}/job/${jobId}`)
}

export function listProjects(): Promise<ProjectInfo[]> {
  return request<ProjectInfo[]>(`${BASE}/projects`)
}

export function getProject(slug: string): Promise<ProjectInfo> {
  return request<ProjectInfo>(`${BASE}/projects/${slug}`)
}
