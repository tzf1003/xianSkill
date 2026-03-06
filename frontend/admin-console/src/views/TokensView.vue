<template>
  <div>
    <!-- 过滤器 -->
    <div class="toolbar">
      <div class="filters">
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
            <th>Token（前16位）</th><th>状态</th>
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
              <code class="token-text">{{ t.token.slice(0, 16) }}…</code>
              <button class="copy-btn" @click="copy(t.token)" title="复制完整 token">📋</button>
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
                class="btn btn-danger btn-sm"
                @click="handleRevoke(t.id)"
              >撤销</button>
              <span v-else class="badge badge-revoked">已撤销</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listTokens, revokeToken, type Token } from '@/api/client'

const items = ref<Token[]>([])
const total = ref(0)
const offset = ref(0)
const statusFilter = ref('')
const page = computed(() => Math.floor(offset.value / 20) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))

async function load() {
  const r = await listTokens(statusFilter.value || undefined, 20, offset.value)
  items.value = r.items; total.value = r.total
}

async function handleRevoke(id: string) {
  if (!confirm('确认撤销此 Token？撤销后用户将无法继续使用。')) return
  await revokeToken(id)
  await load()
}

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'))
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filters { display: flex; align-items: center; gap: 12px; }
.filters select { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: .875rem; }
.total-hint { font-size: .85rem; color: #888; }
.token-text { font-size: .8rem; color: #333; }
.copy-btn { background: none; border: none; cursor: pointer; font-size: .9rem; margin-left: 4px; }
.remaining-ok { color: #22c55e; font-weight: 700; }
.remaining-zero { color: #ef4444; font-weight: 700; }
</style>
