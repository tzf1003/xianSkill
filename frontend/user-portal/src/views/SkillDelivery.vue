<template>
  <div class="delivery-page">
    <!-- 鍔犺浇涓?-->
    <div v-if="phase === 'loading'" class="state-center">
      <p class="hint">姝ｅ湪鍔犺浇 Token 淇℃伅鈥︹€?/p>
    </div>

    <!-- Token 鏃犳晥 -->
    <div v-else-if="phase === 'error'" class="state-center error">
      <h2>{{ errorMsg }}</h2>
      <p>璇风‘璁ら摼鎺ユ湁鏁堬紝鎴栬仈绯绘湇鍔″晢銆?/p>
    </div>

    <!-- 涓荤晫闈?-->
    <template v-else>
      <!-- 淇℃伅鍗?-->
      <div class="info-card">
        <div class="skill-name">{{ tokenInfo!.skill.name }}</div>
        <div class="skill-desc">{{ tokenInfo!.skill.description }}</div>
        <div class="meta-row">
          <span>濂楅锛歿{ tokenInfo!.sku_name }}</span>
          <span v-if="isHuman" class="badge-human">馃 浜哄伐澶勭悊</span>
          <span>鍓╀綑娆℃暟锛?b>{{ tokenInfo!.remaining }}</b> / {{ tokenInfo!.total_uses }}</span>
          <span v-if="tokenInfo!.expires_at">杩囨湡锛歿{ fmtDate(tokenInfo!.expires_at) }}</span>
        </div>
        <div v-if="isHuman && tokenInfo!.human_sla_hours" class="sla-hint">
          棰勮澶勭悊鏃堕棿锛歿{ tokenInfo!.human_sla_hours }} 灏忔椂浠ュ唴
        </div>
      </div>

      <!-- 涓婁紶鍖猴紙auto 妯″紡 鎴?human 妯″紡棣栨鎻愪氦锛?-->
      <div v-if="phase === 'idle'" class="upload-section">
        <p v-if="isHuman" class="human-tip">
          馃搵 璇蜂笂浼犳偍鐨勯渶姹傛潗鏂欙紝鎻愪氦鍚庣敱涓撲笟浜哄憳澶勭悊骞朵氦浠樼粨鏋溿€?
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
            <span class="icon">馃摲</span>
            <p>鐐瑰嚮鎴栨嫋鎷藉浘鐗囧埌姝ゅ</p>
            <p class="hint-small">鏀寔 JPG / PNG / WEBP锛屾渶澶?20MB</p>
          </template>
          <template v-else>
            <img :src="previewUrl" class="preview-img" alt="preview" />
            <p class="file-name">{{ selectedFile.name }}</p>
          </template>
        </div>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />

        <button class="btn-primary" :disabled="!selectedFile || submitting" @click="handleSubmit">
          {{ submitting ? '鎻愪氦涓€︹€? : (isHuman ? '鎻愪氦闇€姹? : '寮€濮嬪鐞?) }}
        </button>
        <p v-if="submitError" class="error-text">{{ submitError }}</p>
      </div>

      <!-- 鑷姩澶勭悊涓?-->
      <div v-else-if="phase === 'processing'" class="state-center">
        <div class="spinner" />
        <p>姝ｅ湪鑷姩澶勭悊锛岃绋嶅€欌€︹€?/p>
        <p class="hint-small">鐘舵€侊細{{ jobStatus }}</p>
      </div>

      <!-- 浜哄伐澶勭悊绛夊緟涓?-->
      <div v-else-if="phase === 'human-pending'" class="state-center human-pending">
        <div class="human-icon">馃晲</div>
        <h3>绛夊緟浜哄伐澶勭悊涓?/h3>
        <p>鎮ㄧ殑闇€姹傚凡鏀跺埌锛屼笓涓氫汉鍛樺皢鍦?SLA 鏃堕檺鍐呭畬鎴愬鐞嗗苟浜や粯缁撴灉銆?/p>
        <p v-if="tokenInfo!.human_sla_hours" class="hint-small">
          鎵胯澶勭悊鏃堕棿锛?b>{{ tokenInfo!.human_sla_hours }} 灏忔椂浠ュ唴</b>
        </p>
        <p class="hint-small">鎻愪氦鏃堕棿锛歿{ jobCreatedAt }}</p>
        <button class="btn-secondary" :disabled="refreshing" @click="checkDelivered">
          {{ refreshing ? '妫€鏌ヤ腑鈥︹€? : '馃攧 鍒锋柊鏌ョ湅缁撴灉' }}
        </button>
        <p class="hint-small mt-8">椤甸潰姣?{{ HUMAN_POLL_SECS }} 绉掕嚜鍔ㄥ埛鏂颁竴娆?/p>
      </div>

      <!-- 鎴愬姛锛坅uto 鎴?human 浜や粯瀹屾垚锛?-->
      <div v-else-if="phase === 'done'" class="done-section">
        <div class="done-header">{{ isHuman ? '鉁?浜哄伐浜や粯瀹屾垚' : '鉁?澶勭悊瀹屾垚' }}</div>
        <div v-if="assets.length > 0" class="asset-list">
          <div v-for="asset in assets" :key="asset.id" class="asset-item">
            <img v-if="isImage(asset.content_type)" :src="asset.download_url" class="result-img" alt="result" />
            <div class="asset-meta">
              <span>{{ asset.filename }}</span>
              <a :href="asset.download_url" target="_blank" class="btn-download">涓嬭浇</a>
            </div>
          </div>
        </div>
        <button v-if="tokenInfo!.remaining > 0" class="btn-secondary" @click="reset">
          鍐峽{ isHuman ? '鎻愪氦涓€娆? : '澶勭悊涓€寮? }}
        </button>
      </div>

      <!-- 澶辫触 -->
      <div v-else-if="phase === 'failed'" class="state-center error">
        <h3>澶勭悊澶辫触</h3>
        <p>{{ jobError }}</p>
        <button class="btn-secondary" @click="reset">閲嶈瘯</button>
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
    errorMsg.value = 'Token 鏃犳晥鎴栧凡杩囨湡'
  }
})

