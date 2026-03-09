<template>
  <div>
    <!-- Header -->
    <div class="tv-header">
      <div>
        <h1 class="tv-title">Tokens</h1>
        <p class="tv-sub">管理所有交付凭证</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 手动新增 Token</button>
    </div>

    <!-- Filters -->
    <div class="toolbar">
      <div class="filters">
        <!-- 项目过滤 -->
        <select v-model="projectFilter" @change="offset = 0; load()">
          <option value="">所有项目</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <!-- 状态过滤 -->
        <select v-model="statusFilter" @change="offset = 0; load()">
          <option value="">全部状态</option>
          <option value="active">active</option>
          <option value="expired">expired</option>
          <option value="revoked">revoked</option>
        </select>
        <span class="total-hint">共 {{ total }} 条</span>
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Token</th><th>状态</th>
            <th>已用 / 总次</th><th>剩余</th>
            <th>过期时间</th><th>创建时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="7" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="t in items" :key="t.id">
            <td>
              <code class="token-text">{{ t.token }}</code>
              <button class="copy-btn" @click="copy(t.token)" title="复制完整 token"></button>
              <a class="link-btn" :href="`/s/${t.token}`" target="_blank" title="在用户端打开"></a>
            </td>
            <td><span :class="'badge badge-' + t.status">{{ t.status }}</span></td>
            <td>{{ t.used_count }} / {{ t.total_uses }}</td>
            <td>
              <span :class="t.remaining > 0 ? 'remaining-ok' : 'remaining-zero'">{{ t.remaining }}</span>
            </td>
            <td>{{ t.expires_at ? fmt(t.expires_at) : '永久' }}</td>
            <td>{{ fmt(t.created_at) }}</td>
            <td>
              <button
                v-if="t.status === 'active'"
                class="btn btn-secondary btn-sm"
                @click="handleGrantUses(t)"
              >添加次数</button>
              <button
                v-if="t.status === 'active'"
                class="btn btn-danger btn-sm"
                @click="handleRevoke(t.id)"
              >撤销</button>
              <span v-else class="badge badge-revoked">已操作</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= 20; load()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="offset + 20 >= total" @click="offset += 20; load()">下一页</button>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="modal-backdrop">
      <div class="modal-box">
        <div class="modal-header">
          <h2>手动新增 Token</h2>
          <button class="modal-close" @click="showCreate = false"></button>
        </div>
        <div class="modal-body">
          <!-- Step 1: 选择项目 -->
          <label class="field-label">项目 <span class="req">*</span></label>
          <select v-model="form.projectId" class="field-select" @change="onProjectChange">
            <option value="">请选择项目</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>

          <!-- Step 2: 选择 SKU -->
          <label class="field-label">套餐（SKU）<span class="req">*</span></label>
          <select v-model="form.skuId" class="field-select" :disabled="!form.projectId || projectSkus.length === 0">
            <option value="">{{ form.projectId ? (projectSkusLoading ? '加载中' : (projectSkus.length ? '请选择套餐' : '该项目暂无套餐')) : '请先选择项目' }}</option>
            <option v-for="s in projectSkus" :key="s.id" :value="s.id">
              {{ s.name }}（{{ deliveryModeLabel(s.delivery_mode) }}，{{ s.total_uses }}次）
            </option>
          </select>

          <!-- Step 3: 次数（可覆盖） -->
          <label class="field-label">可用次数</label>
          <div class="field-hint">留空则使用套餐默认值（{{ selectedSkuUses ?? '' }}次）</div>
          <input v-model.number="form.totalUses" type="number" min="1" class="field-input" placeholder="自定义次数（可选）" />

          <!-- Step 4: 过期时间 -->
          <label class="field-label">过期时间（可选）</label>
          <input v-model="form.expiresAt" type="datetime-local" class="field-input" />

          <!-- Step 5: 来源备注 -->
          <label class="field-label">来源渠道</label>
          <input v-model="form.channel" class="field-input" placeholder="manual（默认）" />

          <p v-if="createError" class="inline-error"> {{ createError }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showCreate = false">取消</button>
          <button class="btn-save" :disabled="!form.skuId || creating" @click="doCreate">
            {{ creating ? '创建中' : '创建 Token' }}
          </button>
        </div>

        <!-- 成功展示 -->
        <div v-if="createdToken" class="created-result">
          <div class="cr-title"> Token 已创建！</div>
          <div class="cr-row">
            <code class="cr-token">{{ createdToken }}</code>
            <button class="copy-btn" @click="copy(createdToken)"> 复制</button>
          </div>
          <div class="cr-row">
            <span class="cr-label">用户访问链接：</span>
            <a :href="`/s/${createdToken}`" target="_blank" class="cr-link">/s/{{ createdToken }}</a>
            <button class="copy-btn" @click="copy(`/s/${createdToken}`)"></button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  listTokens, revokeToken, createToken, grantTokenUses, listSKUs, listProjects,
  type Token, type SKU, type Project,
} from '@/api/client'

