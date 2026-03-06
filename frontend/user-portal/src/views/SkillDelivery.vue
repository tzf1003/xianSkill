<template>
  <div class="wizard-page">
    <!--  加载中  -->
    <div v-if="phase === 'loading'" class="full-center">
      <div class="loader-ring" />
      <p class="loader-hint">正在加载，请稍候</p>
    </div>

    <!--  Token 无效  -->
    <div v-else-if="phase === 'error'" class="full-center error-state">
      <div class="error-icon"></div>
      <h2>{{ errorMsg }}</h2>
      <p>请确认链接有效，或联系服务商获取新的访问链接。</p>
      <button class="btn-home" @click="$router.push('/')">返回首页</button>
    </div>

    <!--  主向导  -->
    <template v-else>
      <!-- 顶部品牌 + 项目名 -->
      <header class="wizard-header">
        <div class="wh-logo" @click="$router.push('/')">
          <svg width="26" height="26" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#wl-grad)"/>
            <path d="M14 6L17.5 12.5H21L15.5 17L17.5 22L14 18.5L10.5 22L12.5 17L7 12.5H10.5L14 6Z" fill="white" opacity="0.9"/>
            <defs><linearGradient id="wl-grad" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#8B5CF6"/><stop offset="1" stop-color="#EC4899"/></linearGradient></defs>
          </svg>
          <span>ArtForge</span>
        </div>
        <div class="wh-title">{{ projectInfo?.name || tokenInfo?.skill.name || 'AI 图像处理' }}</div>
        <div class="wh-meta">剩余&nbsp;<b>{{ tokenInfo?.remaining ?? '-' }}</b>&nbsp;次</div>
      </header>

      <!-- 步骤进度条 -->
      <div v-if="phase === 'wizard'" class="steps-bar">
        <div v-for="(lbl, i) in stepLabels" :key="i" class="step-item"
          :class="{ active: wizardStep === i + 1, done: wizardStep > i + 1 }">
          <div class="step-dot">
            <svg v-if="wizardStep > i + 1" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <span class="step-label">{{ lbl }}</span>
        </div>
      </div>

      <!-- STEP 1: 上传图片 -->
      <div v-if="phase === 'wizard' && wizardStep === 1" class="wizard-body">
        <div class="step-hero">
          <div class="step-number">第 1 步</div>
          <h1 class="step-title">上传您的图片</h1>
          <p class="step-desc">支持 JPG、PNG、WEBP，最大 20MB。点击或拖拽图片到下方区域。</p>
        </div>
        <div class="drop-zone" :class="{ dragover: dragging, 'has-image': !!selectedFile }"
          @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop" @click="triggerFileInput">
          <template v-if="!selectedFile">
            <div class="dz-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <p class="dz-text">点击上传 或 拖拽图片到这里</p>
            <p class="dz-hint">JPG  PNG  WEBP  最大 20MB</p>
          </template>
          <template v-else>
            <img :src="previewUrl" class="preview-img" alt="预览" />
            <div class="preview-overlay" @click.stop="clearFile">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              更换图片
            </div>
          </template>
        </div>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />
        <div class="step-actions">
          <button class="btn-next" :disabled="!selectedFile" @click="wizardStep = hasOptions ? 2 : 3">
            下一步：{{ hasOptions ? '定制选项' : '填写需求' }}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>

      <!-- STEP 2: 定制选项 -->
      <div v-if="phase === 'wizard' && wizardStep === 2" class="wizard-body">
        <div class="step-hero">
          <div class="step-number">第 2 步</div>
          <h1 class="step-title">定制您的效果</h1>
          <p class="step-desc">根据您的需求选择处理方案，不确定就保持默认即可。</p>
        </div>
        <div class="options-wrapper">
          <div v-for="group in optionGroups" :key="group.id" class="option-group">
            <div class="og-label">{{ group.label }}</div>
            <p v-if="group.description" class="og-desc">{{ group.description }}</p>
            <!-- Toggle -->
            <div v-if="group.type === 'toggle'" class="toggle-row" @click="toggleOption(group.id)">
              <div class="toggle-info">
                <span class="toggle-icon">{{ group.icon || '' }}</span>
                <span class="toggle-text">{{ group.label }}</span>
              </div>
              <div class="toggle-switch" :class="{ on: selectedOptions.has(group.id) }">
                <div class="toggle-thumb" />
              </div>
            </div>
            <!-- Single Choice -->
            <div v-else-if="group.type === 'single_choice'" class="choices-grid">
              <button v-for="choice in group.choices" :key="choice.id" class="choice-card"
                :class="{ selected: selectedChoice(group.id) === choice.id }"
                @click="setChoice(group.id, choice.id)">
                <span class="choice-icon">{{ choice.icon || '' }}</span>
                <span class="choice-label">{{ choice.label }}</span>
                <span v-if="choice.description" class="choice-desc">{{ choice.description }}</span>
                <div v-if="selectedChoice(group.id) === choice.id" class="choice-check">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
              </button>
            </div>
          </div>
        </div>
        <div class="step-actions">
          <button class="btn-back" @click="wizardStep = 1">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>上一步
          </button>
          <button class="btn-next" @click="wizardStep = 3">
            下一步：填写需求
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>

      <!-- STEP 3: 填写需求 -->
      <div v-if="phase === 'wizard' && wizardStep === 3" class="wizard-body">
        <div class="step-hero">
          <div class="step-number">第 3 步</div>
          <h1 class="step-title">告诉我们您的特别需求</h1>
          <p class="step-desc">有什么特殊要求都可以写下来，没有也完全没关系～</p>
        </div>
        <div class="note-section">
          <textarea v-model="userNote" class="note-textarea" maxlength="500"
            placeholder="例如：这是我的奶奶，希望修复面部细节，保持原有气质" />
          <div class="note-count">{{ userNote.length }} / 500</div>
        </div>
        <div class="step-actions">
          <button class="btn-back" @click="wizardStep = hasOptions ? 2 : 1">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>上一步
          </button>
          <button class="btn-next" @click="wizardStep = 4">
            下一步：确认提交
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>

      <!-- STEP 4: 确认提交 -->
      <div v-if="phase === 'wizard' && wizardStep === 4" class="wizard-body">
        <div class="step-hero">
          <div class="step-number">第 4 步</div>
          <h1 class="step-title">确认并提交</h1>
          <p class="step-desc">检查一下信息，然后点击提交开始处理。</p>
        </div>
        <div class="confirm-card">
          <div class="confirm-row">
            <span class="confirm-lbl">图片</span>
            <div class="confirm-val">
              <img :src="previewUrl" class="confirm-thumb" alt="预览" />
              <span>{{ selectedFile?.name }}</span>
            </div>
          </div>
          <template v-if="hasOptions">
            <div v-for="group in optionGroups" :key="group.id" class="confirm-row">
              <span class="confirm-lbl">{{ group.label }}</span>
              <span class="confirm-val confirm-option">{{ summarizeOption(group) }}</span>
            </div>
          </template>
          <div v-if="userNote" class="confirm-row">
            <span class="confirm-lbl">特别要求</span>
            <span class="confirm-val note-preview">{{ userNote }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-lbl">处理方式</span>
            <span class="confirm-val">
              <span v-if="isHuman" class="badge-human">人工处理（{{ tokenInfo!.human_sla_hours }}h 以内）</span>
              <span v-else class="badge-auto">AI 自动处理</span>
            </span>
          </div>
        </div>
        <p v-if="submitError" class="inline-error"> {{ submitError }}</p>
        <div class="step-actions">
          <button class="btn-back" @click="wizardStep = 3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>上一步
          </button>
          <button class="btn-submit" :disabled="submitting" @click="handleSubmit">
            <span v-if="submitting"><span class="btn-spinner" /> 提交中</span>
            <span v-else> 立即提交</span>
          </button>
        </div>
      </div>

      <!-- STEP 5: 等待中 -->
      <div v-if="phase === 'processing' || phase === 'human-pending'" class="wizard-body waiting-body">
        <div class="waiting-art">
          <div class="orbit orbit1"><div class="dot d1"/></div>
          <div class="orbit orbit2"><div class="dot d2"/></div>
          <div class="orbit orbit3"><div class="dot d3"/></div>
          <div class="orbit-center">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
            </svg>
          </div>
        </div>
        <template v-if="phase === 'processing'">
          <h2 class="waiting-title">AI 正在处理您的照片</h2>
          <p class="waiting-desc">请放松等待，处理完成后页面会自动显示结果。</p>
          <div class="status-chip"><span class="status-dot-anim" />{{ jobStatusText }}</div>
        </template>
        <template v-else>
          <h2 class="waiting-title">已提交给专业修复师</h2>
          <p class="waiting-desc">将在 <b>{{ tokenInfo!.human_sla_hours }} 小时</b>内完成，稍后再来查看吧～</p>
          <p class="waiting-sub">提交时间：{{ jobCreatedAt }}</p>
          <button class="btn-check" :disabled="refreshing" @click="checkDelivered">
            <span v-if="refreshing"><span class="btn-spinner dark" /> 检查中</span>
            <span v-else> 刷新查看结果</span>
          </button>
          <p class="waiting-auto">页面每 {{ HUMAN_POLL_SECS }} 秒自动刷新</p>
        </template>
      </div>

      <!-- STEP 6: 结果展示 -->
      <div v-if="phase === 'done'" class="wizard-body done-body">
        <div class="done-badge">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h2 class="done-title">{{ isHuman ? '专业修复完成！' : 'AI 处理完成！' }}</h2>
        <p class="done-desc">照片已处理完毕，可放大查看或点击下载保存。</p>
        <div class="result-gallery">
          <div v-for="asset in assets" :key="asset.id" class="result-item">
            <div class="result-img-wrap" @click="openZoom(asset.download_url)">
              <img v-if="isImage(asset.content_type)" :src="asset.download_url" class="result-img" :alt="asset.filename" />
              <div class="result-zoom-hint">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35M11 8v6M8 11h6"/></svg>
                点击放大
              </div>
            </div>
            <div class="result-actions">
              <a :href="asset.download_url" :download="asset.filename" class="btn-download">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                下载图片
              </a>
            </div>
          </div>
        </div>
        <div v-if="(tokenInfo?.remaining ?? 0) > 0" class="done-more">
          <button class="btn-again" @click="reset">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.63"/></svg>
            再处理一张（剩余 {{ tokenInfo?.remaining }} 次）
          </button>
        </div>
      </div>

      <!-- 失败 -->
      <div v-if="phase === 'failed'" class="wizard-body failed-body">
        <div class="failed-icon"></div>
        <h2>处理失败</h2>
        <p>{{ jobError || '发生了未知错误，请联系服务商。' }}</p>
        <button class="btn-again" @click="reset">重新尝试</button>
      </div>
    </template>

    <!-- 图片放大 Modal -->
    <div v-if="zoomUrl" class="zoom-modal" @click.self="zoomUrl = null">
      <div class="zoom-inner">
        <button class="zoom-close" @click="zoomUrl = null">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
        <img :src="zoomUrl" class="zoom-image" alt="放大预览" />
        <a :href="zoomUrl" download class="zoom-download">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          下载图片
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  getTokenInfo, uploadFile, submitJob, getJobStatus,
  type TokenInfo, type AssetOut, type ProjectInfo, type ProjectOptionGroup,
} from '@/api/client'

