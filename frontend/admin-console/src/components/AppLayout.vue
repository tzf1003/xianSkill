<template>
  <div class="admin-shell">
    <!-- ── Sidebar ── -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="7" fill="rgba(255,255,255,0.15)"/>
            <path d="M14 5L17.5 11.5H21L15.5 16L17.5 21L14 17.5L10.5 21L12.5 16L7 11.5H10.5L14 5Z" fill="white" opacity="0.95"/>
          </svg>
        </div>
        <div class="logo-text">
          <span class="logo-name">ArtForge</span>
          <span class="logo-sub">管理控制台</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section-label">主菜单</div>
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item">
          <span class="nav-icon" v-html="item.icon"/>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="user-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <div class="user-info">
            <span class="user-name">管理员</span>
            <span class="user-role">Admin</span>
          </div>
          <button class="logout-btn" title="退出登录" @click="logout()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- ── Main Area ── -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <div class="breadcrumb">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="breadcrumb-home">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-current">{{ currentTitle }}</span>
          </div>
        </div>
        <div class="topbar-right">
          <div class="topbar-badge">
            <span class="status-dot"/>
            系统正常
          </div>
          <div class="topbar-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
        </div>
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
import { logout } from '@/api/client'

const route = useRoute()

const navItems = [
  {
    to: '/dashboard', label: '仪表盘',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`
  },
  {
    to: '/skills', label: 'Skills',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`
  },
  {
    to: '/skus', label: 'SKUs',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`
  },
  {
    to: '/orders', label: '订单',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>`
  },
  {
    to: '/tokens', label: 'Tokens',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>`
  },
  {
    to: '/jobs', label: 'Jobs',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M22 12h-2M4 12H2M18.66 18.66l-1.41-1.41M6.34 5.34l-1.41 1.41M12 2v2M12 20v2"/></svg>`
  },
]