const items = ref<Token[]>([])
const total = ref(0)
const offset = ref(0)
const statusFilter = ref('')
const projectFilter = ref('')
const projects = ref<Project[]>([])
const page = computed(() => Math.floor(offset.value / 20) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))

// Modal state
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createdToken = ref('')
const projectSkus = ref<SKU[]>([])
const projectSkusLoading = ref(false)
const form = ref({ projectId: '', skuId: '', totalUses: undefined as number | undefined, expiresAt: '', channel: 'manual' })
const selectedSkuUses = computed(() => projectSkus.value.find(s => s.id === form.value.skuId)?.total_uses)

async function load() {
  const r = await listTokens(statusFilter.value || undefined, 20, offset.value, projectFilter.value || undefined)
  items.value = r.items; total.value = r.total
}

async function handleRevoke(id: string) {
  if (!confirm('确认撤销此 Token？撤销后用户将无法继续使用。')) return
  await revokeToken(id)
  await load()
}

async function handleGrantUses(token: Token) {
  const value = window.prompt(`请输入要为该 Token 增加的次数。\n当前剩余：${token.remaining}，当前总次数：${token.total_uses}`, '1')
  if (value === null) return

  const uses = Number.parseInt(value, 10)
  if (!Number.isInteger(uses) || uses <= 0) {
    alert('请输入大于 0 的整数次数')
    return
  }

  try {
    await grantTokenUses(token.id, uses)
    await load()
    alert(`已成功增加 ${uses} 次`)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : '添加次数失败，请重试')
  }
}

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'))
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function deliveryModeLabel(mode: string) {
  if (mode === 'auto') return '付款后发放'
  if (mode === 'after_receipt') return '收货后赠送'
  if (mode === 'after_review') return '好评后赠送'
  if (mode === 'human') return '人工处理'
  return mode
}

async function openCreate() {
  form.value = { projectId: '', skuId: '', totalUses: undefined, expiresAt: '', channel: 'manual' }
  projectSkus.value = []
  createError.value = ''
  createdToken.value = ''
  showCreate.value = true
}

async function onProjectChange() {
  form.value.skuId = ''
  if (!form.value.projectId) { projectSkus.value = []; return }
  projectSkusLoading.value = true
  try {
    const r = await listSKUs(undefined, 200, 0, form.value.projectId)
    projectSkus.value = r.items.filter(s => s.enabled !== false)
  } catch { projectSkus.value = [] }
  finally { projectSkusLoading.value = false }
}

