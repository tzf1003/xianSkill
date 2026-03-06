<template>
  <div class="dashboard">
    <!-- ── Page Header ── -->
    <div class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-sub">实时监控平台运营数据</p>
      </div>
      <router-link to="/jobs" class="btn btn-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M22 12h-2M4 12H2"/>
        </svg>
        查看全部 Jobs
      </router-link>
    </div>

    <!-- ── KPI Cards ── -->
    <div v-if="stats" class="kpi-grid">
      <div v-for="card in statCards" :key="card.label" class="kpi-card" :style="{'--accent-color': card.color, '--accent-light': card.light}">
        <div class="kpi-icon-wrap">
          <span v-html="card.icon"/>
        </div>
        <div class="kpi-body">
          <div class="kpi-value">{{ card.value }}</div>
          <div class="kpi-label">{{ card.label }}</div>
        </div>
        <div class="kpi-trend">
          <svg width="40" height="24" viewBox="0 0 40 24" fill="none">
            <polyline :points="card.sparkline" stroke="var(--accent-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
      </div>
    </div>
    <div v-else class="kpi-skeleton-grid">
      <div v-for="i in 5" :key="i" class="kpi-skeleton"/>
    </div>

    <!-- ── Charts Row ── -->
    <div class="charts-row">
      <!-- Job 状态分布 -->
      <div class="chart-card" v-if="stats">
        <div class="chart-header">
          <div>
            <h2 class="chart-title">Job 状态分布</h2>
            <p class="chart-sub">当前全部 Job 状态占比</p>
          </div>
          <div class="chart-total">
            <span class="chart-total-num">{{ stats.total_jobs }}</span>
            <span class="chart-total-lbl">总计</span>
          </div>
        </div>
        <div class="job-bars">
          <div v-for="bar in jobBars" :key="bar.label" class="bar-row">
            <div class="bar-meta">
              <span class="bar-dot" :style="{'background': bar.color}"/>
              <span class="bar-label">{{ bar.label }}</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: bar.pct + '%', background: `linear-gradient(90deg, ${bar.color}cc, ${bar.color})` }"/>
            </div>
            <div class="bar-count">{{ bar.count }}</div>
            <div class="bar-pct">{{ bar.pct }}%</div>
          </div>
        </div>
      </div>

      <!-- Quick Stats Mini ── -->
      <div class="mini-stats-col">
        <div class="mini-stat-card" v-if="stats">
          <div class="mini-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            成功率
          </div>
          <div class="mini-value">{{ successRate }}%</div>
          <div class="mini-bar-wrap">
            <div class="mini-bar" :style="{width: successRate + '%'}"/>
          </div>
        </div>
        <div class="mini-stat-card accent-orange" v-if="stats">
          <div class="mini-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            进行中 Jobs
          </div>
          <div class="mini-value">{{ (stats.jobs_running || 0) + (stats.jobs_queued || 0) }}</div>
          <div class="mini-note">{{ stats.jobs_running || 0 }} 运行 + {{ stats.jobs_queued || 0 }} 排队</div>
        </div>
        <div class="mini-stat-card accent-purple" v-if="stats">
          <div class="mini-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            活跃 Tokens
          </div>
          <div class="mini-value">{{ stats.total_tokens }}</div>
          <div class="mini-note">全部已发放</div>
        </div>
      </div>
    </div>

    <!-- ── Recent Jobs Table ── -->
    <div class="table-card">
      <div class="table-header">
        <div>
          <h2 class="chart-title">最近 Jobs</h2>
          <p class="chart-sub">最近 10 条作业记录</p>
        </div>
        <router-link to="/jobs" class="btn btn-ghost btn-sm">查看全部 →</router-link>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Skill</th>
              <th>状态</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="recentJobs.length === 0">
              <td colspan="4" class="empty-row">
                <div class="empty-state">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".4">
                    <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                  </svg>
                  <span>暂无数据</span>
                </div>
              </td>
            </tr>
            <tr v-for="job in recentJobs" :key="job.id">
              <td><code class="mono-id">{{ job.id.slice(0, 8) }}…</code></td>
              <td><code class="mono-id">{{ job.skill_id.slice(0, 8) }}…</code></td>
              <td><span :class="'badge badge-' + job.status">{{ job.status }}</span></td>
              <td class="time-cell">{{ fmt(job.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getStats, listJobs, type Stats, type Job } from '@/api/client'

const stats = ref<Stats | null>(null)
const recentJobs = ref<Job[]>([])

const statCards = computed(() => stats.value ? [
  {
    label: 'Skills', value: stats.value.total_skills,
    color: '#2563EB', light: '#EFF6FF',
    sparkline: '0,20 8,14 16,18 24,10 32,15 40,8',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`
  },
  {
    label: 'SKUs', value: stats.value.total_skus,
    color: '#7C3AED', light: '#F5F3FF',
    sparkline: '0,16 8,20 16,12 24,18 32,10 40,14',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`
  },
  {
    label: '订单', value: stats.value.total_orders,
    color: '#0891B2', light: '#ECFEFF',
    sparkline: '0,18 8,12 16,20 24,14 32,18 40,10',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>`
  },
  {
    label: 'Tokens', value: stats.value.total_tokens,
    color: '#F97316', light: '#FFF7ED',
    sparkline: '0,14 8,18 16,10 24,20 32,12 40,16',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>`
  },
  {
    label: 'Jobs', value: stats.value.total_jobs,
    color: '#10B981', light: '#ECFDF5',
    sparkline: '0,20 8,10 16,18 24,8 32,20 40,12',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M22 12h-2M4 12H2M18.66 18.66l-1.41-1.41M6.34 5.34l-1.41 1.41"/></svg>`
  },
] : [])

const jobBars = computed(() => {
  if (!stats.value) return []
  const total = stats.value.total_jobs || 1
  return [
    { label: '成功', count: stats.value.jobs_succeeded, color: '#10B981', pct: Math.round(stats.value.jobs_succeeded / total * 100) },
    { label: '失败', count: stats.value.jobs_failed,    color: '#EF4444', pct: Math.round(stats.value.jobs_failed    / total * 100) },
    { label: '运行中', count: stats.value.jobs_running,  color: '#F59E0B', pct: Math.round(stats.value.jobs_running  / total * 100) },
    { label: '排队中', count: stats.value.jobs_queued,   color: '#3B82F6', pct: Math.round(stats.value.jobs_queued   / total * 100) },
  ]
})

const successRate = computed(() => {
  if (!stats.value || !stats.value.total_jobs) return 0
  return Math.round(stats.value.jobs_succeeded / stats.value.total_jobs * 100)
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
/* ── Page Header ── */
.dashboard { display: flex; flex-direction: column; gap: 24px; }
.page-header {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.page-title {
  font-family: 'Poppins', sans-serif; font-size: 1.6rem; font-weight: 700;
  color: var(--text); letter-spacing: -0.01em;
}
.page-sub { font-size: 0.875rem; color: var(--text-muted); margin-top: 2px; }

/* ── KPI Cards ── */
.kpi-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px;
}
.kpi-card {
  background: var(--bg-card); border-radius: 14px;
  border: 1px solid var(--border); padding: 18px 18px 14px;
  display: flex; flex-direction: column; gap: 4px;
  box-shadow: var(--shadow-sm); transition: box-shadow 0.2s, transform 0.2s;
  position: relative; overflow: hidden;
}
.kpi-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent-color); border-radius: 14px 14px 0 0;
}
.kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.kpi-icon-wrap {
  width: 40px; height: 40px; border-radius: 10px;
  background: var(--accent-light); color: var(--accent-color);
  display: flex; align-items: center; justify-content: center; margin-bottom: 8px;
}
.kpi-value {
  font-family: 'Poppins', sans-serif; font-size: 2rem; font-weight: 700;
  color: var(--text); line-height: 1;
}
.kpi-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 500; }
.kpi-trend { margin-top: 4px; }

/* Skeleton */
.kpi-skeleton-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }
.kpi-skeleton {
  height: 130px; border-radius: 14px;
  background: linear-gradient(90deg, #F1F5F9 25%, #E2E8F0 50%, #F1F5F9 75%);
  background-size: 200% 100%; animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .kpi-skeleton { animation: none; } }

/* ── Charts Row ── */
.charts-row { display: grid; grid-template-columns: 1fr 280px; gap: 20px; align-items: stretch; }

.chart-card, .table-card {
  background: var(--bg-card); border-radius: 14px;
  border: 1px solid var(--border); padding: 22px 24px;
  box-shadow: var(--shadow-sm);
}
.chart-card { display: flex; flex-direction: column; }
.chart-card .job-bars { flex: 1; justify-content: center; }
.chart-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
.chart-title { font-family: 'Poppins', sans-serif; font-size: 1rem; font-weight: 700; color: var(--text); }
.chart-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }
.chart-total { text-align: right; }
.chart-total-num { font-family: 'Poppins', sans-serif; font-size: 1.6rem; font-weight: 700; color: var(--text); display: block; line-height: 1; }
.chart-total-lbl { font-size: 0.75rem; color: var(--text-muted); }

