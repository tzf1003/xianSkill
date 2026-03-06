<template>
  <div class="home" :class="{ dark: isDark }">

    <!-- Floating Navbar -->
    <nav class="navbar" role="navigation" aria-label="主导航">
      <div class="nav-inner">
        <div class="nav-logo">
          <div class="logo-mark" aria-hidden="true">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <defs>
                <linearGradient id="lg-nav" x1="0" y1="0" x2="32" y2="32">
                  <stop stop-color="#7C3AED"/>
                  <stop offset="1" stop-color="#DB2777"/>
                </linearGradient>
              </defs>
              <rect width="32" height="32" rx="10" fill="url(#lg-nav)"/>
              <path d="M16 7L19.5 13.5H23L17.5 18.5L19.5 24L16 20.5L12.5 24L14.5 18.5L9 13.5H12.5L16 7Z" fill="white" opacity="0.95"/>
            </svg>
          </div>
          <span class="logo-text">ArtForge</span>
        </div>
        <div class="nav-links">
          <a href="#features" class="nav-link">功能</a>
          <a href="#gallery" class="nav-link">画廊</a>
          <a href="#projects" class="nav-link">项目</a>
        </div>
        <div class="nav-actions">
          <button class="theme-toggle" @click="isDark = !isDark" :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'">
            <svg v-if="isDark" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
          <a href="#start" class="nav-cta-btn">
            立即开始
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </a>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero" id="start" aria-label="欢迎区域">
      <div class="hero-ambient" aria-hidden="true">
        <div class="amb-blob amb1"/>
        <div class="amb-blob amb2"/>
        <div class="amb-blob amb3"/>
        <div class="grid-lines"/>
      </div>
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-eyebrow">
            <div class="eyebrow-dot" aria-hidden="true"/>
            <span>AI 驱动生成式艺术平台</span>
          </div>
          <h1 class="hero-title">
            将创意<br/>
            <span class="hero-gradient">转化为艺术</span>
          </h1>
          <p class="hero-desc">
            上传图片，AI 在秒级内完成修复、风格迁移与创意重绘。让每一张普通照片，都成为独一无二的艺术作品。
          </p>
          <div class="input-block" id="start-input">
            <label for="token-main" class="sr-only">输入 Token</label>
            <div class="input-row">
              <div class="input-wrap">
                <svg class="input-prefix-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                </svg>
                <input id="token-main" v-model="tokenInput" type="text" placeholder="粘贴您的专属 Token" @keyup.enter="go" autocomplete="off" spellcheck="false"/>
              </div>
              <button class="btn-primary" :disabled="!tokenInput.trim()" @click="go">
                开始创作
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </button>
            </div>
            <p class="input-hint">已有服务链接？直接粘贴 Token 即可访问</p>
          </div>
          <div class="stats-row">
            <div class="stat-item"><span class="stat-num">10K+</span><span class="stat-label">艺术作品</span></div>
            <div class="stat-divider" aria-hidden="true"/>
            <div class="stat-item"><span class="stat-num">&lt;5s</span><span class="stat-label">处理时间</span></div>
            <div class="stat-divider" aria-hidden="true"/>
            <div class="stat-item"><span class="stat-num">6+</span><span class="stat-label">艺术风格</span></div>
          </div>
        </div>
        <div class="hero-mosaic" aria-hidden="true">
          <div class="mosaic-grid">
            <div class="mosaic-card mc-tall mc1"><div class="mosaic-label">印象派</div></div>
            <div class="mosaic-card mc2"><div class="mosaic-label">赛博朋克</div></div>
            <div class="mosaic-card mc3"><div class="mosaic-label">水墨写意</div></div>
            <div class="mosaic-card mc-wide mc4"><div class="mosaic-label">抽象几何</div></div>
            <div class="mosaic-card mc5"><div class="mosaic-label">油画质感</div></div>
          </div>
          <div class="mosaic-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            <span>高清输出</span>
          </div>
        </div>
      </div>
      <div class="scroll-hint" aria-hidden="true"><div class="scroll-dot"/></div>
    </section>

    <!-- Features -->
    <section id="features" class="features-section" aria-labelledby="features-title">
      <div class="section-head">
        <div class="section-tag">核心功能</div>
        <h2 class="section-title" id="features-title">三步完成创作</h2>
        <p class="section-sub">简单快捷的 AI 艺术工作流，无需专业技能</p>
      </div>
      <div class="bento-grid">
        <article class="bento-card b-lg">
          <div class="bento-num" aria-hidden="true">01</div>
          <div class="bento-icon-wrap ic-violet">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3>上传原图</h3>
          <p>支持 JPG、PNG、WEBP，最大 20MB。拖拽或点击上传，即时预览确认。</p>
          <div class="bento-deco" aria-hidden="true"><div class="deco-ring r1"/><div class="deco-ring r2"/></div>
        </article>
        <article class="bento-card b-sm">
          <div class="bento-num" aria-hidden="true">02</div>
          <div class="bento-icon-wrap ic-pink">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
          </div>
          <h3>AI 处理</h3>
          <p>模型在秒级内完成智能分析与艺术化处理，全自动无需等待。</p>
        </article>
        <article class="bento-card b-sm">
          <div class="bento-num" aria-hidden="true">03</div>
          <div class="bento-icon-wrap ic-emerald">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </div>
          <h3>下载成品</h3>
          <p>高清输出，即时预览并一键下载，专属艺术作品永久保存。</p>
        </article>
        <article class="bento-card b-wide glass-card">
          <div class="bento-icon-wrap ic-amber">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div class="bento-wide-body">
            <h3>专属服务 Token</h3>
            <p>每个 Token 绑定专属套餐，自动处理或人工定制，灵活满足不同需求。</p>
          </div>
          <div class="bento-pills">
            <span class="pill pill-violet">自动交付</span>
            <span class="pill pill-amber">人工协助</span>
            <span class="pill pill-green">次数计费</span>
          </div>
        </article>
      </div>
    </section>

    <!-- Projects -->
    <section id="projects" class="projects-section" aria-labelledby="projects-title">
      <div class="section-head">
        <div class="section-tag">处理项目</div>
        <h2 class="section-title" id="projects-title">选择您的项目</h2>
        <p class="section-sub">每个项目都有专属 AI 处理流程，选择最适合您需求的方案</p>
      </div>
      <div v-if="projectsLoading" class="loading-state" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true"/>
        <span class="sr-only">正在加载项目...</span>
      </div>
      <div v-else-if="projects.length" class="projects-grid">
        <article v-for="proj in projects" :key="proj.slug" class="project-card"
          @click="selectProject(proj.slug)" tabindex="0" @keyup.enter="selectProject(proj.slug)"
          :aria-label="`选择项目：${proj.name}`">
          <div class="project-cover" :style="proj.cover_url ? `background-image:url(${proj.cover_url})` : ''" aria-hidden="true">
            <div v-if="!proj.cover_url" class="cover-placeholder">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5" aria-hidden="true">
                <rect x="3" y="3" width="18" height="18" rx="3"/>
                <circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
              </svg>
            </div>
            <div class="cover-overlay"/>
          </div>
          <div class="project-body">
            <span class="project-badge">AI 处理</span>
            <h3 class="project-name">{{ proj.name }}</h3>
            <p v-if="proj.description" class="project-desc">{{ proj.description }}</p>
            <transition name="hint-fade">
              <div v-if="selectedProject === proj.slug" class="project-input-area" @click.stop>
                <label :for="`token-${proj.slug}`" class="sr-only">输入 Token</label>
                <div class="hint-row">
                  <input :id="`token-${proj.slug}`" v-model="tokenInput" placeholder="输入 Token 访问此项目" @keyup.enter="go" class="hint-input" autocomplete="off"/>
                  <button class="btn-sm" :disabled="!tokenInput.trim()" @click="go">开始</button>
                </div>
              </div>
              <button v-else class="project-action-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                立即使用
              </button>
            </transition>
          </div>
        </article>
      </div>
      <div v-else class="empty-state" role="status">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="3"/>
          <circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
        </svg>
        <p>暂无可用项目</p>
      </div>
    </section>

    <!-- Gallery -->
    <section id="gallery" class="gallery-section" aria-labelledby="gallery-title">
      <div class="section-head">
        <div class="section-tag">风格画廊</div>
        <h2 class="section-title" id="gallery-title">探索艺术风格</h2>
        <p class="section-sub">六种独特 AI 艺术风格，满足不同创意需求</p>
      </div>
      <div class="gallery-grid">
        <div v-for="style in artStyles" :key="style.name" class="gallery-item"
          :style="{ background: style.bg }" :aria-label="`${style.name}：${style.desc}`">
          <div class="gallery-shimmer" aria-hidden="true"/>
          <div class="gallery-overlay">
            <span class="gallery-name">{{ style.name }}</span>
            <span class="gallery-sub">{{ style.desc }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section" aria-labelledby="cta-title">
      <div class="cta-inner">
        <div class="cta-glow" aria-hidden="true"/>
        <div class="cta-content">
          <div class="section-tag" style="margin: 0 auto 16px;">开始创作</div>
          <h2 class="cta-title" id="cta-title">准备好了吗？</h2>
          <p class="cta-sub">使用您的专属 Token，立即体验 AI 艺术生成的魔力</p>
          <div class="input-row cta-input-row">
            <label for="token-cta" class="sr-only">输入 Token</label>
            <div class="input-wrap">
              <svg class="input-prefix-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
              </svg>
              <input id="token-cta" v-model="tokenInput2" type="text" placeholder="输入 Token" @keyup.enter="go2" autocomplete="off"/>
            </div>
            <button class="btn-primary" :disabled="!tokenInput2.trim()" @click="go2">
              立即开始
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="site-footer" role="contentinfo">
      <div class="footer-inner">
        <div class="footer-brand">
          <svg width="22" height="22" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <defs>
              <linearGradient id="lg-foot" x1="0" y1="0" x2="32" y2="32">
                <stop stop-color="#7C3AED"/>
                <stop offset="1" stop-color="#DB2777"/>
              </linearGradient>
            </defs>
            <rect width="32" height="32" rx="10" fill="url(#lg-foot)"/>
            <path d="M16 7L19.5 13.5H23L17.5 18.5L19.5 24L16 20.5L12.5 24L14.5 18.5L9 13.5H12.5L16 7Z" fill="white" opacity="0.95"/>
          </svg>
          <span>ArtForge</span>
        </div>
        <p class="footer-text">由 Skill Platform 提供支持 &nbsp;&nbsp; AI 驱动的艺术生成服务</p>
      </div>
    </footer>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listProjects, type ProjectInfo } from '@/api/client'

