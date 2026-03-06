/**
 * API 客户端 — 封装对后端 /api/v1/public/* 的调用
 */

const BASE = '/api/v1/public'

export interface TokenInfo {
  token: string
  skill: { id: string; name: string; description: string | null }
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
  idempotencyKey?: string,
): Promise<JobOut> {
  return request<JobOut>(`${BASE}/job`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      idempotency_key: idempotencyKey,
      inputs: { image_key: imageKey },
    }),
  })
}

export function getJobStatus(jobId: string): Promise<JobOut> {
  return request<JobOut>(`${BASE}/job/${jobId}`)
}
