<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-blob blob1" />
    <div class="bg-blob blob2" />

    <div class="login-card">
      <!-- Logo -->
      <div class="logo-area">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="12" fill="url(#lg)" />
          <path d="M14 20l5 5 8-9" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="lg" x1="0" y1="0" x2="40" y2="40">
              <stop stop-color="#2563EB"/>
              <stop offset="1" stop-color="#7C3AED"/>
            </linearGradient>
          </defs>
        </svg>
        <div>
          <div class="brand-name">小神skills</div>
          <div class="brand-sub">统一管理后台</div>
        </div>
      </div>

      <h1 class="title">欢迎回来</h1>
      <p class="subtitle">登录小神skills，统一管理技能、商品、店铺与交付流程</p>

      <form class="form" @submit.prevent="handleLogin">
        <div class="field">
          <label for="username">账号</label>
          <div class="input-wrap">
            <svg class="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <input
              id="username"
              v-model="username"
              type="text"
              placeholder="admin"
              autocomplete="username"
              required
              :disabled="loading"
            />
          </div>
        </div>

        <div class="field">
          <label for="password">密码</label>
          <div class="input-wrap">
            <svg class="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <input
              id="password"
              v-model="password"
              :type="showPwd ? 'text' : 'password'"
              placeholder="••••••••"
              autocomplete="current-password"
              required
              :disabled="loading"
            />
            <button type="button" class="eye-btn" @click="showPwd = !showPwd" tabindex="-1">
              <svg v-if="!showPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12S5 4 12 4s11 8 11 8-4 8-11 8S1 12 1 12z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="btn-login" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner" />
          <span>{{ loading ? '登录中…' : '登 录' }}</span>
        </button>
      </form>

      <p class="hint-text">账号密码在后端 <code>.env</code> 配置文件中设置</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/client'

const router = useRouter()
const username = ref('')
const password = ref('')
const showPwd = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
    router.push('/dashboard')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #F8FAFC);
  position: relative;
  overflow: hidden;
  font-family: 'Open Sans', system-ui, sans-serif;
}

/* 背景装饰 */
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
}
.blob1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #2563EB 0%, transparent 70%);
  top: -150px; left: -150px;
}
.blob2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #7C3AED 0%, transparent 70%);
  bottom: -100px; right: -100px;
}

/* 卡片 */
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 20px;
  padding: 40px 40px 32px;
  box-shadow: 0 20px 60px rgba(37, 99, 235, 0.12), 0 4px 16px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.08);
}

/* Logo */
.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}
.brand-name {
  font-family: 'Poppins', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #1E293B;
  line-height: 1.2;
}
.brand-sub {
  font-size: 0.75rem;
  color: #64748B;
}

.title {
  font-family: 'Poppins', sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 6px;
}
.subtitle {
  color: #64748B;
  font-size: 0.9rem;
  margin: 0 0 28px;
}

/* 表单 */
.form { display: flex; flex-direction: column; gap: 18px; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}
.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.field-icon {
  position: absolute;
  left: 14px;
  color: #94A3B8;
  pointer-events: none;
}
.input-wrap input {
  width: 100%;
  padding: 11px 42px 11px 42px;
  border: 1.5px solid #E2E8F0;
  border-radius: 10px;
  font-size: 0.95rem;
  font-family: inherit;
  color: #1E293B;
  background: #F8FAFC;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}
.input-wrap input:focus {
  border-color: #2563EB;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.input-wrap input:disabled { opacity: 0.6; cursor: not-allowed; }

.eye-btn {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: #94A3B8;
  padding: 4px;
  display: flex;
  align-items: center;
}
.eye-btn:hover { color: #64748B; }

.error-msg {
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: #DC2626;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.88rem;
  margin: 0;
}

/* 登录按钮 */
.btn-login {
  margin-top: 4px;
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  font-family: 'Poppins', sans-serif;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.35);
  transition: opacity 0.2s, transform 0.15s;
  letter-spacing: 0.04em;
}
.btn-login:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

/* 加载中旋转图标 */
.spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }

.hint-text {
  text-align: center;
  font-size: 0.78rem;
  color: #94A3B8;
  margin: 20px 0 0;
}
.hint-text code {
  background: #F1F5F9;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.78rem;
}
</style>