const currentTitle = computed(() => {
  return navItems.find(n => route.path.startsWith(n.to))?.label ?? '管理后台'
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Open Sans', -apple-system, sans-serif;
  background: #F8FAFC;
  color: #1E293B;
}
a { color: inherit; text-decoration: none; }

/* ── Design Tokens ── */
:root {
  --primary: #2563EB;
  --primary-light: #EFF6FF;
  --primary-hover: #1D4ED8;
  --cta: #F97316;
  --cta-hover: #EA6C10;
  --bg: #F8FAFC;
  --bg-card: #FFFFFF;
  --text: #1E293B;
  --text-muted: #64748B;
  --border: #E2E8F0;
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --info: #3B82F6;
  --radius: 10px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}

/* ── Buttons ── */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px; font-size: 0.875rem;
  cursor: pointer; border: none; font-weight: 500;
  font-family: 'Open Sans', sans-serif;
  transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
}
.btn:hover { transform: translateY(-1px); }
.btn:active { transform: translateY(0); }
.btn-primary { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(37,99,235,0.3); }
.btn-primary:hover { background: var(--primary-hover); box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
.btn-danger { background: var(--danger); color: #fff; box-shadow: 0 2px 8px rgba(239,68,68,0.3); }
.btn-danger:hover { background: #DC2626; }
.btn-secondary { background: var(--primary-light); color: var(--primary); border: 1px solid rgba(37,99,235,0.2); }
.btn-secondary:hover { background: #DBEAFE; }
.btn-cta { background: var(--cta); color: #fff; box-shadow: 0 2px 8px rgba(249,115,22,0.3); }
.btn-cta:hover { background: var(--cta-hover); }
.btn-ghost { background: transparent; color: var(--text-muted); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--bg); border-color: var(--primary); color: var(--primary); }
.btn-sm { padding: 5px 11px; font-size: 0.8rem; border-radius: 6px; }

/* ── Tables ── */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th {
  text-align: left; padding: 11px 14px;
  background: var(--bg); border-bottom: 2px solid var(--border);
  color: var(--text-muted); font-weight: 600; font-size: 0.75rem;
  text-transform: uppercase; letter-spacing: .06em;
  font-family: 'Poppins', sans-serif;
}
.data-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #F8FAFC; }

/* ── Badges ── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}
.badge::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.badge-active    { background: #D1FAE5; color: #065F46; }
.badge-revoked   { background: #FEE2E2; color: #991B1B; }
.badge-expired   { background: #FEF9C3; color: #854D0E; }
.badge-queued    { background: #DBEAFE; color: #1E40AF; }
.badge-running   { background: #FEF3C7; color: #92400E; }
.badge-succeeded { background: #D1FAE5; color: #065F46; }
.badge-failed    { background: #FEE2E2; color: #991B1B; }
.badge-canceled  { background: #F3F4F6; color: #4B5563; }
.badge-enabled   { background: #D1FAE5; color: #065F46; }
.badge-disabled  { background: #F3F4F6; color: #6B7280; }
.badge-auto      { background: #DBEAFE; color: #1E40AF; }
.badge-human     { background: #FEF3C7; color: #92400E; }
.badge-paid      { background: #D1FAE5; color: #065F46; }
.badge-pending   { background: #FEF9C3; color: #854D0E; }

/* ── Cards ── */
.card {
  background: var(--bg-card); border-radius: var(--radius);
  padding: 20px 24px; box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
}

/* ── Forms ── */
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-group label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); letter-spacing: .04em; }
.form-group input, .form-group select, .form-group textarea {
  border: 1.5px solid var(--border); border-radius: 8px; padding: 9px 12px;
  font-size: 0.875rem; outline: none; width: 100%;
  font-family: 'Open Sans', sans-serif; color: var(--text);
  background: var(--bg-card); transition: border-color 0.2s, box-shadow 0.2s;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* ── Utilities ── */
.error-text { color: var(--danger); font-size: 0.85rem; margin-top: 8px; }
.pagination { display: flex; align-items: center; gap: 8px; margin-top: 16px; font-size: 0.875rem; color: var(--text-muted); }
.empty-row td { text-align: center; color: var(--text-muted); padding: 40px; }
</style>

<style scoped>
/* ── Shell Layout ── */
.admin-shell { display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  width: 240px; min-height: 100vh;
  background: linear-gradient(175deg, #0F172A 0%, #1E293B 60%, #0F172A 100%);
  display: flex; flex-direction: column; flex-shrink: 0;
  position: fixed; top: 0; left: 0; bottom: 0;
  border-right: 1px solid rgba(255,255,255,0.06);
}

/* Logo Area */
.sidebar-logo {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 18px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}
.logo-mark {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(37,99,235,0.4);
}
.logo-text { display: flex; flex-direction: column; line-height: 1.2; }
.logo-name { font-family: 'Poppins', sans-serif; font-size: 1rem; font-weight: 700; color: #F1F5F9; }
.logo-sub { font-size: 0.7rem; color: rgba(255,255,255,0.4); letter-spacing: .05em; }

/* Nav */
.sidebar-nav { flex: 1; padding: 16px 10px 0; display: flex; flex-direction: column; gap: 2px; }
.nav-section-label {
  font-size: 0.68rem; font-weight: 700; color: rgba(255,255,255,0.3);
  letter-spacing: .1em; text-transform: uppercase; padding: 0 8px 8px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 9px; font-size: 0.875rem; color: rgba(255,255,255,0.55);
  cursor: pointer; transition: background 0.15s, color 0.15s;
  position: relative;
}
.nav-item:hover { background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.9); }
.nav-item.router-link-active {
  background: rgba(37,99,235,0.25);
  color: #93C5FD;
  border: 1px solid rgba(37,99,235,0.3);
}
.nav-item.router-link-active .nav-icon { color: #60A5FA; }
.nav-icon { flex-shrink: 0; }
.nav-label { flex: 1; font-weight: 500; }
.nav-badge {
  background: rgba(37,99,235,0.3); color: #93C5FD;
  font-size: 0.7rem; font-weight: 700; padding: 2px 7px; border-radius: 10px;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 12px 10px; border-top: 1px solid rgba(255,255,255,0.07);
}
.sidebar-user {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 9px; cursor: pointer;
  transition: background 0.15s; background: rgba(255,255,255,0.04);
}
.sidebar-user:hover { background: rgba(255,255,255,0.08); }
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  display: flex; align-items: center; justify-content: center; color: white;
}
.user-info { display: flex; flex-direction: column; line-height: 1.3; flex: 1; }
.user-name { font-size: 0.8rem; font-weight: 600; color: rgba(255,255,255,0.85); }
.user-role { font-size: 0.7rem; color: rgba(255,255,255,0.35); }
.logout-btn {
  background: none; border: none; cursor: pointer; color: rgba(255,255,255,0.4);
  padding: 4px; display: flex; align-items: center; border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.logout-btn:hover { color: #F97316; background: rgba(249,115,22,0.12); }

/* ── Main Area ── */
.main-area { margin-left: 240px; flex: 1; display: flex; flex-direction: column; min-height: 100vh; }

/* Topbar */
.topbar {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 14px 28px; display: flex; align-items: center;
  justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}
.topbar-left, .topbar-right { display: flex; align-items: center; gap: 12px; }
.breadcrumb {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.875rem; color: var(--text-muted);
}
.breadcrumb-home { color: var(--text-muted); }
.breadcrumb-sep { color: var(--border); }
.breadcrumb-current { color: var(--text); font-weight: 600; font-family: 'Poppins', sans-serif; }
.topbar-badge {
  display: flex; align-items: center; gap: 6px;
  background: #D1FAE5; color: #065F46;
  font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px;
}
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #10B981; }
.topbar-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #7C3AED);
  display: flex; align-items: center; justify-content: center;
  color: white; cursor: pointer;
}

/* Content */
.content { padding: 28px 32px; flex: 1; }
</style>


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
