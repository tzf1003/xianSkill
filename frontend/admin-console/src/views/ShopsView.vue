<template>
  <div>
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="total-hint">共 {{ total }} 家店铺</span>
        <select v-model="validOnly" class="filter-select" @change="offset = 0; load()">
          <option :value="undefined">全部状态</option>
          <option :value="true">仅有效订购</option>
          <option :value="false">仅无效订购</option>
        </select>
      </div>
      <div class="toolbar-right">
        <span v-if="syncSummary" class="sync-summary">{{ syncSummary }}</span>
        <button class="btn btn-primary" :disabled="syncing" @click="handleSync">
          {{ syncing ? '同步中…' : '一键同步闲管家店铺' }}
        </button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-label">有效订购</div>
        <div class="stat-value">{{ validCount }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">鱼小铺</div>
        <div class="stat-value">{{ proCount }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">已缴保证金</div>
        <div class="stat-value">{{ depositCount }}</div>
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>店铺</th>
            <th>会员名</th>
            <th>昵称</th>
            <th>授权ID</th>
            <th>用户标识</th>
            <th>业务类型</th>
            <th>服务项</th>
            <th>状态</th>
            <th>有效期至</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="10" class="empty-row">暂无数据，请先同步闲管家店铺</td>
          </tr>
          <tr v-for="shop in items" :key="shop.id">
            <td>
              <div class="shop-name-cell">
                <b>{{ shop.shop_name }}</b>
                <span v-if="shop.is_trial" class="badge badge-expired">试用版</span>
              </div>
            </td>
            <td>{{ shop.user_name }}</td>
            <td>{{ shop.user_nick }}</td>
            <td><span class="tiny">{{ shop.authorize_id }}</span></td>
            <td><span class="identity-text">{{ shop.user_identity }}</span></td>
            <td>{{ formatBizTypes(shop.item_biz_types) }}</td>
            <td>{{ shop.service_support || '—' }}</td>
            <td>
              <div class="status-stack">
                <span :class="shop.is_valid ? 'badge badge-active' : 'badge badge-revoked'">
                  {{ shop.is_valid ? '有效订购' : '无效订购' }}
                </span>
                <span :class="shop.is_pro ? 'badge badge-info' : 'badge badge-expired'">
                  {{ shop.is_pro ? '鱼小铺' : '普通店铺' }}
                </span>
                <span :class="shop.is_deposit_enough ? 'badge badge-succeeded' : 'badge badge-revoked'">
                  {{ shop.is_deposit_enough ? '保证金充足' : '保证金不足' }}
                </span>
              </div>
            </td>
            <td>{{ formatUnix(shop.valid_end_time) }}</td>
            <td>{{ fmt(shop.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="errorText" class="error-text page-error">{{ errorText }}</p>
      <div class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= PAGE_SIZE; load()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="offset + PAGE_SIZE >= total" @click="offset += PAGE_SIZE; load()">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listXgjShops, syncXgjShops, type XgjShop } from '@/api/client'

const PAGE_SIZE = 20

const items = ref<XgjShop[]>([])
const total = ref(0)
const offset = ref(0)
const validOnly = ref<boolean | undefined>(undefined)
const syncing = ref(false)
const errorText = ref('')
const syncSummary = ref('')

const page = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const validCount = computed(() => items.value.filter(shop => shop.is_valid).length)
const proCount = computed(() => items.value.filter(shop => shop.is_pro).length)
const depositCount = computed(() => items.value.filter(shop => shop.is_deposit_enough).length)

async function load() {
  errorText.value = ''
  const result = await listXgjShops(PAGE_SIZE, offset.value, validOnly.value)
  items.value = result.items
  total.value = result.total
}

async function handleSync() {
  syncing.value = true
  errorText.value = ''
  syncSummary.value = ''
  try {
    const result = await syncXgjShops()
    syncSummary.value = `同步 ${result.synced} 条，新增 ${result.created}，更新 ${result.updated}，删除 ${result.deleted}`
    offset.value = 0
    await load()
  } catch (error: unknown) {
    errorText.value = error instanceof Error ? error.message : '同步失败'
  } finally {
    syncing.value = false
  }
}

function formatBizTypes(value: string) {
  return value || '—'
}

function formatUnix(value: number) {
  if (!value) return '—'
  return new Date(value * 1000).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 12px; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 12px; }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.filter-select {
  padding: 5px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: .82rem; background: #fff; color: var(--text);
  font-family: 'Open Sans', sans-serif;
}
.sync-summary { font-size: .85rem; color: var(--text-muted); }
.stats-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px;
  margin-bottom: 16px;
}
.stat-card { padding: 16px 18px; }
.stat-label { font-size: .8rem; color: var(--text-muted); margin-bottom: 8px; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: var(--text); }
.tiny { font-size: .75rem; font-family: monospace; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
.shop-name-cell { display: flex; align-items: center; gap: 8px; }
.identity-text { display: inline-block; max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-stack { display: flex; flex-wrap: wrap; gap: 6px; }
.page-error { margin-top: 12px; }

@media (max-width: 960px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-left, .toolbar-right { justify-content: space-between; flex-wrap: wrap; }
  .stats-grid { grid-template-columns: 1fr; }
}
</style>