<template>
  <div class="admin-shell">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">⚙️ 管理后台</div>
      <nav>
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item">
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="topbar">
        <h1 class="page-title">{{ currentTitle }}</h1>
        <span class="topbar-hint">Skill 商品化与自动交付平台</span>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { to: '/dashboard', icon: '📊', label: '仪表盘' },
  { to: '/skills', icon: '🧠', label: 'Skills' },
  { to: '/skus', icon: '🏷️', label: 'SKUs' },
  { to: '/orders', icon: '📦', label: '订单' },
  { to: '/tokens', icon: '🔑', label: 'Tokens' },
  { to: '/jobs', icon: '⚡', label: 'Jobs' },
]

const currentTitle = computed(() => {
  return navItems.find(n => route.path.startsWith(n.to))?.label ?? ''
})
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f6f9; color: #1a1a2e; }
a { color: inherit; text-decoration: none; }

/* 公共按钮 */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: none; font-weight: 500; transition: opacity .15s; }
.btn:hover { opacity: .85; }
.btn-primary { background: #4f6aff; color: #fff; }
.btn-danger { background: #e53e3e; color: #fff; }
.btn-secondary { background: #e8eaff; color: #4f6aff; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }

/* 公共表格 */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th { text-align: left; padding: 10px 12px; background: #f8f9ff; border-bottom: 2px solid #e2e6ff; color: #444; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .04em; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #eef0f8; vertical-align: middle; }
.data-table tr:hover td { background: #f8f9ff; }

/* 状态徽章 */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 600; }
.badge-active  { background: #d1fae5; color: #065f46; }
.badge-revoked { background: #fee2e2; color: #991b1b; }
.badge-expired { background: #fef9c3; color: #854d0e; }
.badge-queued  { background: #dbeafe; color: #1e40af; }
.badge-running { background: #fef3c7; color: #92400e; }
.badge-succeeded { background: #d1fae5; color: #065f46; }
.badge-failed  { background: #fee2e2; color: #991b1b; }
.badge-canceled { background: #f3f4f6; color: #4b5563; }
.badge-enabled { background: #d1fae5; color: #065f46; }
.badge-disabled { background: #f3f4f6; color: #6b7280; }
.badge-auto { background: #dbeafe; color: #1e40af; }
.badge-human { background: #fef3c7; color: #92400e; }
.badge-paid { background: #d1fae5; color: #065f46; }
.badge-pending { background: #fef9c3; color: #854d0e; }

/* 卡片 */
.card { background: #fff; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.07); }

/* 表单 */
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 0.8rem; font-weight: 600; color: #555; }
.form-group input, .form-group select, .form-group textarea {
  border: 1px solid #d1d5db; border-radius: 6px; padding: 8px 10px;
  font-size: 0.875rem; outline: none; width: 100%;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: #4f6aff; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* 错误与分页 */
.error-text { color: #c00; font-size: 0.85rem; margin-top: 8px; }
.pagination { display: flex; align-items: center; gap: 8px; margin-top: 16px; font-size: 0.875rem; }
.empty-row td { text-align: center; color: #aaa; padding: 32px; }
</style>

<style scoped>
.admin-shell { display: flex; min-height: 100vh; }

.sidebar {
  width: 220px;
  min-height: 100vh;
  background: #1a1a2e;
  color: #cdd;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: fixed;
  top: 0; left: 0; bottom: 0;
}

.logo {
  padding: 20px 20px 14px;
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  border-bottom: 1px solid rgba(255,255,255,.08);
  margin-bottom: 8px;
}

nav { display: flex; flex-direction: column; gap: 2px; padding: 0 8px; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #aab;
  transition: background .15s, color .15s;
}
.nav-item:hover { background: rgba(255,255,255,.07); color: #fff; }
.nav-item.router-link-active { background: #4f6aff; color: #fff; }
.nav-icon { font-size: 1rem; }

.main-area {
  margin-left: 220px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  background: #fff;
  border-bottom: 1px solid #eef0f8;
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 10;
}
.page-title { font-size: 1.1rem; font-weight: 700; color: #1a1a2e; }
.topbar-hint { font-size: 0.8rem; color: #999; }

.content { padding: 24px 28px; flex: 1; }
</style>