onUnmounted(() => { stopPoll() })

/**
 * 鏍规嵁 token 淇℃伅锛堝惈 latest_job锛夊喅瀹氬垵濮嬮〉闈㈢姸鎬併€?
 * 杩欐牱鍒锋柊椤甸潰鍚庤兘鎭㈠鍒版纭樁娈碉紝鑰屼笉鏄€诲洖鍒?idle銆?
 */
function determineInitialPhase() {
  const info = tokenInfo.value!
  const job = info.latest_job

  if (info.status !== 'active') {
    phase.value = 'error'
    errorMsg.value = info.status === 'revoked' ? 'Token 宸叉挙閿€' : 'Token 宸茶繃鏈?
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
      jobError.value = '澶勭悊澶辫触锛岃鑱旂郴鏈嶅姟鍟?
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
    errorMsg.value = 'Token 宸叉棤鍙敤娆℃暟'
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
    submitError.value = e instanceof Error ? e.message : '鎻愪氦澶辫触'
  } finally {
    submitting.value = false
  }
}

/** Auto 妯″紡锛氭瘡 2 绉掕疆璇?Job 鐘舵€?*/
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
        jobError.value = job.error ?? '鏈煡閿欒'
        phase.value = 'failed'
      }
    } catch { /* 鐭殏缃戠粶鎶栧姩锛岀户缁疆璇?*/ }
  }, 2000)
}

/** Human 妯″紡锛氭瘡 HUMAN_POLL_SECS 绉掕疆璇紝绛夊緟浜哄伐浜や粯 */
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
      jobError.value = '澶勭悊澶辫触锛岃鑱旂郴鏈嶅姟鍟?
      phase.value = 'failed'
    }
  } catch { /* ignore */ }
}

/** 鎵嬪姩"鍒锋柊鏌ョ湅缁撴灉"鎸夐挳 */
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
.meta-row { display: flex; gap: 16px; flex-wrap: wrap; font-size: 0.88rem; color: #555; align-items: center; }
.badge-human {
  background: #fff3cd;
  color: #856404;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.82rem;
  font-weight: 600;
}
.sla-hint {
  margin-top: 8px;
  font-size: 0.85rem;
  color: #5a6;
}
.human-tip {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.9rem;
  color: #614700;
  margin: 0;
}
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
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
/* Human pending */
.human-pending { padding: 40px 20px; }
.human-icon { font-size: 3.5rem; margin-bottom: 12px; }
.human-pending h3 { font-size: 1.3rem; margin: 0 0 8px; color: #333; }
.human-pending p { margin: 4px 0; }
.mt-8 { margin-top: 8px; }
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
