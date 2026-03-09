<template>
  <div>
    <div class="toolbar">
      <span class="total-hint">共 {{ total }} 条</span>
      <button class="btn btn-primary" @click="openCreate">＋ 新增 AI 接入</button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>名称</th><th>协议</th><th>Base URL</th><th>模型数</th><th>密钥</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="7" class="empty-row">暂无 AI 接入配置</td>
          </tr>
          <tr v-for="item in items" :key="item.id">
            <td>
              <div class="cell-name">{{ item.name }}</div>
              <div class="cell-sub">更新于 {{ fmt(item.updated_at) }}</div>
            </td>
            <td><span class="badge badge-queued">{{ item.protocol }}</span></td>
            <td class="mono-text">{{ item.base_url || '使用协议默认地址' }}</td>
            <td>{{ item.models.length }}</td>
            <td>{{ item.api_key_masked || '未配置' }}</td>
            <td>
              <span :class="item.enabled ? 'badge badge-enabled' : 'badge badge-disabled'">
                {{ item.enabled ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="action-cell">
              <button class="btn btn-secondary btn-sm" :disabled="refreshingId === item.id" @click="handleRefresh(item.id)">
                {{ refreshingId === item.id ? '拉取中…' : '拉取模型' }}
              </button>
              <button class="btn btn-secondary btn-sm" @click="openEdit(item)">编辑</button>
              <button class="btn btn-danger btn-sm" @click="handleDelete(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? '编辑 AI 接入' : '新增 AI 接入'" width="680px">
      <div class="form-grid">
        <div class="form-group">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="例如：ChatAnywhere 图像服务" />
        </div>
        <div class="form-group">
          <label>协议 *</label>
          <select v-model="form.protocol">
            <option value="openai">openai</option>
            <option value="anthropic">anthropic</option>
            <option value="gemini">gemini</option>
            <option value="volcengine">volcengine</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>Base URL</label>
          <input v-model="form.base_url" placeholder="留空则使用协议默认地址" />
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>API Key <span class="inline-hint">{{ editing && activeMaskedKey ? `当前：${activeMaskedKey}` : '留空表示暂不修改' }}</span></label>
          <input v-model="form.api_key" type="password" placeholder="输入新的 API Key" />
        </div>
        <div class="form-group">
          <label>启用</label>
          <select v-model="form.enabled">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </div>
        <div class="form-group">
          <label>已保存模型</label>
          <input :value="form.models.map(item => item.id).join(', ')" readonly placeholder="点击“拉取模型”后自动填充" />
        </div>
      </div>
      <p v-if="err" class="error-text">{{ err }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  createAIProvider,
  deleteAIProvider,
  listAIProviders,
  refreshAIProviderModels,
  type AIModelItem,
  type AIProvider,
  updateAIProvider,
} from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<AIProvider[]>([])
const total = ref(0)
const showModal = ref(false)
const editing = ref<AIProvider | null>(null)
const saving = ref(false)
const err = ref('')
const refreshingId = ref('')

const defaultForm = () => ({
  name: '',
  protocol: 'openai',
  base_url: '',
  api_key: '',
  enabled: true,
  models: [] as AIModelItem[],
})

const form = ref(defaultForm())
const activeMaskedKey = computed(() => editing.value?.api_key_masked || '')

async function load() {
  const result = await listAIProviders()
  items.value = result.items
  total.value = result.total
}

function openCreate() {
  editing.value = null
  form.value = defaultForm()
  err.value = ''
  showModal.value = true
}

function openEdit(item: AIProvider) {
  editing.value = item
  form.value = {
    name: item.name,
    protocol: item.protocol,
    base_url: item.base_url || '',
    api_key: '',
    enabled: item.enabled,
    models: item.models,
  }
  err.value = ''
  showModal.value = true
}

async function handleSave() {
  if (!form.value.name.trim()) {
    err.value = '名称不能为空'
    return
  }

  saving.value = true
  err.value = ''
  try {
    const body = {
      name: form.value.name.trim(),
      protocol: form.value.protocol,
      base_url: form.value.base_url.trim() || undefined,
      api_key: form.value.api_key.trim() || undefined,
      enabled: form.value.enabled,
      models: form.value.models,
    }

    if (editing.value) {
      await updateAIProvider(editing.value.id, body)
    } else {
      await createAIProvider(body)
    }
    showModal.value = false
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleRefresh(id: string) {
  refreshingId.value = id
  try {
    const updated = await refreshAIProviderModels(id)
    items.value = items.value.map(item => item.id === id ? updated : item)
    total.value = items.value.length
    if (editing.value?.id === id) {
      editing.value = updated
      form.value.models = updated.models
    }
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : '模型拉取失败'
  } finally {
    refreshingId.value = ''
  }
}

async function handleDelete(item: AIProvider) {
  if (!confirm(`确认删除 AI 接入“${item.name}”？`)) return
  await deleteAIProvider(item.id)
  await load()
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.total-hint { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; }
.cell-name { font-weight: 600; font-size: 0.88rem; color: var(--text); }
.cell-sub { font-size: 0.77rem; color: var(--text-muted); margin-top: 2px; }
.action-cell { display: flex; gap: 6px; white-space: nowrap; }
.mono-text { font-family: Consolas, Monaco, monospace; font-size: 0.8rem; color: var(--text-muted); max-width: 280px; word-break: break-all; }
.inline-hint { color: var(--text-muted); font-weight: 400; margin-left: 4px; }
</style>