async function doCreate() {
  createError.value = ''
  creating.value = true
  try {
    const body: { sku_id: string; total_uses?: number; expires_at?: string | null; channel?: string } = {
      sku_id: form.value.skuId,
      channel: form.value.channel || 'manual',
    }
    if (form.value.totalUses) body.total_uses = form.value.totalUses
    if (form.value.expiresAt) body.expires_at = new Date(form.value.expiresAt).toISOString()
    const t = await createToken(body)
    createdToken.value = t.token
    await load()
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : '创建失败，请重试'
  } finally { creating.value = false }
}

onMounted(async () => {
  const [, pr] = await Promise.all([load(), listProjects(200)])
  projects.value = pr.items
})
</script>

<style scoped>
.tv-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.tv-title { font-size: 1.5rem; font-weight: 700; }
.tv-sub { color: var(--text-muted); font-size: 0.88rem; margin-top: 4px; }
.btn-primary { padding: 10px 20px; background: linear-gradient(135deg,#8B5CF6,#EC4899); color: white; border: none; border-radius: 10px; font-weight: 600; cursor: pointer; white-space: nowrap; font-size: 0.9rem; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
.filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.filters select { border: 1.5px solid var(--border); border-radius: 8px; padding: 7px 10px; font-size: .875rem; color: var(--text); background: var(--bg-card); outline: none; cursor: pointer; }
.filters select:focus { border-color: var(--primary); }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.token-text { font-size: .78rem; color: var(--text-muted); font-family: monospace; }
.copy-btn { background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 0 4px; transition: color 0.15s; }
.copy-btn:hover { color: var(--primary); }
.link-btn { background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 0 4px; text-decoration: none; font-size: 0.85rem; }
.link-btn:hover { color: var(--primary); }
.remaining-ok { color: #10B981; font-weight: 700; }
.remaining-zero { color: var(--danger); font-weight: 700; }
/* Modal */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-box { background: white; border-radius: 20px; width: 100%; max-width: 520px; max-height: 92vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 24px 28px 16px; border-bottom: 1px solid #F1F5F9; }
.modal-header h2 { font-size: 1.1rem; font-weight: 700; }
.modal-close { background: none; border: none; cursor: pointer; color: #94A3B8; font-size: 1.1rem; }
.modal-body { padding: 20px 28px; display: flex; flex-direction: column; gap: 10px; }
.modal-footer { padding: 16px 28px 24px; display: flex; justify-content: flex-end; gap: 10px; }
.field-label { font-size: 0.82rem; font-weight: 600; color: #475569; }
.req { color: #EF4444; }
.field-hint { font-size: 0.76rem; color: #94A3B8; margin-top: -6px; }
.field-select, .field-input { width: 100%; padding: 9px 12px; border: 1.5px solid #E2E8F0; border-radius: 9px; font-size: 0.9rem; outline: none; transition: border-color 0.15s; background: white; }
.field-select:focus, .field-input:focus { border-color: #8B5CF6; }
.field-select:disabled { opacity: 0.5; cursor: not-allowed; }
.inline-error { background: #FEE2E2; color: #991B1B; border-radius: 8px; padding: 8px 12px; font-size: 0.84rem; }
.btn-cancel { padding: 9px 18px; border-radius: 9px; border: 1.5px solid #E2E8F0; background: white; color: #64748B; font-weight: 600; cursor: pointer; }
.btn-save { padding: 9px 22px; border-radius: 9px; background: linear-gradient(135deg,#8B5CF6,#EC4899); color: white; border: none; font-weight: 600; cursor: pointer; }
.btn-save:disabled { opacity: 0.45; cursor: not-allowed; }
.created-result { margin: 0 28px 24px; background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.cr-title { font-weight: 700; color: #15803D; }
.cr-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cr-token { font-family: monospace; font-size: 0.8rem; background: white; border: 1px solid #D1FAE5; padding: 4px 8px; border-radius: 6px; word-break: break-all; flex: 1; }
.cr-label { font-size: 0.82rem; color: #475569; }
.cr-link { font-size: 0.82rem; color: #7C3AED; text-decoration: none; font-weight: 600; }
</style>