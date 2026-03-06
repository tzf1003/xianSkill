<template>
  <div>
    <div class="toolbar">
      <span class="total-hint">共 {{ total }} 条</span>
      <button class="btn btn-primary" @click="openCreate">＋ 新建订单</button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr><th>订单 ID</th><th>SKU ID</th><th>状态</th><th>渠道</th><th>Token 链接</th><th>创建时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="6" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="o in items" :key="o.id">
            <td><code class="tiny">{{ o.id.slice(0,8) }}…</code></td>
            <td><code class="tiny">{{ o.sku_id.slice(0,8) }}…</code></td>
            <td><span :class="'badge badge-' + o.status">{{ o.status }}</span></td>
            <td>{{ o.channel ?? '—' }}</td>
            <td>
              <a v-if="o.token_url" :href="portalBase + o.token_url" target="_blank" class="link">
                {{ o.token_url }}
              </a>
              <span v-else>—</span>
            </td>
            <td>{{ fmt(o.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= 20; load()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="offset + 20 >= total" @click="offset += 20; load()">下一页</button>
      </div>
    </div>

    <Modal v-model="showModal" title="新建订单">
      <div class="form-group">
        <label>SKU *</label>
        <select v-model="form.sku_id">
          <option value="">— 选择 SKU —</option>
          <option v-for="s in skus" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="form-group">
        <label>渠道（可选）</label>
        <input v-model="form.channel" placeholder="例：weixin / direct" />
      </div>
      <p v-if="err" class="error-text">{{ err }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleCreate">{{ saving ? '创建中…' : '创建' }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listOrders, createOrder, listSKUs, type Order, type SKU } from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<Order[]>([])
const skus = ref<SKU[]>([])
const total = ref(0)
const offset = ref(0)
const page = computed(() => Math.floor(offset.value / 20) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))
const portalBase = 'http://localhost:5173'

const showModal = ref(false)
const saving = ref(false)
const err = ref('')
const form = ref({ sku_id: '', channel: '' })

async function load() {
  const [r, s] = await Promise.all([listOrders(20, offset.value), listSKUs(undefined, 200)])
  items.value = r.items; total.value = r.total; skus.value = s.items
}

function openCreate() { form.value = { sku_id: '', channel: '' }; err.value = ''; showModal.value = true }

async function handleCreate() {
  if (!form.value.sku_id) { err.value = '请选择 SKU'; return }
  saving.value = true; err.value = ''
  try {
    await createOrder({ sku_id: form.value.sku_id, channel: form.value.channel || undefined })
    showModal.value = false; await load()
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : '创建失败' }
  finally { saving.value = false }
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.total-hint { font-size: .85rem; color: #888; }
.tiny { font-size: .75rem; }
.link { color: #4f6aff; font-size: .82rem; text-decoration: underline; }
</style>