/* Job Bars */
.job-bars { display: flex; flex-direction: column; gap: 14px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-meta { display: flex; align-items: center; gap: 6px; width: 64px; flex-shrink: 0; }
.bar-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.bar-label { font-size: 0.82rem; color: var(--text-muted); white-space: nowrap; }
.bar-track { flex: 1; height: 10px; background: var(--bg); border-radius: 5px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 5px; transition: width 0.6s ease-out; }
.bar-count { width: 32px; font-size: 0.82rem; color: var(--text); font-weight: 600; text-align: right; }
.bar-pct { width: 38px; font-size: 0.75rem; color: var(--text-muted); text-align: right; }

/* Mini Stats */
.mini-stats-col { display: flex; flex-direction: column; gap: 12px; }
.mini-stat-card {
  background: var(--bg-card); border-radius: 14px;
  border: 1px solid var(--border); padding: 16px 18px;
  box-shadow: var(--shadow-sm);
}
.mini-stat-card.accent-orange { border-top: 3px solid #F97316; }
.mini-stat-card.accent-purple { border-top: 3px solid #7C3AED; }
.mini-header {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.78rem; font-weight: 600; color: var(--text-muted);
  margin-bottom: 8px;
}
.mini-value {
  font-family: 'Poppins', sans-serif; font-size: 1.8rem; font-weight: 700; color: var(--text);
  line-height: 1; margin-bottom: 6px;
}
.mini-bar-wrap { height: 4px; background: var(--bg); border-radius: 2px; overflow: hidden; }
.mini-bar { height: 100%; background: linear-gradient(90deg, #10B981, #06D6A0); border-radius: 2px; transition: width 0.8s ease-out; }
.mini-note { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }

/* ── Table Card ── */
.table-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid var(--border); }
.mono-id { font-size: 0.78rem; font-family: monospace; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
.time-cell { font-size: 0.82rem; color: var(--text-muted); white-space: nowrap; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--text-muted); padding: 24px; }

/* Responsive */
@media (max-width: 900px) {
  .charts-row { grid-template-columns: 1fr; }
  .mini-stats-col { flex-direction: row; flex-wrap: wrap; }
  .mini-stat-card { flex: 1; min-width: 160px; }
}
</style>
