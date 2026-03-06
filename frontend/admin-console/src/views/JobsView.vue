<template>
  <div>
    <!-- 过滤器 -->
    <div class="toolbar">
      <div class="filters">
        <select v-model="statusFilter" @change="offset = 0; load()">
          <option value="">全部状态</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
          <option value="canceled">canceled</option>
        </select>
        <span class="total-hint">共 {{ total }} 条</span>
      </div>
      <button class="btn btn-secondary btn-sm" @click="load()">🔄 刷新</button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Job ID</th><th>状态</th><th>Skill</th>
            <th>创建时间</th><th>耗时</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="6" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="j in items" :key="j.id" :class="{ 'row-selected': selectedId === j.id }">
            <td>
              <code class="tiny">{{ j.id.slice(0,8) }}…</code>
            </td>
            <td><span :class="'badge badge-' + j.status">{{ j.status }}</span></td>
            <td><code class="tiny">{{ j.skill_id.slice(0,8) }}…</code></td>
            <td>{{ fmt(j.created_at) }}</td>
            <td>{{ duration(j) }}</td>
            <td>
              <button class="btn btn-secondary btn-sm" @click="openDetail(j)">详情</button>
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

    <!-- 详情弹窗 -->
    <Modal v-model="showDetail" title="Job 详情" width="680px">
      <div v-if="detail" class="detail-grid">
        <div class="detail-row"><span class="dl">ID</span><code class="dv">{{ detail.id }}</code></div>
        <div class="detail-row"><span class="dl">状态</span><span :class="'badge badge-' + detail.status">{{ detail.status }}</span></div>
        <div class="detail-row"><span class="dl">Skill</span><code class="dv">{{ detail.skill_id }}</code></div>
        <div class="detail-row"><span class="dl">创建</span><span class="dv">{{ fmtFull(detail.created_at) }}</span></div>
        <div class="detail-row" v-if="detail.started_at">
          <span class="dl">开始</span><span class="dv">{{ fmtFull(detail.started_at) }}</span>
        </div>
        <div class="detail-row" v-if="detail.finished_at">
          <span class="dl">完成</span><span class="dv">{{ fmtFull(detail.finished_at) }}</span>
        </div>
        <div class="detail-row" v-if="detail.error">
          <span class="dl">错误</span><span class="dv err">{{ detail.error }}</span>
        </div>
        <div v-if="detail.inputs" class="detail-block">
          <div class="dl">输入</div>
          <pre class="json-block">{{ JSON.stringify(detail.inputs, null, 2) }}</pre>
        </div>
        <div v-if="detail.log_text" class="detail-block">
          <div class="dl">日志</div>
          <pre class="log-block">{{ detail.log_text }}</pre>
        </div>
        <div v-if="detail.assets.length > 0" class="detail-block">
          <div class="dl">Assets</div>
          <div v-for="a in detail.assets" :key="a.id" class="asset-row">
            <span>{{ a.filename }}</span>
            <a v-if="a.download_url" :href="a.download_url" target="_blank" class="btn btn-secondary btn-sm">下载</a>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listJobs, getJob, type Job } from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<Job[]>([])
const total = ref(0)
const offset = ref(0)
const statusFilter = ref('')
const page = computed(() => Math.floor(offset.value / 20) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))

const showDetail = ref(false)
const detail = ref<Job | null>(null)
const selectedId = ref<string | null>(null)

async function load() {
  const r = await listJobs(statusFilter.value || undefined, undefined, 20, offset.value)
  items.value = r.items; total.value = r.total
}

async function openDetail(j: Job) {
  selectedId.value = j.id
  detail.value = await getJob(j.id)
  showDetail.value = true
}

function duration(j: Job) {
  if (!j.started_at || !j.finished_at) return '—'
  const ms = new Date(j.finished_at).getTime() - new Date(j.started_at).getTime()
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
function fmtFull(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
.filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.filters select { border: 1.5px solid var(--border); border-radius: 8px; padding: 7px 10px; font-size: .875rem; color: var(--text); background: var(--bg-card); outline: none; }
.filters select:focus { border-color: var(--primary); }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.tiny { font-size: .76rem; font-family: monospace; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
.row-selected td { background: var(--primary-light); }
.detail-grid { display: flex; flex-direction: column; gap: 10px; }
.detail-row { display: flex; align-items: center; gap: 12px; }
.detail-block { display: flex; flex-direction: column; gap: 6px; }
.dl { font-size: .78rem; font-weight: 700; color: var(--text-muted); min-width: 48px; }
.dv { font-size: .875rem; color: var(--text); }
.err { color: var(--danger); }
.json-block, .log-block {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 12px; font-size: .8rem; overflow: auto; max-height: 200px;
  white-space: pre-wrap; word-break: break-all; font-family: monospace; color: var(--text);
}
.asset-row { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: var(--bg); border-radius: 8px; font-size: .85rem; border: 1px solid var(--border); }
</style>