const route = useRoute()
const tokenValue = route.params.token as string
const HUMAN_POLL_SECS = 15

type Phase = 'loading' | 'error' | 'wizard' | 'processing' | 'human-pending' | 'done' | 'failed'

const phase = ref<Phase>('loading')
const wizardStep = ref(1)
const errorMsg = ref('')
const tokenInfo = ref<TokenInfo | null>(null)
const projectInfo = ref<ProjectInfo | null>(null)
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const dragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedOptions = ref(new Set<string>())
const singleChoiceMap = ref(new Map<string, string>())
const userNote = ref('')
const submitting = ref(false)
const submitError = ref('')
const jobStatus = ref('')
const jobError = ref('')
const assets = ref<AssetOut[]>([])
const jobCreatedAt = ref('')
const refreshing = ref(false)
const currentJobId = ref<string | null>(null)
const zoomUrl = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const isHuman = computed(() => tokenInfo.value?.delivery_mode === 'human')
const optionGroups = computed<ProjectOptionGroup[]>(() => projectInfo.value?.options?.option_groups ?? [])
const hasOptions = computed(() => optionGroups.value.length > 0)
const stepLabels = computed(() => {
  const base = ['上传图片']
  if (hasOptions.value) base.push('定制选项')
  base.push('填写需求', '确认提交')
  return base
})
const jobStatusText = computed(() => ({ queued: '排队等待中', running: 'AI 处理中' }[jobStatus.value] ?? '处理中'))