const router = useRouter()
const tokenInput = ref('')
const tokenInput2 = ref('')
const isDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)
const projects = ref<ProjectInfo[]>([])
const projectsLoading = ref(true)
const selectedProject = ref<string | null>(null)

onMounted(async () => {
  try { projects.value = (await listProjects()).filter(p => p.enabled) }
  catch { /* ignore */ }
  finally { projectsLoading.value = false }
})

function go() {
  const t = tokenInput.value.trim()
  if (t) router.push(`/s/${t}`)
}
function go2() {
  const t = tokenInput2.value.trim()
  if (t) router.push(`/s/${t}`)
}
function selectProject(slug: string) {
  selectedProject.value = selectedProject.value === slug ? null : slug
}

const artStyles = [
  { name: '印象派',   desc: '光影流动的色彩世界',   bg: 'linear-gradient(145deg,#667eea 0%,#764ba2 100%)' },
  { name: '赛博朋克', desc: '霓虹与数据的未来都市', bg: 'linear-gradient(145deg,#f093fb 0%,#f5576c 100%)' },
  { name: '水墨写意', desc: '东方美学的诗意表达',   bg: 'linear-gradient(145deg,#4facfe 0%,#00f2fe 100%)' },
  { name: '像素艺术', desc: '复古与现代的创意碰撞', bg: 'linear-gradient(145deg,#43e97b 0%,#38f9d7 100%)' },
  { name: '油画质感', desc: '厚重纹理的视觉张力',   bg: 'linear-gradient(145deg,#fa709a 0%,#fee140 100%)' },
  { name: '抽象几何', desc: '极简形式的无限可能',   bg: 'linear-gradient(145deg,#a18cd1 0%,#fbc2eb 100%)' },
]
</script>

