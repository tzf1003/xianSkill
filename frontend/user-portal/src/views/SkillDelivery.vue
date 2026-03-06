<template>
  <div class="delivery-page">
    <!-- 加载中 -->
    <div v-if="phase === 'loading'" class="state-center">
      <div class="spinner" />
      <p class="hint">正在加载 Token 信息</p>
    </div>

    <!-- Token 无效 -->
    <div v-else-if="phase === 'error'" class="state-center error">
      <h2>{{ errorMsg }}</h2>
      <p>请确认链接有效，或联系服务商。</p>
    </div>

    <!-- 主界面 -->
    <template v-else>
      <!-- 信息卡 -->
      <div class="info-card">
        <div class="skill-name">{{ tokenInfo!.skill.name }}</div>
        <div class="skill-desc">{{ tokenInfo!.skill.description }}</div>
        <div class="meta-row">
          <span>套餐：{{ tokenInfo!.sku_name }}</span>
          <span v-if="isHuman" class="badge-human">人工处理</span>
          <span>剩余次数：<b>{{ tokenInfo!.remaining }}</b> / {{ tokenInfo!.total_uses }}</span>
          <span v-if="tokenInfo!.expires_at">过期：{{ fmtDate(tokenInfo!.expires_at) }}</span>
        </div>
        <div v-if="isHuman && tokenInfo!.human_sla_hours" class="sla-hint">
          预计处理时间：{{ tokenInfo!.human_sla_hours }} 小时以内
        </div>
      </div>

      <!-- 上传区（auto 模式或 human 模式首次提交） -->
      <div v-if="phase === 'idle'" class="upload-section">
        <p v-if="isHuman" class="human-tip">
          请上传您的需求材料，提交后由专业人员处理并交付结果。
        </p>
        <div
          class="drop-zone"
          :class="{ dragover: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
          @click="fileInput?.click()"
        >
          <template v-if="!selectedFile">
            <svg class="icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
              <rect x="3" y="3" width="18" height="18" rx="4"/><path d="M3 9h18M9 21V9"/>
            </svg>
            <p>点击或拖拽图片到此处</p>
            <p class="hint-small">支持 JPG / PNG / WEBP，最大 20MB</p>
          </template>
          <template v-else>
            <img :src="previewUrl" class="preview-img" alt="preview" />
            <p class="file-name">{{ selectedFile.name }}</p>
          </template>
        </div>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />

        <button class="btn-primary" :disabled="!selectedFile || submitting" @click="handleSubmit">
          {{ submitting ? '提交中' : (isHuman ? '提交需求' : '开始处理') }}
        </button>
        <p v-if="submitError" class="error-text">{{ submitError }}</p>
      </div>

      <!-- 自动处理中 -->
      <div v-else-if="phase === 'processing'" class="state-center">
        <div class="spinner" />
        <p>正在自动处理，请稍候</p>
        <p class="hint-small">状态：{{ jobStatus }}</p>
      </div>

      <!-- 人工处理等待中 -->
      <div v-else-if="phase === 'human-pending'" class="state-center human-pending">
        <div class="human-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </div>
        <h3>等待人工处理中</h3>
        <p>您的需求已收到，专业人员将在 SLA 时限内完成处理并交付结果。</p>
        <p v-if="tokenInfo!.human_sla_hours" class="hint-small">
          预计处理时间：<b>{{ tokenInfo!.human_sla_hours }} 小时以内</b>
        </p>
        <p class="hint-small">提交时间：{{ jobCreatedAt }}</p>
        <button class="btn-secondary" :disabled="refreshing" @click="checkDelivered">
          {{ refreshing ? '检查中' : '刷新查看结果' }}
        </button>
        <p class="hint-small mt-8">页面每 {{ HUMAN_POLL_SECS }} 秒自动刷新一次</p>
      </div>

      <!-- 成功（auto 或 human 交付完成） -->
      <div v-else-if="phase === 'done'" class="done-section">
        <div class="done-header">{{ isHuman ? '人工交付完成' : '处理完成' }}</div>
        <div v-if="assets.length > 0" class="asset-list">
          <div v-for="asset in assets" :key="asset.id" class="asset-item">
            <img v-if="isImage(asset.content_type)" :src="asset.download_url" class="result-img" alt="result" />
            <div class="asset-meta">
              <span>{{ asset.filename }}</span>
              <a :href="asset.download_url" target="_blank" class="btn-download">下载</a>
            </div>
          </div>
        </div>
        <button v-if="tokenInfo!.remaining > 0" class="btn-secondary" @click="reset">
          再{{ isHuman ? '提交一次' : '处理一张' }}
        </button>
      </div>

      <!-- 失败 -->
      <div v-else-if="phase === 'failed'" class="state-center error">
        <h3>处理失败</h3>
        <p>{{ jobError }}</p>
        <button class="btn-secondary" @click="reset">重试</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  getTokenInfo,
  uploadFile,
  submitJob,
  getJobStatus,
  type TokenInfo,
  type AssetOut,
} from '@/api/client'