onMounted(async () => {
  try {
    const info = await getTokenInfo(tokenValue)
    tokenInfo.value = info
    projectInfo.value = info.project ?? null
    for (const g of (info.project?.options?.option_groups ?? [])) {
      if (g.type === 'single_choice' && g.default) {
        singleChoiceMap.value.set(g.id, String(g.default))
      }
    }
    determineInitialPhase()
  } catch {
    phase.value = 'error'
    errorMsg.value = 'Token 无效或已过期，请联系服务商'
  }
})
onUnmounted(() => stopPoll())

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
    if (job.status === 'succeeded') { assets.value = job.assets; phase.value = 'done'; return }
    if (job.status === 'failed' || job.status === 'canceled') { jobError.value = '处理失败，请联系服务商'; phase.value = 'failed'; return }
    if (isHuman.value) { jobCreatedAt.value = fmtDate(job.created_at); phase.value = 'human-pending'; startHumanPoll(job.id) }
    else { jobStatus.value = job.status; phase.value = 'processing'; startAutoPoll(job.id) }
    return
  }
  if (info.remaining <= 0) { phase.value = 'error'; errorMsg.value = 'Token 可用次数已用完'; return }
  phase.value = 'wizard'; wizardStep.value = 1
}

function triggerFileInput() { fileInput.value?.click() }
function onFileChange(e: Event) { const f = (e.target as HTMLInputElement).files?.[0]; if (f) setFile(f) }
function onDrop(e: DragEvent) { dragging.value = false; const f = e.dataTransfer?.files?.[0]; if (f?.type.startsWith('image/')) setFile(f) }
function setFile(f: File) { if (previewUrl.value) URL.revokeObjectURL(previewUrl.value); selectedFile.value = f; previewUrl.value = URL.createObjectURL(f) }
function clearFile() { selectedFile.value = null; if (previewUrl.value) { URL.revokeObjectURL(previewUrl.value); previewUrl.value = '' } }