<style scoped>
.home {
  --bg:#F7F7FA; --bg-card:#FFFFFF; --bg-card-alt:#F1F1F6;
  --text:#0D0D14; --text-muted:#52526E; --text-subtle:#8888A8;
  --border:#E2E2EE; --border-soft:#EBEBF5;
  --accent:#7C3AED; --accent2:#DB2777; --accent3:#EA580C;
  --accent-glow:rgba(124,58,237,0.22);
  --nav-bg:rgba(247,247,250,0.88);
  --shadow-sm:0 1px 4px rgba(0,0,0,0.05);
  --shadow-md:0 4px 20px rgba(0,0,0,0.08);
  --shadow-lg:0 12px 48px rgba(0,0,0,0.10);
  --r-sm:10px; --r-md:14px; --r-lg:20px; --r-xl:28px;
  min-height:100vh; background:var(--bg); color:var(--text);
  font-family:'Archivo',sans-serif; transition:background .35s,color .35s; overflow-x:hidden;
}
.home.dark {
  --bg:#07070F; --bg-card:#111120; --bg-card-alt:#181828;
  --text:#EEEEF8; --text-muted:#8888A8; --text-subtle:#50506A;
  --border:#22223A; --border-soft:#1A1A2E;
  --nav-bg:rgba(7,7,15,0.90);
  --accent-glow:rgba(124,58,237,0.32);
  --shadow-md:0 4px 20px rgba(0,0,0,0.45);
  --shadow-lg:0 12px 48px rgba(0,0,0,0.55);
}
.sr-only { position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0; }