const route = useRoute()
const tokenValue = route.params.token as string

const HUMAN_POLL_SECS = 15

type Phase = 'loading' | 'error' | 'idle' | 'processing' | 'human-pending' | 'done' | 'failed'

const phase = ref<Phase>('loading')
const errorMsg = ref('')
const tokenInfo = ref<TokenInfo | null>(null)
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const dragging = ref(false)
const submitting = ref(false)
const submitError = ref('')
const jobStatus = ref('')
const jobError = ref('')
const assets = ref<AssetOut[]>([])
const jobCreatedAt = ref('')
const refreshing = ref(false)
const currentJobId = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const isHuman = computed(() => tokenInfo.value?.delivery_mode === 'human')

onMounted(async () => {
  try {
    tokenInfo.value = await getTokenInfo(tokenValue)
    determineInitialPhase()
  } catch {
    phase.value = 'error'
    errorMsg.value = 'Token 无效或已过期'
  }
})

onUnmounted(() => { stopPoll() })

/**
 * 根据 token 信息（含 latest_job）决定初始页面状态。
 * 这样刷新页面后能恢复到正确阶段，而不是总回到 idle。
 */
function determineInitialPhase() {
  const info = tokenInfo.value!
  const job = info.latest_job

  if (info.status !== 'active') {
    phase.value = 'error'
    errorMsg.value = info.status === 'revoked' ? 'Token 已吊销' : 'Token 已过期'
    return
  }

  if (job) {
    currentJobId.value = job.id
    if (job.status === 'succeeded') {
      assets.value = job.assets
      phase.value = 'done'
      return
    }
    if (job.status === 'failed' || job.status === 'canceled') {
      jobError.value = '处理失败，请联系服务商'
      phase.value = 'failed'
      return
    }
    // queued / running
    if (isHuman.value) {
      jobCreatedAt.value = new Date(job.created_at).toLocaleString('zh-CN')
      phase.value = 'human-pending'
      startHumanPoll(job.id)
    } else {
      phase.value = 'processing'
      jobStatus.value = job.status
      startAutoPoll(job.id)
    }
    return
  }

  if (info.remaining <= 0) {
    phase.value = 'error'
    errorMsg.value = 'Token 已无可用次数'
    return
  }

  phase.value = 'idle'
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) setFile(f)
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f && f.type.startsWith('image/')) setFile(f)
}

function setFile(f: File) {
  selectedFile.value = f
  previewUrl.value = URL.createObjectURL(f)
}

async function handleSubmit() {
  if (!selectedFile.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const { object_key } = await uploadFile(tokenValue, selectedFile.value)
    const job = await submitJob(tokenValue, object_key)
    currentJobId.value = job.id
    if (isHuman.value) {
      jobCreatedAt.value = new Date(job.created_at).toLocaleString('zh-CN')
      phase.value = 'human-pending'
      startHumanPoll(job.id)
    } else {
      phase.value = 'processing'
      jobStatus.value = job.status
      startAutoPoll(job.id)
    }
  } catch (e: unknown) {
    submitError.value = e instanceof Error ? e.message : '提交失败'
  } finally {
    submitting.value = false
  }
}