function toggleOption(id: string) { if (selectedOptions.value.has(id)) selectedOptions.value.delete(id); else selectedOptions.value.add(id); selectedOptions.value = new Set(selectedOptions.value) }
function setChoice(gid: string, cid: string) { singleChoiceMap.value.set(gid, cid); singleChoiceMap.value = new Map(singleChoiceMap.value) }
function selectedChoice(gid: string) { return singleChoiceMap.value.get(gid) }
function summarizeOption(group: ProjectOptionGroup): string {
  if (group.type === 'toggle') return selectedOptions.value.has(group.id) ? ' 已开启' : '未开启'
  const cid = singleChoiceMap.value.get(group.id)
  return group.choices?.find(c => c.id === cid)?.label ?? '默认'
}
function collectSelectedIds(): string[] {
  const ids: string[] = []
  for (const gid of selectedOptions.value) ids.push(gid)
  for (const cid of singleChoiceMap.value.values()) ids.push(cid)
  return ids
}

async function handleSubmit() {
  if (!selectedFile.value) return
  submitting.value = true; submitError.value = ''
  try {
    const { object_key } = await uploadFile(tokenValue, selectedFile.value)
    const job = await submitJob(tokenValue, object_key, { selectedOptions: collectSelectedIds(), userNote: userNote.value })
    currentJobId.value = job.id
    if (isHuman.value) { jobCreatedAt.value = fmtDate(job.created_at); phase.value = 'human-pending'; startHumanPoll(job.id) }
    else { jobStatus.value = job.status; phase.value = 'processing'; startAutoPoll(job.id) }
  } catch (e: unknown) { submitError.value = e instanceof Error ? e.message : '提交失败，请稍后重试' }
  finally { submitting.value = false }
}

