<template>
  <div class="home">
    <div class="hero">
      <div class="logo">✦</div>
      <h1>小神AI</h1>
      <p class="subtitle">AI 驱动的业务处理服务，所见即所得</p>
    </div>

    <div class="card-row">
      <div class="info-card">
        <div class="icon">🔗</div>
        <h3>如何使用？</h3>
        <p>通过您的专属服务链接访问，链接格式为：</p>
        <code>{{ baseUrl }}/s/&lt;您的Token&gt;</code>
      </div>
      <div class="info-card">
        <div class="icon">🖼️</div>
        <h3>上传图片</h3>
        <p>拖拽或点击上传您的图片，平台将自动处理并返回结果。</p>
      </div>
      <div class="info-card">
        <div class="icon">⬇️</div>
        <h3>下载结果</h3>
        <p>处理完成后可直接预览并下载高质量处理结果。</p>
      </div>
    </div>

    <div class="token-area">
      <p class="hint">已有服务链接？粘贴 Token 快速跳转：</p>
      <div class="input-row">
        <input v-model="tokenInput" placeholder="粘贴您的 Token…" @keyup.enter="go" />
        <button :disabled="!tokenInput.trim()" @click="go">前往 →</button>
      </div>
    </div>

    <footer class="footer">由 Skill Platform 提供支持</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const tokenInput = ref('')
const baseUrl = window.location.origin

function go() {
  const t = tokenInput.value.trim()
  if (t) router.push(`/s/${t}`)
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 60%, #16213e 100%);
  color: #e2e8f0;
  font-family: 'Segoe UI', system-ui, sans-serif;
  padding: 0 1rem;
}

.hero {
  text-align: center;
  padding: 6rem 0 3rem;
}

.logo {
  font-size: 3rem;
  color: #4f6aff;
  margin-bottom: 1rem;
}

h1 {
  font-size: 2.8rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  background: linear-gradient(90deg, #4f6aff, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  font-size: 1.15rem;
  color: #94a3b8;
  margin: 0;
}

.card-row {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 900px;
  width: 100%;
  margin-bottom: 3rem;
}

.info-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2rem 1.5rem;
  max-width: 260px;
  flex: 1;
  min-width: 200px;
  text-align: center;
  transition: border-color 0.2s;
}

.info-card:hover {
  border-color: #4f6aff66;
}

.icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.info-card h3 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.info-card p {
  font-size: 0.88rem;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0 0 0.75rem;
}

.info-card code {
  font-size: 0.78rem;
  background: rgba(79, 106, 255, 0.15);
  color: #818cf8;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  word-break: break-all;
}

.token-area {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2rem 2.5rem;
  max-width: 520px;
  width: 100%;
  margin-bottom: 4rem;
  text-align: center;
}

.hint {
  color: #94a3b8;
  margin: 0 0 1rem;
  font-size: 0.9rem;
}

.input-row {
  display: flex;
  gap: 0.75rem;
}

.input-row input {
  flex: 1;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 0.6rem 1rem;
  color: #e2e8f0;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}

.input-row input:focus {
  border-color: #4f6aff;
}

.input-row button {
  background: #4f6aff;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1.25rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.input-row button:hover:not(:disabled) {
  background: #3b4fd9;
}

.input-row button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.footer {
  margin-top: auto;
  padding: 1.5rem;
  color: #475569;
  font-size: 0.8rem;
}
</style>