/** Auto 模式：每 2 秒轮询 Job 状态 */
function startAutoPoll(jobId: string) {
  pollTimer = setInterval(async () => {
    try {
      const job = await getJobStatus(jobId)
      jobStatus.value = job.status
      if (job.status === 'succeeded') {
        stopPoll()
        assets.value = job.assets
        phase.value = 'done'
        tokenInfo.value = await getTokenInfo(tokenValue).catch(() => tokenInfo.value!)
      } else if (job.status === 'failed' || job.status === 'canceled') {
        stopPoll()
        jobError.value = job.error ?? '未知错误'
        phase.value = 'failed'
      }
    } catch { /* 短暂网络抖动，继续轮询 */ }
  }, 2000)
}

/** Human 模式：每 HUMAN_POLL_SECS 秒轮询，等待人工交付 */
function startHumanPoll(jobId: string) {
  pollTimer = setInterval(() => silentCheckDelivered(jobId), HUMAN_POLL_SECS * 1000)
}

async function silentCheckDelivered(jobId: string) {
  try {
    const job = await getJobStatus(jobId)
    if (job.status === 'succeeded') {
      stopPoll()
      assets.value = job.assets
      phase.value = 'done'
      tokenInfo.value = await getTokenInfo(tokenValue).catch(() => tokenInfo.value!)
    } else if (job.status === 'failed' || job.status === 'canceled') {
      stopPoll()
      jobError.value = '处理失败，请联系服务商'
      phase.value = 'failed'
    }
  } catch { /* ignore */ }
}

