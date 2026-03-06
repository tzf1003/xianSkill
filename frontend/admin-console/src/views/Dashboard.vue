<template>
  <div>
    <!-- 统计卡片 -->
    <div v-if="stats" class="stats-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.label">
        <div class="stat-icon">{{ card.icon }}</div>
        <div class="stat-body">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>
    <div v-else class="card" style="text-align:center;padding:40px;color:#aaa">加载中…</div>

    <!-- Job 状态分布 -->
    <div v-if="stats" class="card mt" style="margin-top:20px">
      <div class="section-title">Job 状态分布</div>
      <div class="job-bars">
        <div v-for="bar in jobBars" :key="bar.label" class="bar-row">
          <div class="bar-label">{{ bar.label }}</div>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: bar.pct + '%', background: bar.color }" />
          </div>
          <div class="bar-count">{{ bar.count }}</div>
        </div>
      </div>
    </div>

    <!-- 最近 Jobs -->
    <div class="card" style="margin-top:20px">
      <div class="section-title-row">
        <div class="section-title">最近 Jobs</div>
        <router-link to="/jobs" class="btn btn-secondary btn-sm">查看全部</router-link>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Job ID</th><th>Skill</th><th>状态</th><th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="recentJobs.length === 0">
            <td colspan="4" class="empty-row" style="text-align:center;color:#aaa;padding:24px">暂无数据</td>
          </tr>
          <tr v-for="job in recentJobs" :key="job.id">
            <td><code style="font-size:.77rem">{{ job.id.slice(0,8) }}…</code></td>
            <td><code style="font-size:.77rem">{{ job.skill_id.slice(0,8) }}…</code></td>
            <td><span :class="'badge badge-' + job.status">{{ job.status }}</span></td>
            <td>{{ fmt(job.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getStats, listJobs, type Stats, type Job } from '@/api/client'

const stats = ref<Stats | null>(null)
const recentJobs = ref<Job[]>([])

const statCards = computed(() => stats.value ? [
  { icon: '🧠', label: 'Skills', value: stats.value.total_skills },
  { icon: '🏷️', label: 'SKUs', value: stats.value.total_skus },
  { icon: '📦', label: '订单', value: stats.value.total_orders },
  { icon: '🔑', label: 'Tokens', value: stats.value.total_tokens },
  { icon: '⚡', label: 'Jobs', value: stats.value.total_jobs },
] : [])

const jobBars = computed(() => {
  if (!stats.value) return []
  const total = stats.value.total_jobs || 1
  return [
    { label: '成功', count: stats.value.jobs_succeeded, color: '#22c55e', pct: Math.round(stats.value.jobs_succeeded / total * 100) },
    { label: '失败', count: stats.value.jobs_failed, color: '#ef4444', pct: Math.round(stats.value.jobs_failed / total * 100) },
    { label: '运行中', count: stats.value.jobs_running, color: '#f59e0b', pct: Math.round(stats.value.jobs_running / total * 100) },
    { label: '排队中', count: stats.value.jobs_queued, color: '#3b82f6', pct: Math.round(stats.value.jobs_queued / total * 100) },
  ]
})

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  const [s, j] = await Promise.all([getStats(), listJobs(undefined, undefined, 10)])
  stats.value = s
  recentJobs.value = j.items
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 16px;
}
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.07);
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon { font-size: 2rem; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; line-height: 1; }
.stat-label { font-size: 0.78rem; color: #888; margin-top: 4px; }
.section-title { font-size: 0.95rem; font-weight: 700; margin-bottom: 16px; color: #1a1a2e; }
.section-title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.section-title-row .section-title { margin-bottom: 0; }
.job-bars { display: flex; flex-direction: column; gap: 12px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-label { width: 50px; font-size: 0.82rem; color: #555; text-align: right; }
.bar-track { flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width .4s; }
.bar-count { width: 36px; font-size: 0.8rem; color: #666; }
</style>