function startAutoPoll(jobId: string) {
  pollTimer = setInterval(async () => {
    try {
      const job = await getJobStatus(jobId)
      jobStatus.value = job.status
      if (job.status === 'succeeded') { stopPoll(); assets.value = job.assets; phase.value = 'done'; tokenInfo.value = await getTokenInfo(tokenValue).catch(() => tokenInfo.value!) }
      else if (job.status === 'failed' || job.status === 'canceled') { stopPoll(); jobError.value = job.error ?? '处理失败'; phase.value = 'failed' }
    } catch { /* ignore */ }
  }, 2000)
}
function startHumanPoll(jobId: string) { pollTimer = setInterval(() => silentCheck(jobId), HUMAN_POLL_SECS * 1000) }
async function silentCheck(jobId: string) {
  try {
    const job = await getJobStatus(jobId)
    if (job.status === 'succeeded') { stopPoll(); assets.value = job.assets; phase.value = 'done'; tokenInfo.value = await getTokenInfo(tokenValue).catch(() => tokenInfo.value!) }
    else if (job.status === 'failed' || job.status === 'canceled') { stopPoll(); jobError.value = '处理失败'; phase.value = 'failed' }
  } catch { /* ignore */ }
}
async function checkDelivered() { if (!currentJobId.value) return; refreshing.value = true; await silentCheck(currentJobId.value); refreshing.value = false }
function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

function reset() {
  stopPoll(); clearFile()
  selectedOptions.value = new Set()
  for (const g of optionGroups.value) { if (g.type === 'single_choice' && g.default) singleChoiceMap.value.set(g.id, String(g.default)) }
  userNote.value = ''; assets.value = []; currentJobId.value = null; submitError.value = ''; wizardStep.value = 1; phase.value = 'wizard'
}
function openZoom(url: string) { zoomUrl.value = url }
function isImage(ct: string | null) { return !ct || ct.startsWith('image/') }
function fmtDate(s: string) { return new Date(s).toLocaleString('zh-CN') }
</script>