/** 手动"刷新查看结果"按钮 */
async function checkDelivered() {
  if (!currentJobId.value) return
  refreshing.value = true
  try {
    await silentCheckDelivered(currentJobId.value)
  } finally {
    refreshing.value = false
  }
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

function reset() {
  stopPoll()
  selectedFile.value = null
  previewUrl.value = ''
  submitError.value = ''
  assets.value = []
  jobStatus.value = ''
  jobError.value = ''
  currentJobId.value = null
  phase.value = 'idle'
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

function isImage(ct: string | null) {
  return ct?.startsWith('image/') ?? false
}
</script>

<style scoped>
/*  Design Tokens  */
.delivery-page {
  --bg: #FAFAFA;
  --bg-card: #FFFFFF;
  --text: #111111;
  --text-muted: #555555;
  --border: #E5E5E5;
  --accent: #8B5CF6;
  --accent2: #EC4899;
  --success: #10B981;
  --danger: #EF4444;
  --warning: #F59E0B;

  max-width: 680px;
  margin: 80px auto 60px;
  padding: 0 24px;
  font-family: 'Manrope', sans-serif;
  color: var(--text);
}

/*  States  */
.state-center {
  text-align: center; padding: 80px 0; color: var(--text-muted);
}
.state-center h2 { font-family: 'Syne', sans-serif; font-size: 1.5rem; margin-bottom: 8px; color: var(--text); }
.state-center h3 { font-family: 'Syne', sans-serif; font-size: 1.3rem; margin-bottom: 8px; color: var(--text); }

/*  Info Card  */
.info-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 24px 28px; margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.skill-name {
  font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 700;
  color: var(--text); margin-bottom: 6px;
}
.skill-desc { color: var(--text-muted); margin-bottom: 14px; font-size: 0.92rem; line-height: 1.6; }
.meta-row {
  display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.85rem;
  color: var(--text-muted); align-items: center;
}
.meta-row b { color: var(--text); font-weight: 700; }
.badge-human {
  background: rgba(249,115,22,0.1); color: #C2410C;
  padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;
  border: 1px solid rgba(249,115,22,0.2);
}
.sla-hint {
  margin-top: 10px; font-size: 0.85rem;
  color: var(--success); font-weight: 500;
  background: rgba(16,185,129,0.08); padding: 6px 12px; border-radius: 8px;
  display: inline-block;
}

/*  Upload Section  */
.upload-section { display: flex; flex-direction: column; gap: 16px; }
.human-tip {
  background: rgba(249,115,22,0.06); border: 1px solid rgba(249,115,22,0.2);
  border-radius: 10px; padding: 12px 16px; font-size: 0.9rem;
  color: #92400E; line-height: 1.6;
}
.drop-zone {
  border: 2px dashed var(--border); border-radius: 14px;
  min-height: 220px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; cursor: pointer;
  transition: background 0.2s, border-color 0.2s; padding: 20px; gap: 10px;
  background: #FAFAFF;
}
.drop-zone:hover { border-color: var(--accent); background: rgba(139,92,246,0.03); }
.drop-zone.dragover { background: rgba(139,92,246,0.06); border-color: var(--accent); border-style: solid; }
.drop-zone .icon { opacity: 0.5; color: var(--text-muted); }
.drop-zone p { color: var(--text-muted); font-size: 0.9rem; margin: 0; }
.preview-img { max-height: 200px; border-radius: 10px; object-fit: contain; }
.file-name { font-size: 0.82rem; color: var(--text-muted); }
.hint, .hint-small { color: var(--text-muted) !important; font-size: 0.82rem; margin: 0; }

/*  Buttons  */
.btn-primary {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; border: none; padding: 13px 32px; border-radius: 12px;
  font-size: 0.95rem; cursor: pointer; font-family: 'Manrope', sans-serif;
  font-weight: 600; box-shadow: 0 4px 15px rgba(139,92,246,0.3);
  transition: opacity 0.2s, transform 0.15s; align-self: flex-start;
}
.btn-primary:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:disabled { background: #CBD5E0; box-shadow: none; cursor: not-allowed; transform: none; }
.btn-secondary {
  background: rgba(139,92,246,0.08); color: var(--accent);
  border: 1px solid rgba(139,92,246,0.2); padding: 10px 24px;
  border-radius: 10px; font-size: 0.9rem; cursor: pointer;
  font-family: 'Manrope', sans-serif; font-weight: 600; margin-top: 8px;
  transition: background 0.15s; display: inline-flex; align-items: center; gap: 6px;
}
.btn-secondary:hover:not(:disabled) { background: rgba(139,92,246,0.14); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

/*  Human Pending  */
.human-pending {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 40px 32px;
}
.human-icon { color: var(--accent); margin-bottom: 16px; }
.human-pending h3 {
  font-family: 'Syne', sans-serif; font-size: 1.4rem; margin: 0 0 10px; color: var(--text);
}
.human-pending p { margin: 4px 0; color: var(--text-muted); font-size: 0.9rem; }
.mt-8 { margin-top: 10px; }

/*  Processing Spinner  */
.spinner {
  width: 50px; height: 50px;
  border: 4px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
  margin: 0 auto 20px;
}
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; border-top-color: var(--accent); } }

/*  Done Section  */
.done-section { display: flex; flex-direction: column; gap: 20px; }
.done-header {
  font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 700;
  color: var(--success); display: flex; align-items: center; gap: 8px;
}
.done-header::before {
  content: ''; width: 10px; height: 10px; border-radius: 50%;
  background: var(--success); box-shadow: 0 0 0 3px rgba(16,185,129,0.2);
}
.asset-list { display: flex; flex-direction: column; gap: 16px; }
.asset-item {
  border: 1px solid var(--border); border-radius: 14px; overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.result-img { width: 100%; max-height: 440px; object-fit: contain; background: #F1F5F9; }
.asset-meta {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; font-size: 0.85rem; background: var(--bg-card);
  border-top: 1px solid var(--border);
}
.btn-download {
  background: linear-gradient(135deg, var(--success), #06D6A0);
  color: #fff; padding: 6px 18px; border-radius: 8px;
  text-decoration: none; font-size: 0.85rem; font-weight: 600;
  box-shadow: 0 2px 8px rgba(16,185,129,0.3); transition: opacity 0.15s;
}
.btn-download:hover { opacity: 0.9; }

/*  Misc  */
.error { color: var(--danger); }
.error-text { color: var(--danger); font-size: 0.87rem; margin: 0; }
</style>