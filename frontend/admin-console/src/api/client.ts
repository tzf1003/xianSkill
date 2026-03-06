/**
 * Admin Console — API 客户端
 * 对接后端 /api/v1/admin/* 全量接口
 */

const BASE = '/api/v1/admin'

// ── 共用类型 ─────────────────────────────────────────────────────────
export interface Skill {
  id: string; name: string; description: string | null
  type: string; version: string; enabled: boolean; created_at: string
}

export interface SKU {
  id: string; skill_id: string; name: string
  price_cents: number; delivery_mode: string; total_uses: number
  enabled: boolean; created_at: string; project_id: string | null
}

export interface Order {
  id: string; sku_id: string; status: string
  channel: string | null; token_url: string | null; created_at: string
}

export interface Token {
  id: string; token: string; order_id: string
  sku_id: string; skill_id: string; status: string
  total_uses: number; used_count: number; reserved_count: number
  remaining: number; expires_at: string | null; created_at: string
}

export interface AssetOut {
  id: string; filename: string; storage_key: string
  content_type: string | null; size_bytes: number | null; download_url: string
}

export interface Job {
  id: string; skill_id: string; status: string
  inputs: Record<string, unknown> | null; result: Record<string, unknown> | null
  error: string | null; log_text: string | null
  created_at: string; started_at: string | null; finished_at: string | null
  assets: AssetOut[]
}

export interface Stats {
  total_skills: number; total_skus: number; total_orders: number
  total_tokens: number; total_jobs: number
  jobs_queued: number; jobs_running: number
  jobs_succeeded: number; jobs_failed: number
}

export interface PageResult<T> { total: number; items: T[] }

// ── 请求工具 ─────────────────────────────────────────────────────────
const TOKEN_KEY = 'admin_token'

export const getStoredToken = () => localStorage.getItem(TOKEN_KEY)
export const setStoredToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearStoredToken = () => localStorage.removeItem(TOKEN_KEY)

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(url, { ...init, headers })
  if (res.status === 401) {
    clearStoredToken()
    window.location.href = '/login'
    throw new Error('未登录')
  }
  const json = await res.json()
  if (json.code !== 0) throw new Error(json.message ?? `HTTP ${res.status}`)
  return json.data as T
}

function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

// ── 认证 ──────────────────────────────────────────────────────────────
export async function login(username: string, password: string): Promise<void> {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await res.json()
  if (data.code !== 0) throw new Error(data.message ?? '登录失败')
  setStoredToken(data.data.token)
}

export function logout(): void {
  clearStoredToken()
  window.location.href = '/login'
}



// ── Stats ─────────────────────────────────────────────────────────────
export const getStats = () => request<Stats>(`${BASE}/stats`)

// ── Skills ────────────────────────────────────────────────────────────
export const listSkills = (limit = 50, offset = 0) =>
  request<PageResult<Skill>>(`${BASE}/skills?limit=${limit}&offset=${offset}`)

export const createSkill = (body: Partial<Skill> & { type: string; name: string; prompt_template?: string; runner_config?: Record<string,unknown> }) =>
  request<Skill>(`${BASE}/skills`, json('POST', body))

export const updateSkill = (id: string, body: Partial<Skill> & { prompt_template?: string; runner_config?: Record<string,unknown> }) =>
  request<Skill>(`${BASE}/skills/${id}`, json('PUT', body))

export const disableSkill = (id: string) =>
  request<{ id: string; enabled: boolean }>(`${BASE}/skills/${id}`, { method: 'DELETE' })

// ── SKUs ──────────────────────────────────────────────────────────────
export const listSKUs = (skillId?: string, limit = 50, offset = 0, projectId?: string) => {
  const q = [skillId ? `skill_id=${skillId}` : '', projectId ? `project_id=${projectId}` : ''].filter(Boolean).join('&')
  return request<PageResult<SKU>>(`${BASE}/skus?limit=${limit}&offset=${offset}${q ? '&' + q : ''}`)
}

export const createSKU = (body: { skill_id: string; name: string; price_cents: number; delivery_mode: string; total_uses: number; project_id?: string | null }) =>
  request<SKU>(`${BASE}/skus`, json('POST', body))

export const updateSKU = (id: string, body: Partial<SKU>) =>
  request<SKU>(`${BASE}/skus/${id}`, json('PUT', body))

// ── Orders ────────────────────────────────────────────────────────────
export const listOrders = (limit = 50, offset = 0) =>
  request<PageResult<Order>>(`${BASE}/orders?limit=${limit}&offset=${offset}`)

export const createOrder = (body: { sku_id: string; channel?: string }) =>
  request<Order>(`${BASE}/orders`, json('POST', body))

// ── Tokens ────────────────────────────────────────────────────────────
export const listTokens = (status?: string, limit = 50, offset = 0, projectId?: string) => {
  const q = [status ? `status=${status}` : '', projectId ? `project_id=${projectId}` : ''].filter(Boolean).join('&')
  return request<PageResult<Token>>(`${BASE}/tokens?limit=${limit}&offset=${offset}${q ? '&' + q : ''}`)
}

export const revokeToken = (id: string) =>
  request<{ id: string; status: string }>(`${BASE}/tokens/${id}`, { method: 'DELETE' })

export interface TokenCreate {
  sku_id: string
  total_uses?: number
  expires_at?: string | null
  channel?: string
}

export const createToken = (body: TokenCreate) =>
  request<Token>(`${BASE}/tokens`, json('POST', body))

// ── Jobs ──────────────────────────────────────────────────────────────
export const listJobs = (status?: string, skillId?: string, limit = 50, offset = 0) => {
  const q = [
    status ? `status=${status}` : '',
    skillId ? `skill_id=${skillId}` : '',
    `limit=${limit}`,
    `offset=${offset}`,
  ].filter(Boolean).join('&')
  return request<PageResult<Job>>(`${BASE}/jobs?${q}`)
}

export const getJob = (id: string) =>
  request<Job>(`${BASE}/jobs/${id}`)

export const retryJob = (id: string) =>
  request<Job>(`${BASE}/jobs/${id}/retry`, { method: 'POST' })

// ── Projects ─────────────────────────────────────────────────────────
export interface Project {
  id: string
  name: string
  slug: string
  description: string | null
  cover_url: string | null
  type: string
  options: Record<string, unknown> | null
  enabled: boolean
  skill_id: string | null
  created_at: string
}

export interface ProjectCreate {
  name: string
  slug: string
  description?: string
  cover_url?: string
  type?: string
  options?: Record<string, unknown>
  enabled?: boolean
  skill_id?: string | null
}

export const listProjects = (limit = 50, offset = 0) =>
  request<{ total: number; items: Project[] }>(`${BASE}/projects?limit=${limit}&offset=${offset}`)

export const createProject = (body: ProjectCreate) =>
  request<Project>(`${BASE}/projects`, json('POST', body))

export const updateProject = (id: string, body: Partial<ProjectCreate>) =>
  request<Project>(`${BASE}/projects/${id}`, json('PATCH', body))

export const deleteProject = (id: string) =>
  request<{ id: string; enabled: boolean }>(`${BASE}/projects/${id}`, { method: 'DELETE' })
