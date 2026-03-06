<template>
  <div class="delivery-page">
    <!-- 加载中 -->
    <div v-if="phase === 'loading'" class="state-center">
      <p class="hint">正在加载 Token 信息……</p>
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
          <span>剩余次数：<b>{{ tokenInfo!.remaining }}</b> / {{ tokenInfo!.total_uses }}</span>
          <span v-if="tokenInfo!.expires_at">过期：{{ fmtDate(tokenInfo!.expires_at) }}</span>
        </div>
      </div>

      <!-- 上传区 -->
      <div v-if="phase === 'idle'" class="upload-section">
        <div
          class="drop-zone"
          :class="{ dragover: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
          @click="fileInput?.click()"
        >
          <template v-if="!selectedFile">
            <span class="icon">📷</span>
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
          {{ submitting ? '提交中……' : '开始处理' }}
        </button>
        <p v-if="submitError" class="error-text">{{ submitError }}</p>
      </div>

      <!-- 处理中 -->
      <div v-else-if="phase === 'processing'" class="state-center">
        <div class="spinner" />
        <p>正在处理，请稍候……</p>
        <p class="hint-small">状态：{{ jobStatus }}</p>
      </div>

      <!-- 成功 -->
      <div v-else-if="phase === 'done'" class="done-section">
        <div class="done-header">✅ 处理完成</div>
        <div v-if="assets.length > 0" class="asset-list">
          <div v-for="asset in assets" :key="asset.id" class="asset-item">
            <img v-if="isImage(asset.content_type)" :src="asset.download_url" class="result-img" alt="result" />
            <div class="asset-meta">
              <span>{{ asset.filename }}</span>
              <a :href="asset.download_url" target="_blank" class="btn-download">下载</a>
            </div>
          </div>
        </div>
        <button class="btn-secondary" @click="reset">再处理一张</button>
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
import { ref, onMounted, onUnmounted } from 'vue'
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

type Phase = 'loading' | 'error' | 'idle' | 'processing' | 'done' | 'failed'

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
const fileInput = ref<HTMLInputElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    tokenInfo.value = await getTokenInfo(tokenValue)
    if (tokenInfo.value.remaining <= 0) {
      phase.value = 'error'
      errorMsg.value = 'Token 已无可用次数'
    } else {
      phase.value = 'idle'
    }
  } catch {
    phase.value = 'error'
    errorMsg.value = 'Token 无效或已过期'
  }
})

onUnmounted(() => { stopPoll() })

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
    // 1. 上传图像
    const { object_key } = await uploadFile(tokenValue, selectedFile.value)
    // 2. 提交 Job
    const job = await submitJob(tokenValue, object_key)
    phase.value = 'processing'
    jobStatus.value = job.status
    // 3. 开始轮询
    startPoll(job.id)
  } catch (e: unknown) {
    submitError.value = e instanceof Error ? e.message : '提交失败'
  } finally {
    submitting.value = false
  }
}

function startPoll(jobId: string) {
  pollTimer = setInterval(async () => {
    try {
      const job = await getJobStatus(jobId)
      jobStatus.value = job.status
      if (job.status === 'succeeded') {
        stopPoll()
        assets.value = job.assets
        phase.value = 'done'
        // 刷新 token 信息（次数变化）
        tokenInfo.value = await getTokenInfo(tokenValue).catch(() => tokenInfo.value!)
      } else if (job.status === 'failed' || job.status === 'canceled') {
        stopPoll()
        jobError.value = job.error ?? '未知错误'
        phase.value = 'failed'
      }
    } catch { /* 短暂网络抖动，继续轮询 */ }
  }, 2000)
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

function reset() {
  selectedFile.value = null
  previewUrl.value = ''
  submitError.value = ''
  assets.value = []
  jobStatus.value = ''
  jobError.value = ''
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
.delivery-page {
  max-width: 680px;
  margin: 40px auto;
  padding: 0 16px;
  font-family: sans-serif;
}
.state-center {
  text-align: center;
  padding: 60px 0;
  color: #555;
}
.info-card {
  background: #f8f9ff;
  border: 1px solid #dde;
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 24px;
}
.skill-name { font-size: 1.4rem; font-weight: 700; margin-bottom: 6px; }
.skill-desc { color: #666; margin-bottom: 12px; }
.meta-row { display: flex; gap: 16px; flex-wrap: wrap; font-size: 0.88rem; color: #555; }
.upload-section { display: flex; flex-direction: column; gap: 16px; }
.drop-zone {
  border: 2px dashed #aab;
  border-radius: 10px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
  padding: 16px;
  gap: 8px;
}
.drop-zone.dragover { background: #eef0ff; border-color: #667; }
.drop-zone .icon { font-size: 3rem; }
.preview-img { max-height: 180px; border-radius: 6px; object-fit: contain; }
.file-name { font-size: 0.85rem; color: #555; }
.hint, .hint-small { color: #999; font-size: 0.85rem; margin: 0; }
.btn-primary {
  background: #4f6aff;
  color: #fff;
  border: none;
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
}
.btn-primary:disabled { background: #aab; cursor: not-allowed; }
.btn-secondary {
  background: #e8eaff;
  color: #4f6aff;
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
  margin-top: 16px;
}
.error { color: #c00; }
.error-text { color: #c00; font-size: 0.87rem; }
.spinner {
  width: 48px; height: 48px;
  border: 5px solid #dde;
  border-top-color: #4f6aff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.done-section { display: flex; flex-direction: column; gap: 16px; }
.done-header { font-size: 1.3rem; font-weight: 700; color: #2a7; }
.asset-list { display: flex; flex-direction: column; gap: 12px; }
.asset-item {
  border: 1px solid #dde;
  border-radius: 8px;
  overflow: hidden;
}
.result-img { width: 100%; max-height: 400px; object-fit: contain; background: #f0f0f0; }
.asset-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  font-size: 0.88rem;
}
.btn-download {
  background: #2a7;
  color: #fff;
  padding: 4px 14px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.85rem;
}
</style>