<style scoped>
.wizard-page {
  --bg: #F5F3FF; --card: #FFFFFF; --accent: #8B5CF6; --accent2: #EC4899;
  --text: #1a1a2e; --text-soft: #6B7280; --border: #E5E7EB;
  --radius: 16px; --shadow: 0 4px 24px rgba(139,92,246,0.12);
  min-height: 100vh; background: var(--bg); color: var(--text);
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  display: flex; flex-direction: column; align-items: center; padding-bottom: 60px;
}
.full-center {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 16px; padding: 24px; text-align: center;
}
.loader-ring {
  width: 56px; height: 56px; border: 4px solid rgba(139,92,246,0.2);
  border-top-color: var(--accent); border-radius: 50%; animation: spin 0.9s linear infinite;
}
.loader-hint { color: var(--text-soft); font-size: 0.95rem; }
.error-state { gap: 12px; }
.error-icon { font-size: 3rem; }
.error-state h2 { font-size: 1.4rem; }
.error-state p { color: var(--text-soft); max-width: 320px; }
.btn-home {
  margin-top: 8px; padding: 12px 28px; border-radius: 12px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; font-weight: 600; border: none; cursor: pointer; font-size: 1rem;
}
.wizard-header {
  width: 100%; max-width: 640px; display: flex; align-items: center; gap: 12px; padding: 20px 20px 0;
}
.wh-logo {
  display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 1rem;
  cursor: pointer; flex-shrink: 0; color: var(--text);
}
.wh-title { flex: 1; font-size: 1rem; font-weight: 600; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wh-meta { font-size: 0.8rem; color: var(--text-soft); flex-shrink: 0; }
.wh-meta b { color: var(--accent); }
.steps-bar {
  display: flex; gap: 4px; padding: 16px 20px 0; width: 100%; max-width: 640px;
  overflow-x: auto; scrollbar-width: none;
}
.steps-bar::-webkit-scrollbar { display: none; }
.step-item { display: flex; align-items: center; gap: 6px; flex-shrink: 0; color: var(--text-soft); font-size: 0.78rem; }
.step-item::after { content: ''; display: block; width: 16px; height: 2px; background: var(--border); margin-left: 4px; }
.step-item:last-child::after { display: none; }
.step-item.active { color: var(--accent); }
.step-item.done { color: #10B981; }
.step-dot {
  width: 22px; height: 22px; border-radius: 50%; border: 2px solid currentColor;
  display: flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 700; flex-shrink: 0;
}
.step-item.active .step-dot { background: var(--accent); color: white; border-color: var(--accent); }
.step-item.done .step-dot { background: #10B981; color: white; border-color: #10B981; }
.step-label { display: none; }
@media(min-width:460px){ .step-label { display: inline; } }
.wizard-body { width: 100%; max-width: 640px; padding: 20px; display: flex; flex-direction: column; gap: 20px; }
.step-hero { text-align: center; }
.step-number { display: inline-block; color: var(--accent); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.step-title { font-size: clamp(1.3rem,5vw,1.8rem); font-weight: 700; margin-bottom: 8px; line-height: 1.2; }
.step-desc { color: var(--text-soft); font-size: 0.92rem; line-height: 1.6; }
.drop-zone {
  border: 2px dashed var(--border); border-radius: var(--radius); background: white;
  min-height: 200px; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; cursor: pointer; transition: border-color 0.2s, box-shadow 0.2s; position: relative; overflow: hidden;
}
.drop-zone:hover,.drop-zone.dragover { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(139,92,246,0.1); }
.drop-zone.has-image { border-style: solid; padding: 0; }
.dz-icon { color: var(--accent); opacity: 0.6; }
.dz-text { font-size: 1rem; font-weight: 600; }
.dz-hint { font-size: 0.8rem; color: var(--text-soft); }
.preview-img { width: 100%; max-height: 260px; object-fit: contain; background: #f9f5ff; }
.preview-overlay {
  position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.55); color: white;
  border-radius: 8px; padding: 6px 12px; display: flex; align-items: center; gap: 6px;
  font-size: 0.8rem; cursor: pointer; backdrop-filter: blur(4px);
}
.options-wrapper { display: flex; flex-direction: column; gap: 16px; }
.option-group { background: white; border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); }
.og-label { font-size: 1rem; font-weight: 700; margin-bottom: 4px; }
.og-desc { font-size: 0.82rem; color: var(--text-soft); margin-bottom: 10px; }
.toggle-row { display: flex; align-items: center; justify-content: space-between; cursor: pointer; gap: 12px; padding: 4px 0; }
.toggle-info { display: flex; align-items: center; gap: 10px; }
.toggle-icon { font-size: 1.4rem; }
.toggle-text { font-size: 0.95rem; font-weight: 500; }
.toggle-switch { width: 46px; height: 26px; border-radius: 13px; background: var(--border); position: relative; flex-shrink: 0; transition: background 0.25s; }
.toggle-switch.on { background: var(--accent); }
.toggle-thumb { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; background: white; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,0.2); transition: transform 0.25s; }
.toggle-switch.on .toggle-thumb { transform: translateX(20px); }
.choices-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(120px,1fr)); gap: 8px; margin-top: 4px; }
.choice-card {
  position: relative; border: 2px solid var(--border); border-radius: 12px; padding: 12px 10px;
  text-align: center; cursor: pointer; background: white; transition: border-color 0.2s,transform 0.15s;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.choice-card:hover { border-color: var(--accent); transform: translateY(-1px); }
.choice-card.selected { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(139,92,246,0.15); }
.choice-icon { font-size: 1.5rem; }
.choice-label { font-size: 0.82rem; font-weight: 600; }
.choice-desc { font-size: 0.7rem; color: var(--text-soft); line-height: 1.3; }
.choice-check { position: absolute; top: 5px; right: 5px; width: 16px; height: 16px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; }
.note-section { position: relative; }
.note-textarea {
  width: 100%; min-height: 130px; padding: 14px; border-radius: 12px;
  border: 2px solid var(--border); background: white; font-size: 0.93rem; line-height: 1.7;
  font-family: inherit; resize: vertical; transition: border-color 0.2s; box-sizing: border-box;
}
.note-textarea:focus { outline: none; border-color: var(--accent); }
.note-count { text-align: right; font-size: 0.75rem; color: var(--text-soft); margin-top: 4px; }
.confirm-card { background: white; border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 14px; }
.confirm-row { display: flex; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.confirm-row:last-child { border-bottom: none; padding-bottom: 0; }
.confirm-lbl { font-size: 0.8rem; font-weight: 600; color: var(--text-soft); width: 68px; flex-shrink: 0; padding-top: 2px; }
.confirm-val { font-size: 0.9rem; font-weight: 500; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--text); }
.confirm-thumb { width: 40px; height: 40px; border-radius: 8px; object-fit: cover; flex-shrink: 0; }
.confirm-option { color: var(--accent); }
.note-preview { font-style: italic; color: var(--text-soft); }
.badge-human { background: #FEF3C7; color: #92400E; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
.badge-auto { background: #EDE9FE; color: var(--accent); padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
.inline-error { background: #FEE2E2; color: #991B1B; border-radius: 10px; padding: 10px 14px; font-size: 0.86rem; }
.step-actions { display: flex; gap: 10px; padding-top: 4px; }
.btn-back {
  display: flex; align-items: center; gap: 6px; padding: 13px 16px;
  border-radius: 12px; border: 2px solid var(--border); background: white;
  color: var(--text-soft); font-size: 0.9rem; font-weight: 600; cursor: pointer; flex-shrink: 0; transition: border-color 0.2s;
}
.btn-back:hover { border-color: var(--accent); color: var(--accent); }
.btn-next {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 16px;
  border-radius: 12px; background: linear-gradient(135deg,var(--accent),var(--accent2));
  color: white; font-size: 0.97rem; font-weight: 700; border: none; cursor: pointer; transition: opacity 0.2s,transform 0.15s;
}
.btn-next:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-next:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.btn-submit {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 15px 16px;
  border-radius: 12px; background: linear-gradient(135deg,#EC4899,#8B5CF6);
  color: white; font-size: 1rem; font-weight: 700; border: none; cursor: pointer; transition: opacity 0.2s,transform 0.15s;
}
.btn-submit:hover:not(:disabled) { opacity: 0.9; transform: translateY(-2px); }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.waiting-body { align-items: center; text-align: center; padding-top: 40px; }
.waiting-art { position: relative; width: 130px; height: 130px; margin-bottom: 20px; }
.orbit { position: absolute; inset: 0; border-radius: 50%; border: 2px solid transparent; }
.orbit1 { border-color: rgba(139,92,246,0.2); animation: spin 3s linear infinite; }
.orbit2 { inset: 14px; border-color: rgba(236,72,153,0.25); animation: spin 2s linear infinite reverse; }
.orbit3 { inset: 28px; border-color: rgba(249,115,22,0.2); animation: spin 4s linear infinite; }
.dot { position: absolute; width: 9px; height: 9px; border-radius: 50%; top: -4px; left: calc(50% - 4px); }
.d1 { background: var(--accent); }
.d2 { background: var(--accent2); }
.d3 { background: #F97316; }
.orbit-center {
  position: absolute; inset: 42px;
  background: linear-gradient(135deg,var(--accent),var(--accent2));
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.waiting-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 8px; }
.waiting-desc { color: var(--text-soft); line-height: 1.7; max-width: 300px; }
.waiting-sub { font-size: 0.8rem; color: var(--text-soft); }
.status-chip { display: inline-flex; align-items: center; gap: 8px; background: white; border-radius: 20px; padding: 8px 16px; font-size: 0.86rem; font-weight: 600; box-shadow: var(--shadow); color: var(--accent); margin-top: 6px; }
.status-dot-anim { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
.btn-check {
  display: flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 26px;
  border-radius: 12px; background: white; border: 2px solid var(--accent); color: var(--accent);
  font-size: 0.93rem; font-weight: 700; cursor: pointer; margin-top: 10px; transition: background 0.2s;
}
.btn-check:hover:not(:disabled) { background: #F5F3FF; }
.btn-check:disabled { opacity: 0.5; cursor: not-allowed; }
.waiting-auto { font-size: 0.75rem; color: var(--text-soft); margin-top: 6px; }
.done-body { align-items: center; text-align: center; }
.done-badge { width: 60px; height: 60px; background: linear-gradient(135deg,#10B981,#059669); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.done-title { font-size: 1.5rem; font-weight: 700; }
.done-desc { color: var(--text-soft); margin-bottom: 4px; }
.result-gallery { width: 100%; display: flex; flex-direction: column; gap: 14px; }
.result-item { background: white; border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); }
.result-img-wrap { position: relative; cursor: zoom-in; background: #f9f5ff; }
.result-img { width: 100%; max-height: 440px; object-fit: contain; display: block; }
.result-zoom-hint {
  position: absolute; inset: 0; background: rgba(0,0,0,0); display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px; color: white; font-size: 0.85rem;
  font-weight: 600; opacity: 0; transition: all 0.2s;
}
.result-img-wrap:hover .result-zoom-hint { background: rgba(0,0,0,0.4); opacity: 1; }
.result-actions { padding: 12px 14px; }
.btn-download {
  display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 10px;
  background: linear-gradient(135deg,var(--accent),var(--accent2)); color: white;
  font-weight: 600; font-size: 0.88rem; text-decoration: none; transition: opacity 0.2s,transform 0.15s;
}
.btn-download:hover { opacity: 0.9; transform: translateY(-1px); }
.done-more { width: 100%; }
.btn-again {
  width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 13px;
  border-radius: 12px; border: 2px solid var(--border); background: white; color: var(--text-soft);
  font-size: 0.93rem; font-weight: 600; cursor: pointer; transition: border-color 0.2s,color 0.2s;
}
.btn-again:hover { border-color: var(--accent); color: var(--accent); }
.failed-body { align-items: center; text-align: center; gap: 12px; padding-top: 60px; }
.failed-icon { font-size: 3rem; }
.failed-body h2 { font-size: 1.4rem; font-weight: 700; }
.failed-body p { color: var(--text-soft); }
.zoom-modal { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,0.9); display: flex; align-items: center; justify-content: center; padding: 16px; }
.zoom-inner { position: relative; max-width: 90vw; max-height: 90vh; display: flex; flex-direction: column; gap: 10px; }
.zoom-close { position: absolute; top: -10px; right: -10px; width: 32px; height: 32px; background: white; border-radius: 50%; border: none; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #374151; box-shadow: 0 2px 8px rgba(0,0,0,0.3); z-index: 1; }
.zoom-image { max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 8px; display: block; }
.zoom-download { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 18px; border-radius: 10px; background: white; color: var(--text); text-decoration: none; font-weight: 600; font-size: 0.88rem; align-self: center; }
.btn-spinner { display: inline-block; width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.4); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; }
.btn-spinner.dark { border-color: rgba(0,0,0,0.2); border-top-color: var(--accent); }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.4;transform:scale(0.7)} }
</style>