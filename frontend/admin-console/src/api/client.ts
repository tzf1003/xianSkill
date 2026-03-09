/**
 * Admin Console — API 客户端
 * 对接后端 /api/v1/admin/* 全量接口
 */

const BASE = '/api/v1/admin'

// ── 共用类型 ─────────────────────────────────────────────────────────
export interface Skill {
  id: string; name: string; description: string | null
  type: string; version: string; enabled: boolean; created_at: string
  prompt_template?: string | null
}

export interface SKU {
  id: string; skill_id: string; name: string
  price_cents: number; delivery_mode: string; total_uses: number
  enabled: boolean; created_at: string; project_id: string | null
  push_channel_id: string | null
  delivery_content_template: string | null
}

export interface PushChannel {
  id: string
  name: string
  provider: string
  base_url: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface PushChannelPayload {
  name: string
  provider: 'bark' | string
  base_url: string
  enabled?: boolean
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

export interface AIModelItem {
  id: string
  label?: string | null
}

export interface AIProvider {
  id: string
  name: string
  protocol: string
  base_url: string | null
  enabled: boolean
  models: AIModelItem[]
  has_api_key: boolean
  api_key_masked: string | null
  created_at: string
  updated_at: string
}

export interface AIProviderPayload {
  name: string
  protocol: 'openai' | 'anthropic' | 'gemini' | 'volcengine' | string
  base_url?: string
  api_key?: string
  enabled?: boolean
  models?: AIModelItem[]
}

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

// ── AI Providers ─────────────────────────────────────────────────────
export const listAIProviders = (limit = 50, offset = 0) =>
  request<PageResult<AIProvider>>(`${BASE}/ai-providers?limit=${limit}&offset=${offset}`)

export const createAIProvider = (body: AIProviderPayload) =>
  request<AIProvider>(`${BASE}/ai-providers`, json('POST', body))

export const updateAIProvider = (id: string, body: Partial<AIProviderPayload>) =>
  request<AIProvider>(`${BASE}/ai-providers/${id}`, json('PATCH', body))

export const refreshAIProviderModels = (id: string) =>
  request<AIProvider>(`${BASE}/ai-providers/${id}/refresh-models`, { method: 'POST' })

export const deleteAIProvider = (id: string) =>
  request<{ deleted: string }>(`${BASE}/ai-providers/${id}`, { method: 'DELETE' })

// ── Push Channels ────────────────────────────────────────────────────
export const listPushChannels = (limit = 50, offset = 0) =>
  request<PageResult<PushChannel>>(`${BASE}/push-channels?limit=${limit}&offset=${offset}`)

export const createPushChannel = (body: PushChannelPayload) =>
  request<PushChannel>(`${BASE}/push-channels`, json('POST', body))

export const updatePushChannel = (id: string, body: Partial<PushChannelPayload>) =>
  request<PushChannel>(`${BASE}/push-channels/${id}`, json('PUT', body))

export const deletePushChannel = (id: string) =>
  request<{ deleted: string }>(`${BASE}/push-channels/${id}`, { method: 'DELETE' })

export const testPushChannel = (id: string, body: { title: string; body: string }) =>
  request<{ success: boolean; provider: string; response: Record<string, unknown> }>(`${BASE}/push-channels/${id}/test`, json('POST', body))

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

export const createSKU = (body: { skill_id: string; name: string; price_cents: number; delivery_mode: string; total_uses: number; project_id?: string | null; push_channel_id?: string | null; delivery_content_template?: string | null }) =>
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
  ai_provider_id: string | null
  ai_model: string | null
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
  ai_provider_id?: string | null
  ai_model?: string | null
}

export const listProjects = (limit = 50, offset = 0) =>
  request<{ total: number; items: Project[] }>(`${BASE}/projects?limit=${limit}&offset=${offset}`)

export const createProject = (body: ProjectCreate) =>
  request<Project>(`${BASE}/projects`, json('POST', body))

export const updateProject = (id: string, body: Partial<ProjectCreate>) =>
  request<Project>(`${BASE}/projects/${id}`, json('PATCH', body))

export const deleteProject = (id: string) =>
  request<{ id: string; enabled: boolean }>(`${BASE}/projects/${id}`, { method: 'DELETE' })

// ── Goods（虚拟货源商品）──────────────────────────────────────────────
export interface SpecSkuBinding {
  id: string
  timing: string  // after_payment | after_receipt | after_review
  sku_id: string | null
  created_at: string
}

export interface GoodsSpec {
  id: string
  goods_id: string
  spec_name: string
  price_cents: number
  stock: number
  enabled: boolean
  xgj_sku_text: string | null
  xgj_outer_id: string | null
  sku_bindings: SpecSkuBinding[]
  created_at: string
}

export interface SpecGroup {
  name: string
  values: string[]
}

export interface GoodsXgjProfile {
  item_biz_type: number
  sp_biz_type: number
  category_id: number | null
  channel_cat_id: string
  original_price_cents: number
  express_fee_cents: number
  stuff_status: number
  notify_url: string | null
  flash_sale_type: number | null
  is_tax_included: boolean
  product_status?: number | null
  publish_status?: number | null
}

export interface GoodsXgjProperty {
  id?: string
  property_id: string
  property_name: string
  value_id: string
  value_name: string
  sort_order?: number
}

export interface GoodsXgjPublishShopImage {
  id?: string
  image_url: string
  sort_order?: number
}

export interface XgjShopRef {
  id: string
  user_name: string
  user_nick: string
  shop_name: string
  service_support: string | null
  is_valid: boolean
}

export interface GoodsXgjPublishShop {
  id?: string
  xgj_shop_id?: string | null
  xgj_shop?: XgjShopRef | null
  user_name: string
  province: number
  city: number
  district: number
  title: string
  content: string
  white_image_url?: string | null
  service_support?: string | null
  sort_order?: number
  images: GoodsXgjPublishShopImage[]
}

export interface Goods {
  id: string
  goods_no: string
  goods_type: number   // 1=直充 2=卡密 3=券码
  goods_name: string
  logo_url: string | null
  price_cents: number
  stock: number
  status: number       // 1=在架 2=下架
  multi_spec: boolean  // 是否多规格
  xgj_goods_id: string | null  // 闲管家商品ID
  spec_groups: SpecGroup[] | null  // 规格维度定义
  xgj_profile: GoodsXgjProfile | null
  xgj_properties: GoodsXgjProperty[]
  xgj_publish_shops: GoodsXgjPublishShop[]
  template: Record<string, unknown> | null
  description: string | null
  specs: GoodsSpec[]
  created_at: string
  updated_at: string
}

export interface GoodsCreate {
  goods_type: number
  goods_name: string
  logo_url?: string | null
  price_cents?: number
  stock?: number
  status?: number
  multi_spec?: boolean
  spec_groups?: SpecGroup[] | null
  xgj_profile: GoodsXgjProfile
  xgj_properties?: GoodsXgjProperty[]
  xgj_publish_shops: GoodsXgjPublishShop[]
  template?: Record<string, unknown> | null
  description?: string | null
  specs?: { spec_name: string; price_cents?: number; stock?: number; enabled?: boolean; xgj_sku_text?: string | null; xgj_outer_id?: string | null; sku_bindings?: { timing: string; sku_id?: string | null }[] }[]
}

export interface GoodsUpdate {
  goods_name?: string
  goods_type?: number
  logo_url?: string | null
  price_cents?: number
  stock?: number
  status?: number
  multi_spec?: boolean
  xgj_goods_id?: string | null
  spec_groups?: SpecGroup[] | null
  xgj_profile?: Partial<GoodsXgjProfile> | null
  xgj_properties?: GoodsXgjProperty[] | null
  xgj_publish_shops?: GoodsXgjPublishShop[] | null
  template?: Record<string, unknown> | null
  description?: string | null
}

export interface SpecVariantPayload {
  spec_name: string
  price_cents: number
  stock: number
  enabled?: boolean
  xgj_sku_text?: string | null
  xgj_outer_id?: string | null
  sku_bindings?: { timing: string; sku_id?: string | null }[]
}

export interface SpecConfigPayload {
  spec_groups: SpecGroup[]
  variants: SpecVariantPayload[]
}

export interface XgjOrder {
  id: string
  order_no: string
  out_order_no: string
  goods_no: string
  spec_id: string | null
  goods_type: number
  status: number
  quantity: number
  total_price_cents: number
  buyer_info: Record<string, unknown> | null
  delivery_info: Record<string, unknown> | null
  created_at: string
}

export interface XgjShop {
  id: string
  authorize_id: number
  authorize_expires: number
  user_id: number | null
  user_identity: string
  user_name: string
  user_nick: string
  shop_name: string
  service_support: string | null
  is_deposit_enough: boolean
  is_pro: boolean
  is_valid: boolean
  is_trial: boolean
  valid_start_time: number | null
  valid_end_time: number
  item_biz_types: string
  created_at: string
  updated_at: string
}

export interface XgjShopSyncResult {
  synced: number
  created: number
  updated: number
  deleted: number
}

export interface XgjGoodsSyncResult {
  synced: number
  created: number
  updated: number
  failed: number
}

export const listGoods = (limit = 50, offset = 0, status?: number, goodsType?: number) => {
  const q = [status != null ? `status=${status}` : '', goodsType != null ? `goods_type=${goodsType}` : ''].filter(Boolean).join('&')
  return request<PageResult<Goods>>(`${BASE}/goods?limit=${limit}&offset=${offset}${q ? '&' + q : ''}`)
}

export const createGoods = (body: GoodsCreate) =>
  request<Goods>(`${BASE}/goods`, json('POST', body))

export const getGoods = (id: string) =>
  request<Goods>(`${BASE}/goods/${id}`)

export const syncGoodsFromCloud = () =>
  request<XgjGoodsSyncResult>(`${BASE}/goods/sync`, { method: 'POST' })

export const updateGoods = (id: string, body: GoodsUpdate) =>
  request<Goods>(`${BASE}/goods/${id}`, json('PATCH', body))

export const deleteGoods = (id: string) =>
  request<{ deleted: string }>(`${BASE}/goods/${id}`, { method: 'DELETE' })

export async function uploadGoodsLogo(goodsId: string, file: File): Promise<Goods> {
  const formData = new FormData()
  formData.append('file', file)
  const token = getStoredToken()
  const res = await fetch(`${BASE}/goods/${goodsId}/logo`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (res.status === 401) {
    clearStoredToken(); window.location.href = '/login'; throw new Error('未登录')
  }
  const j = await res.json()
  if (j.code !== 0) throw new Error(j.message ?? `HTTP ${res.status}`)
  return j.data as Goods
}

export async function uploadAdminImage(file: File): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)
  const token = getStoredToken()
  const res = await fetch(`${BASE}/uploads/image`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (res.status === 401) {
    clearStoredToken(); window.location.href = '/login'; throw new Error('未登录')
  }
  const j = await res.json()
  if (j.code !== 0) throw new Error(j.message ?? `HTTP ${res.status}`)
  return j.data.url as string
}

export const createGoodsSpec = (goodsId: string, body: { spec_name: string; price_cents?: number; stock?: number; enabled?: boolean; sku_bindings?: { timing: string; sku_id?: string | null }[] }) =>
  request<GoodsSpec>(`${BASE}/goods/${goodsId}/specs`, json('POST', body))

export const updateGoodsSpec = (goodsId: string, specId: string, body: { spec_name?: string; price_cents?: number; stock?: number; enabled?: boolean }) =>
  request<GoodsSpec>(`${BASE}/goods/${goodsId}/specs/${specId}`, json('PATCH', body))

export const deleteGoodsSpec = (goodsId: string, specId: string) =>
  request<{ deleted: string }>(`${BASE}/goods/${goodsId}/specs/${specId}`, { method: 'DELETE' })

export const setSpecBindings = (goodsId: string, specId: string, bindings: { timing: string; sku_id?: string | null }[]) =>
  request<GoodsSpec>(`${BASE}/goods/${goodsId}/specs/${specId}/bindings`, json('PUT', bindings))

export const setSpecConfig = (goodsId: string, body: SpecConfigPayload) =>
  request<Goods>(`${BASE}/goods/${goodsId}/spec-config`, json('PUT', body))

export const listXgjShops = (limit = 50, offset = 0, validOnly?: boolean) => {
  const q = [validOnly != null ? `valid_only=${validOnly}` : ''].filter(Boolean).join('&')
  return request<PageResult<XgjShop>>(`${BASE}/shops?limit=${limit}&offset=${offset}${q ? '&' + q : ''}`)
}

export const syncXgjShops = () =>
  request<XgjShopSyncResult>(`${BASE}/shops/sync`, { method: 'POST' })

export const listXgjOrders = (limit = 50, offset = 0, status?: number, goodsNo?: string) => {
  const q = [status != null ? `status=${status}` : '', goodsNo ? `goods_no=${goodsNo}` : ''].filter(Boolean).join('&')
  return request<PageResult<XgjOrder>>(`${BASE}/xgj-orders?limit=${limit}&offset=${offset}${q ? '&' + q : ''}`)
}