/* Navbar */
.navbar {
  position:fixed; top:14px; left:50%; transform:translateX(-50%);
  width:calc(100% - 40px); max-width:1160px; z-index:200;
  background:var(--nav-bg); backdrop-filter:blur(28px); -webkit-backdrop-filter:blur(28px);
  border:1px solid var(--border); border-radius:var(--r-lg); box-shadow:var(--shadow-md);
}
.nav-inner { display:flex; align-items:center; justify-content:space-between; padding:10px 18px; gap:16px; }
.nav-logo { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.logo-mark { display:flex; }
.logo-text { font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem; color:var(--text); letter-spacing:-0.01em; }
.nav-links { display:flex; align-items:center; gap:2px; flex:1; justify-content:center; }
.nav-link { padding:6px 16px; border-radius:var(--r-sm); font-size:.875rem; font-weight:500; color:var(--text-muted); cursor:pointer; text-decoration:none; transition:color .2s,background .2s; }
.nav-link:hover { color:var(--text); background:rgba(124,58,237,0.07); }
.nav-actions { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.theme-toggle { width:36px; height:36px; border-radius:var(--r-sm); border:1px solid var(--border); background:transparent; color:var(--text-muted); cursor:pointer; display:flex; align-items:center; justify-content:center; transition:color .2s,background .2s,border-color .2s; }
.theme-toggle:hover { background:rgba(124,58,237,0.08); color:var(--accent); border-color:rgba(124,58,237,0.25); }
.theme-toggle:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.nav-cta-btn { display:inline-flex; align-items:center; gap:7px; padding:8px 18px; border-radius:var(--r-sm); background:linear-gradient(135deg,var(--accent) 0%,var(--accent2) 100%); color:#fff; font-size:.85rem; font-weight:700; text-decoration:none; cursor:pointer; box-shadow:0 3px 14px var(--accent-glow); transition:opacity .2s,transform .15s; }
.nav-cta-btn:hover { opacity:.9; transform:translateY(-1px); }

/* Hero */
.hero { min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:120px 48px 80px; position:relative; overflow:hidden; }
.hero-ambient { position:absolute; inset:0; overflow:hidden; pointer-events:none; }
.amb-blob { position:absolute; border-radius:50%; filter:blur(100px); }
.amb1 { width:520px; height:520px; background:rgba(124,58,237,0.12); top:-12%; left:-10%; }
.amb2 { width:400px; height:400px; background:rgba(219,39,119,0.09); top:30%; right:-6%; }
.amb3 { width:320px; height:320px; background:rgba(234,88,12,0.07); bottom:5%; left:32%; }
@media (prefers-reduced-motion:no-preference) {
  .amb1 { animation:adrift 12s ease-in-out infinite alternate; }
  .amb2 { animation:adrift 9s ease-in-out infinite alternate-reverse; }
  .amb3 { animation:adrift 14s ease-in-out infinite alternate; }
}
@keyframes adrift { from{transform:translate(0,0) scale(1)} to{transform:translate(28px,-20px) scale(1.07)} }
.grid-lines {
  position:absolute; inset:0;
  background-image:linear-gradient(var(--border-soft) 1px,transparent 1px),linear-gradient(90deg,var(--border-soft) 1px,transparent 1px);
  background-size:64px 64px;
  mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,#000 0%,transparent 100%);
  opacity:.6;
}
.hero-content { display:grid; grid-template-columns:1fr 1fr; align-items:center; gap:64px; width:100%; max-width:1200px; position:relative; z-index:1; }
.hero-left { display:flex; flex-direction:column; }
.hero-eyebrow { display:inline-flex; align-items:center; gap:8px; padding:6px 14px; border-radius:40px; background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.2); color:var(--accent); font-size:.8rem; font-weight:700; letter-spacing:.02em; margin-bottom:22px; width:fit-content; }
.eyebrow-dot { width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px rgba(124,58,237,0.6); }
@media (prefers-reduced-motion:no-preference) { .eyebrow-dot { animation:blink-glow 2.6s ease-in-out infinite; } }
@keyframes blink-glow { 0%,100%{box-shadow:0 0 6px rgba(124,58,237,0.5)}50%{box-shadow:0 0 16px rgba(124,58,237,0.85)} }
.hero-title { font-family:'Space Grotesk',sans-serif; font-size:clamp(2.8rem,5.5vw,4.5rem); font-weight:700; line-height:1.08; letter-spacing:-0.035em; color:var(--text); margin-bottom:22px; }
.hero-gradient { display:inline; background:linear-gradient(135deg,var(--accent) 0%,var(--accent2) 55%,var(--accent3) 100%); background-size:200% auto; -webkit-background-clip:text; background-clip:text; color:transparent; }
@media (prefers-reduced-motion:no-preference) { .hero-gradient { animation:grad-move 6s linear infinite; } }
@keyframes grad-move { from{background-position:0% center} to{background-position:200% center} }
.hero-desc { font-size:1.05rem; line-height:1.8; color:var(--text-muted); max-width:460px; margin-bottom:36px; }
.input-block { display:flex; flex-direction:column; gap:10px; margin-bottom:36px; }
.input-row { display:flex; gap:10px; align-items:stretch; flex-wrap:wrap; }
.input-wrap { flex:1; min-width:210px; position:relative; display:flex; align-items:center; }
.input-prefix-icon { position:absolute; left:14px; color:var(--text-subtle); pointer-events:none; z-index:1; }
.input-wrap input { width:100%; padding:14px 14px 14px 42px; background:var(--bg-card); border:1.5px solid var(--border); border-radius:var(--r-md); font-size:.9rem; font-family:'Archivo',sans-serif; color:var(--text); outline:none; box-shadow:var(--shadow-sm); transition:border-color .2s,box-shadow .2s; }
.input-wrap input:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(124,58,237,0.12); }
.input-wrap input::placeholder { color:var(--text-subtle); }
.input-hint { font-size:.8rem; color:var(--text-subtle); }
.btn-primary { display:inline-flex; align-items:center; gap:8px; padding:14px 26px; border-radius:var(--r-md); border:none; background:linear-gradient(135deg,var(--accent) 0%,var(--accent2) 100%); color:#fff; font-size:.9rem; font-weight:700; font-family:'Archivo',sans-serif; cursor:pointer; white-space:nowrap; box-shadow:0 4px 18px var(--accent-glow); transition:opacity .2s,transform .15s,box-shadow .2s; }
.btn-primary:hover:not(:disabled) { opacity:.9; transform:translateY(-2px); box-shadow:0 8px 28px var(--accent-glow); }
.btn-primary:active:not(:disabled) { transform:translateY(0); }
.btn-primary:disabled { opacity:.45; cursor:not-allowed; transform:none; }
.btn-primary:focus-visible { outline:3px solid var(--accent); outline-offset:2px; }
.stats-row { display:flex; align-items:center; gap:24px; }
.stat-item { display:flex; flex-direction:column; gap:2px; }
.stat-num { font-family:'Space Grotesk',sans-serif; font-size:1.55rem; font-weight:700; letter-spacing:-0.025em; color:var(--text); line-height:1; }
.stat-label { font-size:.76rem; color:var(--text-muted); font-weight:500; }
.stat-divider { width:1px; height:36px; background:var(--border); }

/* Mosaic */
.hero-mosaic { position:relative; }
.mosaic-grid { display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:145px 145px; gap:10px; }
.mosaic-card { border-radius:var(--r-md); overflow:hidden; position:relative; box-shadow:var(--shadow-md); transition:transform .3s,box-shadow .3s; }
.mosaic-card:hover { transform:scale(1.025); box-shadow:var(--shadow-lg); z-index:2; }
.mc-tall { grid-row:span 2; } .mc-wide { grid-column:span 2; }
.mc1{background:linear-gradient(145deg,#667eea,#764ba2)} .mc2{background:linear-gradient(145deg,#f093fb,#f5576c)}
.mc3{background:linear-gradient(145deg,#4facfe,#00f2fe)} .mc4{background:linear-gradient(145deg,#fa709a,#fee140)}
.mc5{background:linear-gradient(145deg,#43e97b,#38f9d7)}
.mosaic-label { position:absolute; bottom:0; left:0; right:0; padding:10px 12px; background:linear-gradient(to top,rgba(0,0,0,0.52),transparent); color:#fff; font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; opacity:0; transition:opacity .25s; }
.mosaic-card:hover .mosaic-label { opacity:1; }
@media (prefers-reduced-motion:reduce) { .mosaic-card,.mosaic-label { transition:none; } }
.mosaic-badge { position:absolute; bottom:-14px; right:-10px; display:inline-flex; align-items:center; gap:6px; background:var(--bg-card); border:1px solid var(--border); border-radius:40px; padding:7px 14px; font-size:.8rem; font-weight:600; color:var(--text); box-shadow:var(--shadow-md); white-space:nowrap; }

/* Scroll hint */
.scroll-hint { position:absolute; bottom:28px; left:50%; transform:translateX(-50%); width:26px; height:42px; border-radius:13px; border:2px solid var(--border); display:flex; align-items:center; justify-content:center; }
.scroll-dot { width:5px; height:5px; border-radius:50%; background:var(--accent); }
@media (prefers-reduced-motion:no-preference) { .scroll-dot { animation:drop 2.2s ease-in-out infinite; } }
@keyframes drop { 0%{transform:translateY(-8px);opacity:0} 30%{opacity:1} 70%{opacity:1} 100%{transform:translateY(8px);opacity:0} }
@media (prefers-reduced-motion:reduce) { .amb-blob,.eyebrow-dot,.hero-gradient,.scroll-dot{animation:none!important} }

/* Sections */
.features-section,.projects-section,.gallery-section { max-width:1160px; margin:0 auto; padding:96px 48px; }
.section-head { text-align:center; margin-bottom:56px; }
.section-tag { display:inline-block; padding:4px 14px; border-radius:40px; background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.16); color:var(--accent); font-size:.76rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; margin-bottom:14px; }
.section-title { font-family:'Space Grotesk',sans-serif; font-size:clamp(1.9rem,3.5vw,2.8rem); font-weight:700; letter-spacing:-0.025em; color:var(--text); margin-bottom:12px; line-height:1.15; }
.section-sub { font-size:1rem; line-height:1.72; color:var(--text-muted); max-width:520px; margin:0 auto; }

/* Bento */
.bento-grid { display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:auto auto; gap:14px; }
.bento-card { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--r-lg); padding:30px; position:relative; overflow:hidden; cursor:default; transition:box-shadow .25s,transform .25s,border-color .25s; }
.bento-card:hover { box-shadow:var(--shadow-lg); transform:translateY(-3px); border-color:rgba(124,58,237,0.22); }
.b-lg { grid-column:span 2; }
.b-wide { grid-column:span 2; display:flex; align-items:center; gap:20px; flex-wrap:wrap; }
.b-wide .bento-wide-body { flex:1; min-width:180px; }
.bento-num { position:absolute; top:22px; right:22px; font-family:'Space Grotesk',sans-serif; font-size:3.2rem; font-weight:800; letter-spacing:-0.06em; color:var(--border); line-height:1; user-select:none; }
.bento-icon-wrap { width:52px; height:52px; border-radius:13px; display:flex; align-items:center; justify-content:center; margin-bottom:20px; }
.b-wide .bento-icon-wrap { margin-bottom:0; flex-shrink:0; }
.ic-violet{background:rgba(124,58,237,0.10);color:#7C3AED} .ic-pink{background:rgba(219,39,119,0.10);color:#DB2777}
.ic-emerald{background:rgba(16,185,129,0.10);color:#059669} .ic-amber{background:rgba(234,88,12,0.10);color:#EA580C}
.bento-card h3 { font-family:'Space Grotesk',sans-serif; font-size:1.12rem; font-weight:700; color:var(--text); margin-bottom:8px; letter-spacing:-0.01em; }
.bento-card p { font-size:.9rem; line-height:1.75; color:var(--text-muted); }
.bento-deco { position:absolute; bottom:-30px; right:-30px; pointer-events:none; }
.deco-ring { position:absolute; border-radius:50%; border:1px solid rgba(124,58,237,0.1); }
.r1{width:120px;height:120px;bottom:0;right:0} .r2{width:80px;height:80px;bottom:20px;right:20px}
.bento-pills { display:flex; gap:8px; flex-wrap:wrap; }
.pill { padding:4px 12px; border-radius:20px; font-size:.76rem; font-weight:700; }
.pill-violet{background:rgba(124,58,237,0.10);color:#6D28D9} .pill-amber{background:rgba(234,88,12,0.10);color:#C2410C} .pill-green{background:rgba(16,185,129,0.10);color:#047857}
.glass-card { background:linear-gradient(135deg,rgba(124,58,237,0.05),rgba(219,39,119,0.04)); border-color:rgba(124,58,237,0.14); }

/* Projects */
.loading-state { display:flex; flex-direction:column; align-items:center; gap:14px; padding:60px; }
.spinner { width:44px; height:44px; border:3px solid rgba(124,58,237,0.15); border-top-color:var(--accent); border-radius:50%; animation:spin .85s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }
.projects-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:20px; }
.project-card { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--r-lg); overflow:hidden; cursor:pointer; transition:transform .25s,box-shadow .25s,border-color .25s; }
.project-card:hover { transform:translateY(-5px); box-shadow:0 16px 50px rgba(124,58,237,0.14); border-color:rgba(124,58,237,0.2); }
.project-card:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.project-cover { height:168px; background:linear-gradient(135deg,#7C3AED,#DB2777); background-size:cover; background-position:center; display:flex; align-items:center; justify-content:center; position:relative; overflow:hidden; }
.cover-placeholder { display:flex; align-items:center; justify-content:center; width:100%; height:100%; color:rgba(255,255,255,0.55); }
.cover-overlay { position:absolute; inset:0; background:linear-gradient(to bottom,transparent 40%,rgba(0,0,0,0.22) 100%); }
.project-body { padding:20px; }
.project-badge { display:inline-block; padding:3px 10px; border-radius:20px; background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.15); color:var(--accent); font-size:.72rem; font-weight:700; letter-spacing:.03em; margin-bottom:8px; }
.project-name { font-family:'Space Grotesk',sans-serif; font-size:1.05rem; font-weight:700; color:var(--text); margin-bottom:6px; letter-spacing:-0.015em; }
.project-desc { font-size:.85rem; color:var(--text-muted); line-height:1.65; margin-bottom:14px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.project-action-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--r-sm); background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; font-size:.82rem; font-weight:600; font-family:'Archivo',sans-serif; border:none; cursor:pointer; transition:opacity .2s; }
.project-action-btn:hover { opacity:.88; }
.project-input-area { margin-top:4px; }
.hint-row { display:flex; gap:8px; align-items:center; }
.hint-input { flex:1; padding:9px 12px; border-radius:var(--r-sm); border:1.5px solid var(--border); background:var(--bg); color:var(--text); font-size:.85rem; font-family:'Archivo',sans-serif; outline:none; transition:border-color .2s; }
.hint-input:focus { border-color:var(--accent); }
.btn-sm { padding:9px 16px; border-radius:var(--r-sm); background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; font-weight:700; font-size:.84rem; font-family:'Archivo',sans-serif; border:none; cursor:pointer; white-space:nowrap; }
.btn-sm:disabled { opacity:.4; cursor:not-allowed; }
.hint-fade-enter-active,.hint-fade-leave-active { transition:opacity .2s; }
.hint-fade-enter-from,.hint-fade-leave-to { opacity:0; }
.empty-state { display:flex; flex-direction:column; align-items:center; gap:14px; padding:64px; color:var(--text-muted); font-size:.95rem; }

/* Gallery */
.gallery-grid { display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:repeat(2,200px); gap:12px; }
.gallery-item { border-radius:var(--r-md); overflow:hidden; position:relative; cursor:pointer; transition:transform .25s,box-shadow .25s; }
.gallery-item:hover { transform:scale(1.03); z-index:2; box-shadow:var(--shadow-lg); }
.gallery-item:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
@media (prefers-reduced-motion:reduce) { .gallery-item{transition:none} }
.gallery-shimmer { position:absolute; inset:0; background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,0.1) 50%,transparent 100%); background-size:200% 100%; }
@media (prefers-reduced-motion:no-preference) { .gallery-shimmer { animation:shim 3s ease-in-out infinite; } }
@keyframes shim { from{background-position:-200% center} to{background-position:200% center} }
.gallery-overlay { position:absolute; inset:0; background:linear-gradient(to top,rgba(0,0,0,0.74) 0%,transparent 55%); display:flex; flex-direction:column; justify-content:flex-end; padding:16px; opacity:0; transition:opacity .25s; }
.gallery-item:hover .gallery-overlay { opacity:1; }
.gallery-name { font-family:'Space Grotesk',sans-serif; color:#fff; font-weight:700; font-size:1rem; }
.gallery-sub { color:rgba(255,255,255,0.75); font-size:.78rem; margin-top:3px; }

/* CTA */
.cta-section { padding:60px 48px 88px; max-width:1160px; margin:0 auto; }
.cta-inner { position:relative; overflow:hidden; border-radius:var(--r-xl); border:1px solid rgba(124,58,237,0.18); background:linear-gradient(135deg,rgba(124,58,237,0.07) 0%,rgba(219,39,119,0.05) 60%,rgba(234,88,12,0.03) 100%); padding:70px 48px; text-align:center; }
.cta-glow { position:absolute; top:-80px; left:50%; transform:translateX(-50%); width:500px; height:300px; background:radial-gradient(ellipse,rgba(124,58,237,0.18) 0%,transparent 70%); pointer-events:none; }
.cta-content { position:relative; z-index:1; }
.cta-title { font-family:'Space Grotesk',sans-serif; font-size:clamp(2.2rem,4vw,3.2rem); font-weight:700; letter-spacing:-0.03em; color:var(--text); margin-bottom:12px; }
.cta-sub { color:var(--text-muted); font-size:1.05rem; margin-bottom:32px; }
.cta-input-row { justify-content:center; max-width:560px; margin:0 auto; }

/* Footer */
.site-footer { border-top:1px solid var(--border); padding:32px 48px; }
.footer-inner { display:flex; flex-direction:column; align-items:center; gap:10px; max-width:1160px; margin:0 auto; }
.footer-brand { display:flex; align-items:center; gap:8px; font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:.95rem; color:var(--text); }
.footer-text { color:var(--text-subtle); font-size:.82rem; }

/* Responsive */
@media (max-width:960px) {
  .navbar { width:calc(100% - 32px); }
  .nav-links { display:none; }
  .hero { padding:96px 28px 72px; }
  .hero-content { grid-template-columns:1fr; text-align:center; gap:48px; }
  .hero-left { align-items:center; }
  .hero-eyebrow { align-self:center; }
  .hero-desc { max-width:100%; }
  .hero-mosaic { max-width:420px; margin:0 auto; width:100%; }
  .stats-row { justify-content:center; }
  .scroll-hint { display:none; }
  .features-section,.projects-section,.gallery-section,.cta-section { padding:64px 28px; }
  .bento-grid { grid-template-columns:1fr; }
  .b-lg,.b-wide { grid-column:span 1; }
  .b-wide { flex-direction:column; align-items:flex-start; }
  .gallery-grid { grid-template-columns:repeat(2,1fr); grid-template-rows:repeat(3,180px); }
  .cta-inner { padding:48px 28px; }
}
@media (max-width:560px) {
  .hero-title { font-size:2.4rem; }
  .mosaic-grid { grid-template-rows:110px 110px; gap:8px; }
  .input-row { flex-direction:column; }
  .btn-primary { width:100%; justify-content:center; }
  .stats-row { gap:16px; }
  .stat-num { font-size:1.25rem; }
  .gallery-grid { grid-template-columns:1fr; grid-template-rows:repeat(6,160px); }
  .projects-grid { grid-template-columns:1fr; }
}
</style>