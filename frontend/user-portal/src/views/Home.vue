<template>
  <div class="home" :class="{ dark: isDark }">
    <!-- ── Floating Navbar ── -->
    <nav class="navbar">
      <div class="nav-inner">
        <div class="nav-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#logo-grad)"/>
            <path d="M14 6L17.5 12.5H21L15.5 17L17.5 22L14 18.5L10.5 22L12.5 17L7 12.5H10.5L14 6Z" fill="white" opacity="0.9"/>
            <defs>
              <linearGradient id="logo-grad" x1="0" y1="0" x2="28" y2="28">
                <stop stop-color="#8B5CF6"/>
                <stop offset="1" stop-color="#EC4899"/>
              </linearGradient>
            </defs>
          </svg>
          <span>ArtForge</span>
        </div>
        <div class="nav-actions">
          <button class="theme-toggle" @click="isDark = !isDark" :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'">
            <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
          <a href="#gallery" class="nav-link">画廊</a>
          <a href="#create" class="nav-link">开始创作</a>
        </div>
      </div>
    </nav>

    <!-- ── Hero ── -->
    <section class="hero">
      <div class="hero-mesh" aria-hidden="true">
        <div class="mesh-blob blob1"/>
        <div class="mesh-blob blob2"/>
        <div class="mesh-blob blob3"/>
      </div>
      <div class="hero-inner">
        <div class="hero-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          AI 驱动生成式艺术平台
        </div>
        <h1 class="hero-title">
          将创意变为<br/>
          <span class="gradient-text">无限艺术</span>
        </h1>
        <p class="hero-desc">上传一张图片，AI 在秒级内将其转化为专业级艺术作品。支持修复、风格迁移、创意重绘等多种处理模式。</p>
        <div class="hero-ctas">
          <div class="token-input-row">
            <div class="token-input-wrap">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
              </svg>
              <input v-model="tokenInput" placeholder="输入您的 Token 开始创作…" @keyup.enter="go" />
            </div>
            <button class="btn-cta" :disabled="!tokenInput.trim()" @click="go">
              开始创作
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
          <p class="hero-hint">已有服务链接？直接粘贴 Token 即可访问</p>
        </div>
      </div>

      <!-- art preview grid -->
      <div class="hero-preview" aria-hidden="true">
        <div class="preview-grid">
          <div class="preview-card pc1"><div class="preview-shimmer"/></div>
          <div class="preview-card pc2"><div class="preview-shimmer"/></div>
          <div class="preview-card pc3"><div class="preview-shimmer"/></div>
          <div class="preview-card pc4"><div class="preview-shimmer"/></div>
          <div class="preview-card pc5"><div class="preview-shimmer"/></div>
        </div>
      </div>
    </section>

    <!-- ── How It Works / Bento ── -->
    <section id="create" class="bento-section">
      <div class="section-header">
        <h2 class="section-title">三步完成创作</h2>
        <p class="section-sub">简单快捷的 AI 艺术工作流</p>
      </div>
      <div class="bento-grid">
        <div class="bento-card bento-lg">
          <div class="bento-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3>上传原图</h3>
          <p>支持 JPG、PNG、WEBP 格式，最大 20MB。拖拽或点击上传，即时预览。</p>
          <div class="bento-step">01</div>
        </div>
        <div class="bento-card bento-sm">
          <div class="bento-icon icon-purple">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
          </div>
          <h3>AI 处理</h3>
          <p>模型在秒级内完成智能分析与艺术化处理。</p>
          <div class="bento-step">02</div>
        </div>
        <div class="bento-card bento-sm">
          <div class="bento-icon icon-pink">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </div>
          <h3>下载成品</h3>
          <p>高清输出，直接预览并一键下载您的专属艺术作品。</p>
          <div class="bento-step">03</div>
        </div>
        <div class="bento-card bento-wide">
          <div class="bento-icon icon-orange">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <h3>专属服务 Token</h3>
          <p>每个 Token 绑定专属套餐——自动处理或人工定制，灵活满足不同需求场景。</p>
          <div class="bento-pill-row">
            <span class="pill pill-blue">自动交付</span>
            <span class="pill pill-amber">人工协助</span>
            <span class="pill pill-green">次数计费</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Style Gallery ── -->
    <section id="gallery" class="gallery-section">
      <div class="section-header">
        <h2 class="section-title">风格画廊</h2>
        <p class="section-sub">探索多种 AI 艺术风格</p>
      </div>
      <div class="gallery-grid">
        <div v-for="style in artStyles" :key="style.name" class="gallery-item" :style="{ background: style.bg }">
          <div class="gallery-overlay">
            <span class="gallery-name">{{ style.name }}</span>
            <span class="gallery-desc">{{ style.desc }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ── CTA Footer ── -->
    <section class="cta-section">
      <div class="cta-card">
        <h2>准备好开始创作了吗？</h2>
        <p>使用您的专属 Token，立即体验 AI 艺术生成</p>
        <div class="token-input-row cta-input">
          <div class="token-input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
            </svg>
            <input v-model="tokenInput2" placeholder="输入 Token…" @keyup.enter="go2" />
          </div>
          <button class="btn-cta" :disabled="!tokenInput2.trim()" @click="go2">
            立即开始
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </section>

    <footer class="site-footer">
      <div class="footer-logo">
        <svg width="20" height="20" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="8" fill="url(#foot-grad)"/>
          <path d="M14 6L17.5 12.5H21L15.5 17L17.5 22L14 18.5L10.5 22L12.5 17L7 12.5H10.5L14 6Z" fill="white" opacity="0.9"/>
          <defs>
            <linearGradient id="foot-grad" x1="0" y1="0" x2="28" y2="28">
              <stop stop-color="#8B5CF6"/>
              <stop offset="1" stop-color="#EC4899"/>
            </linearGradient>
          </defs>
        </svg>
        ArtForge
      </div>
      <p>由 Skill Platform 提供支持 &nbsp;·&nbsp; AI 驱动的艺术生成服务</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const tokenInput = ref('')
const tokenInput2 = ref('')
const isDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

function go() {
  const t = tokenInput.value.trim()
  if (t) router.push(`/s/${t}`)
}
function go2() {
  const t = tokenInput2.value.trim()
  if (t) router.push(`/s/${t}`)
}

const artStyles = [
  { name: '印象派', desc: '光影流动的色彩世界', bg: 'linear-gradient(135deg,#667eea,#764ba2)' },
  { name: '赛博朋克', desc: '霓虹与数据的未来都市', bg: 'linear-gradient(135deg,#f093fb,#f5576c)' },
  { name: '水墨写意', desc: '东方美学的诗意表达', bg: 'linear-gradient(135deg,#4facfe,#00f2fe)' },
  { name: '像素艺术', desc: '复古与现代的创意碰撞', bg: 'linear-gradient(135deg,#43e97b,#38f9d7)' },
  { name: '油画质感', desc: '厚重纹理的视觉张力', bg: 'linear-gradient(135deg,#fa709a,#fee140)' },
  { name: '抽象几何', desc: '极简形式的无限可能', bg: 'linear-gradient(135deg,#a18cd1,#fbc2eb)' },
]
</script>

<style scoped>
/* ── Design Tokens ── */
.home {
  --bg: #FAFAFA;
  --bg-card: #FFFFFF;
  --text: #111111;
  --text-muted: #555555;
  --border: #E5E5E5;
  --accent: #8B5CF6;
  --accent2: #EC4899;
  --accent3: #F97316;
  --nav-bg: rgba(250,250,250,0.85);
  --hero-mesh: rgba(139,92,246,0.08);

  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'Manrope', sans-serif;
  transition: background 0.3s, color 0.3s;
  overflow-x: hidden;
}
.home.dark {
  --bg: #0A0A0A;
  --bg-card: #141414;
  --text: #F5F5F5;
  --text-muted: #999999;
  --border: #2A2A2A;
  --nav-bg: rgba(10,10,10,0.85);
  --hero-mesh: rgba(139,92,246,0.15);
}

/* ── Navbar ── */
.navbar {
  position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
  width: calc(100% - 48px); max-width: 1100px; z-index: 100;
  background: var(--nav-bg);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}
.nav-inner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px;
}
.nav-logo {
  display: flex; align-items: center; gap: 10px;
  font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.1rem;
  color: var(--text);
}
.nav-actions { display: flex; align-items: center; gap: 8px; }
.nav-link {
  padding: 6px 14px; border-radius: 8px; font-size: 0.875rem; font-weight: 500;
  color: var(--text-muted); cursor: pointer; transition: color 0.2s, background 0.2s;
  text-decoration: none;
}
.nav-link:hover { color: var(--text); background: rgba(139,92,246,0.08); }
.theme-toggle {
  width: 36px; height: 36px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; color: var(--text-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.2s, background 0.2s;
}
.theme-toggle:hover { background: rgba(139,92,246,0.1); color: var(--accent); }

/* ── Hero ── */
.hero {
  min-height: 100vh; display: grid; grid-template-columns: 1fr 1fr;
  align-items: center; gap: 40px;
  padding: 120px 48px 80px; max-width: 1200px; margin: 0 auto;
  position: relative;
}
.hero-mesh { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.mesh-blob {
  position: absolute; border-radius: 50%; filter: blur(80px);
  animation: drift 8s ease-in-out infinite alternate;
}
@media (prefers-reduced-motion: reduce) { .mesh-blob { animation: none; } }
.blob1 { width: 400px; height: 400px; background: rgba(139,92,246,0.18); top: 5%; left: -10%; animation-delay: 0s; }
.blob2 { width: 300px; height: 300px; background: rgba(236,72,153,0.14); top: 40%; right: 10%; animation-delay: -3s; }
.blob3 { width: 250px; height: 250px; background: rgba(249,115,22,0.12); bottom: 10%; left: 30%; animation-delay: -5s; }
@keyframes drift {
  from { transform: translate(0,0) scale(1); }
  to { transform: translate(30px, -20px) scale(1.05); }
}

.hero-inner { position: relative; z-index: 1; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.25);
  color: var(--accent); padding: 5px 12px; border-radius: 20px;
  font-size: 0.8rem; font-weight: 600; margin-bottom: 24px;
}
.hero-title {
  font-family: 'Syne', sans-serif; font-size: clamp(2.4rem, 5vw, 4rem);
  font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  color: var(--text); margin-bottom: 20px;
}
.gradient-text {
  background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-desc {
  font-size: 1.05rem; line-height: 1.75; color: var(--text-muted);
  max-width: 480px; margin-bottom: 36px;
}
.hero-ctas { display: flex; flex-direction: column; gap: 12px; }

/* Token Input */
.token-input-row { display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap; }
.token-input-wrap {
  flex: 1; min-width: 220px; position: relative;
  display: flex; align-items: center;
}
.input-icon {
  position: absolute; left: 14px; color: var(--text-muted); pointer-events: none;
}
.token-input-wrap input {
  width: 100%; padding: 13px 14px 13px 40px;
  background: var(--bg-card); border: 1.5px solid var(--border);
  border-radius: 10px; font-size: 0.9rem; color: var(--text);
  font-family: 'Manrope', sans-serif; outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.token-input-wrap input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(139,92,246,0.15); }
.token-input-wrap input::placeholder { color: var(--text-muted); }
.btn-cta {
  display: flex; align-items: center; gap: 8px;
  padding: 13px 24px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; font-family: 'Manrope', sans-serif;
  white-space: nowrap; transition: opacity 0.2s, transform 0.15s;
  box-shadow: 0 4px 15px rgba(139,92,246,0.35);
}
.btn-cta:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-cta:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.hero-hint { font-size: 0.82rem; color: var(--text-muted); }

/* Art preview */
.hero-preview { position: relative; z-index: 1; }
.preview-grid {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 180px 180px; gap: 12px;
}
.preview-card {
  border-radius: 14px; overflow: hidden; position: relative;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.pc1 { grid-column: 1/3; background: linear-gradient(135deg,#667eea,#764ba2); }
.pc2 { background: linear-gradient(135deg,#f093fb,#f5576c); }
.pc3 { background: linear-gradient(135deg,#4facfe,#00f2fe); }
.pc4 { grid-column: 2/4; background: linear-gradient(135deg,#43e97b,#38f9d7); }
.pc5 { background: linear-gradient(135deg,#fa709a,#fee140); }
.preview-shimmer {
  position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%);
  animation: shimmer 2.5s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) { .preview-shimmer { animation: none; } }
@keyframes shimmer {
  from { transform: translateX(-100%); }
  to { transform: translateX(100%); }
}

/* ── Sections ── */
.bento-section, .gallery-section { max-width: 1100px; margin: 0 auto; padding: 80px 48px; }
.section-header { text-align: center; margin-bottom: 48px; }
.section-title {
  font-family: 'Syne', sans-serif; font-size: clamp(1.8rem, 3vw, 2.6rem);
  font-weight: 700; color: var(--text); margin-bottom: 10px;
}
.section-sub { font-size: 1rem; color: var(--text-muted); }

/* ── Bento Grid ── */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: auto auto;
  gap: 16px;
}
.bento-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px; position: relative; overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s; cursor: default;
}
.bento-card:hover { box-shadow: 0 12px 40px rgba(0,0,0,0.1); transform: translateY(-2px); border-color: rgba(139,92,246,0.3); }
.bento-lg { grid-column: span 2; }
.bento-wide { grid-column: span 2; }
.bento-icon {
  width: 54px; height: 54px; border-radius: 12px;
  background: rgba(139,92,246,0.1); color: var(--accent);
  display: flex; align-items: center; justify-content: center; margin-bottom: 16px;
}
.bento-icon.icon-purple { background: rgba(139,92,246,0.1); color: #8B5CF6; }
.bento-icon.icon-pink { background: rgba(236,72,153,0.1); color: #EC4899; }
.bento-icon.icon-orange { background: rgba(249,115,22,0.1); color: #F97316; }
.bento-card h3 { font-family: 'Syne', sans-serif; font-size: 1.15rem; font-weight: 700; color: var(--text); margin-bottom: 8px; }
.bento-card p { font-size: 0.9rem; line-height: 1.7; color: var(--text-muted); }
.bento-step {
  position: absolute; top: 20px; right: 20px;
  font-family: 'Syne', sans-serif; font-size: 2.5rem; font-weight: 700;
  color: var(--border); line-height: 1;
}
.bento-pill-row { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
.pill { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
.pill-blue { background: rgba(59,130,246,0.12); color: #3B82F6; }
.pill-amber { background: rgba(245,158,11,0.12); color: #D97706; }
.pill-green { background: rgba(34,197,94,0.12); color: #16A34A; }

/* ── Gallery ── */
.gallery-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.gallery-item {
  aspect-ratio: 4/3; border-radius: 14px; position: relative; overflow: hidden;
  cursor: pointer; transition: transform 0.25s;
}
.gallery-item:hover { transform: scale(1.02); }
.gallery-item:hover .gallery-overlay { opacity: 1; }
.gallery-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 60%);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 16px; opacity: 0; transition: opacity 0.25s;
}
.gallery-name { color: #fff; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1rem; }
.gallery-desc { color: rgba(255,255,255,0.8); font-size: 0.8rem; margin-top: 2px; }

/* ── CTA Section ── */
.cta-section { padding: 60px 48px; max-width: 900px; margin: 0 auto; }
.cta-card {
  background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(236,72,153,0.06));
  border: 1px solid rgba(139,92,246,0.2);
  border-radius: 20px; padding: 48px 40px; text-align: center;
}
.cta-card h2 { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: var(--text); margin-bottom: 10px; }
.cta-card p { color: var(--text-muted); margin-bottom: 28px; }
.cta-input { justify-content: center; }

/* ── Footer ── */
.site-footer {
  text-align: center; padding: 32px 48px;
  border-top: 1px solid var(--border);
  color: var(--text-muted); font-size: 0.85rem;
}
.footer-logo {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.95rem;
  color: var(--text); margin-bottom: 8px;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding: 100px 24px 60px; text-align: center; }
  .hero-desc { max-width: 100%; }
  .hero-preview { display: none; }
  .hero-ctas { align-items: center; }
  .bento-section, .gallery-section, .cta-section { padding: 60px 24px; }
  .bento-grid { grid-template-columns: 1fr; }
  .bento-lg, .bento-wide { grid-column: span 1; }
  .gallery-grid { grid-template-columns: repeat(2, 1fr); }
  .navbar { width: calc(100% - 32px); }
}
@media (max-width: 540px) {
  .gallery-grid { grid-template-columns: 1fr; }
  .token-input-row { flex-direction: column; }
  .btn-cta { width: 100%; justify-content: center; }
}
</style>
