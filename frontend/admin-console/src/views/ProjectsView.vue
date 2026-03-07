<template>
  <div class="pv-wrap">
      <!-- Header -->
      <div class="pv-header">
        <div>
          <h1 class="pv-title">Projects</h1>
          <p class="pv-sub">管理项目及其选项配置</p>
        </div>
        <button class="btn-primary" @click="openCreate">+ 新建项目</button>
      </div>

      <!-- Table -->
      <div class="table-card">
        <div v-if="loading" class="table-loading">加载中…</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>名称</th><th>Slug</th><th>类型</th><th>绑定 Skill</th><th>状态</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in projects" :key="p.id">
              <td class="td-name">
                <div class="td-cover" :style="p.cover_url ? `background-image:url(${p.cover_url})` : ''">
                  <span v-if="!p.cover_url">🖼</span>
                </div>
                {{ p.name }}
              </td>
              <td><code class="slug-code">{{ p.slug }}</code></td>
              <td><span class="badge-type">{{ p.type }}</span></td>
              <td>
                <span v-if="p.skill_id" class="badge-skill">
                  {{ skills.find(s => s.id === p.skill_id)?.name ?? p.skill_id.slice(0,8) + '…' }}
                </span>
                <span v-else class="badge-none">未绑定</span>
              </td>
              <td>
                <span :class="p.enabled ? 'badge-on' : 'badge-off'">{{ p.enabled ? '启用' : '禁用' }}</span>
              </td>
              <td class="td-date">{{ fmtDate(p.created_at) }}</td>
              <td class="td-actions">
                <button class="btn-edit" @click="openEdit(p)">编辑</button>
                <button class="btn-del" @click="confirmDelete(p)">删除</button>
              </td>
            </tr>
            <tr v-if="!loading && !projects.length">
              <td colspan="6" class="td-empty">暂无项目，点击「新建项目」开始</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="modal" class="modal-backdrop">
      <div class="modal-box">
        <div class="modal-header">
          <h2>{{ isEdit ? '编辑项目' : '新建项目' }}</h2>
          <button class="modal-close" @click="modal = null">✕</button>
        </div>
        <div class="modal-body">
          <label class="field-label">项目名称 <span class="req">*</span></label>
          <input v-model="form.name" class="field-input" placeholder="例如：老照片修复" />

          <label class="field-label">Slug（URL 标识）<span class="req">*</span></label>
          <input v-model="form.slug" class="field-input" placeholder="例如：photo-restore" />

          <label class="field-label">描述</label>
          <textarea v-model="form.description" class="field-textarea" rows="2" placeholder="简短描述项目功能…" />

          <label class="field-label">封面图 URL</label>
          <input v-model="form.cover_url" class="field-input" placeholder="https://…" />

          <label class="field-label">类型</label>
          <select v-model="form.type" class="field-input">
            <option v-for="t in PROJECT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>

          <label class="field-label">绑定 Skill <span class="hint">&#40;该项目使用的技能&#41;</span></label>
          <select v-model="form.skill_id" class="field-input">
            <option :value="null">— 不绑定 —</option>
            <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>

          <label class="field-label">启用</label>
          <div class="toggle-row" @click="form.enabled = !form.enabled">
            <div class="toggle-switch" :class="{ on: form.enabled }"><div class="toggle-thumb"/></div>
            <span>{{ form.enabled ? '已启用' : '已禁用' }}</span>
          </div>

          <!-- ========== 选项配置可视化编辑器 ========== -->
          <div class="og-section">
            <div class="og-section-header">
              <span class="field-label" style="margin:0">选项配置</span>
              <button class="btn-add-group" @click="addOptionGroup">+ 添加选项组</button>
            </div>

            <div v-if="form.option_groups.length === 0" class="og-empty">
              暂无选项组，点击右侧「添加选项组」开始配置
            </div>

            <div v-for="(grp, gi) in form.option_groups" :key="gi" class="og-card">
              <!-- Group header row -->
              <div class="og-head">
                <input v-model="grp.icon" class="inp inp-icon" maxlength="4" placeholder="🎨" title="图标（emoji）" />
                <input v-model="grp.label" class="inp inp-label" placeholder="显示名称" />
                <select v-model="grp.type" class="inp sel-type">
                  <option value="toggle">开关 (toggle)</option>
                  <option value="single_choice">单选 (single_choice)</option>
                </select>
                <div class="og-btns">
                  <button class="icon-btn" :disabled="gi === 0" @click="moveGroup(gi, -1)" title="上移">↑</button>
                  <button class="icon-btn" :disabled="gi === form.option_groups.length - 1" @click="moveGroup(gi, 1)" title="下移">↓</button>
                  <button class="icon-btn danger" @click="removeOptionGroup(gi)" title="删除组">✕</button>
                </div>
              </div>

              <div class="og-body">
                <label class="sub-label">描述（展示在标题下方，可选）</label>
                <textarea v-model="grp.description" class="field-textarea sm-area" rows="2"
                  placeholder="例如：在不改变人物身份和照片质感的前提下增强清晰度。" />
              </div>

              <!-- Toggle body -->
              <div v-if="grp.type === 'toggle'" class="og-body">
                <div class="row-two">
                  <div class="field-col">
                    <label class="sub-label">默认值</label>
                    <div class="toggle-row" style="cursor:pointer" @click="grp.default = !grp.default">
                      <div class="toggle-switch" :class="{ on: grp.default }"><div class="toggle-thumb"/></div>
                      <span class="sub-label" style="margin:0">{{ grp.default ? '默认开启' : '默认关闭' }}</span>
                    </div>
                  </div>
                  <div class="field-col flex-1">
                    <label class="sub-label">开启时附加的提示词</label>
                    <textarea v-model="grp.prompt_addition" class="field-textarea sm-area" rows="2"
                      placeholder="例如：对图片进行高质量彩色化处理。" />
                  </div>
                </div>
              </div>

              <!-- Single choice body -->
              <div v-else-if="grp.type === 'single_choice'" class="og-body">
                <div class="choices-header">
                  <label class="sub-label">选项列表</label>
                  <button class="btn-add-choice" @click="addChoice(gi)">+ 添加选项</button>
                </div>

                <div class="choices-empty" v-if="grp.choices.length === 0">暂无选项，请点击「添加选项」</div>

                <div v-for="(ch, ci) in grp.choices" :key="ci" class="choice-card">
                  <div class="ch-row1">
                    <input v-model="ch.icon" class="inp inp-icon" maxlength="4" placeholder="🔧" title="图标（emoji）" />
                    <input v-model="ch.label" class="inp inp-label" placeholder="显示名称" />
                    <input v-model="ch.description" class="inp inp-desc" placeholder="描述（副标题，可选）" />
                    <div class="og-btns">
                      <button class="icon-btn" :disabled="ci === 0" @click="moveChoice(gi, ci, -1)" title="上移">↑</button>
                      <button class="icon-btn" :disabled="ci === grp.choices.length - 1" @click="moveChoice(gi, ci, 1)" title="下移">↓</button>
                      <button class="icon-btn danger" @click="removeChoice(gi, ci)" title="删除">✕</button>
                    </div>
                  </div>
                  <div class="ch-row2">
                    <label class="sub-label" style="white-space:nowrap">选中时附加提示词</label>
                    <textarea v-model="ch.prompt_addition" class="field-textarea sm-area" rows="1"
                      placeholder="例如：进行重度损伤修复。" />
                  </div>
                </div>

                <div class="og-default-row">
                  <label class="sub-label" style="white-space:nowrap">默认选中项</label>
                  <select v-model="grp.default" class="inp sel-type">
                    <option value="">-- 不设默认 --</option>
                    <option v-for="ch in grp.choices" :key="ch.id" :value="ch.id">
                      {{ ch.icon }} {{ ch.label || ch.id }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          <!-- ========== end 选项配置 ========== -->

          <p v-if="saveError" class="json-error">{{ saveError }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="modal = null">取消</button>
          <button class="btn-save" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : (isEdit ? '保存更改' : '创建项目') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Delete -->
    <div v-if="deleteTarget" class="modal-backdrop">
      <div class="modal-box modal-sm">
        <div class="modal-header">
          <h2>确认删除</h2>
          <button class="modal-close" @click="deleteTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p>确定要删除项目 <b>{{ deleteTarget.name }}</b>？关联的 Skills 将解除绑定。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="deleteTarget = null">取消</button>
          <button class="btn-del-confirm" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listProjects, createProject, updateProject, deleteProject, listSkills, type Project, type Skill } from '@/api/client'

// ── 项目类型枚举（后期拓展在此追加）────────────────────────────
const PROJECT_TYPES = [
  { value: 'image_processing', label: '图片处理' },
  { value: 'text_processing', label: '文本处理' },
] as const

// ── 选项配置数据类型 ─────────────────────────────────────────
interface Choice {
  id: string; label: string; icon: string; description: string; prompt_addition: string
}
interface OptionGroup {
  id: string; label: string; icon: string; description: string
  type: 'toggle' | 'single_choice'
  default: string | boolean
  prompt_addition: string   // for toggle
  choices: Choice[]         // for single_choice
}

function genId(prefix = 'opt'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 7)}`
}
function emptyGroup(): OptionGroup {
  return { id: genId('grp'), label: '', icon: '', description: '', type: 'toggle', default: false, prompt_addition: '', choices: [] }
}
function emptyChoice(): Choice {
  return { id: genId('ch'), label: '', icon: '', description: '', prompt_addition: '' }
}

// ── 解析已有 options JSON → OptionGroup[] ────────────────────
function parseOptions(raw: unknown): OptionGroup[] {
  if (!raw || typeof raw !== 'object') return []
  const data = raw as Record<string, unknown>
  const groups = data.option_groups
  if (!Array.isArray(groups)) return []
  return groups.map((g: unknown) => {
    const grp = g as Record<string, unknown>
    return {
      id: String(grp.id ?? ''),
      label: String(grp.label ?? ''),
      icon: String(grp.icon ?? ''),
      description: String(grp.description ?? ''),
      type: grp.type === 'single_choice' ? 'single_choice' : 'toggle',
      default: grp.type === 'single_choice' ? String(grp.default ?? '') : Boolean(grp.default),
      prompt_addition: String(grp.prompt_addition ?? ''),
      choices: Array.isArray(grp.choices)
        ? (grp.choices as Record<string, unknown>[]).map(c => ({
            id: String(c.id ?? ''),
            label: String(c.label ?? ''),
            icon: String(c.icon ?? ''),
            description: String(c.description ?? ''),
            prompt_addition: String(c.prompt_addition ?? ''),
          }))
        : [],
    }
  })
}

// ── 序列化 OptionGroup[] → JSON-ready object ─────────────────
function serializeOptions(groups: OptionGroup[]): Record<string, unknown> | undefined {
  if (!groups.length) return undefined
  return {
    option_groups: groups.map(g => {
      const base: Record<string, unknown> = {
        id: g.id, label: g.label, type: g.type, icon: g.icon || undefined,
      }
      if (g.description) base.description = g.description
      if (g.type === 'toggle') {
        base.default = g.default
        if (g.prompt_addition) base.prompt_addition = g.prompt_addition
      } else {
        base.default = g.default
        base.choices = g.choices.map(c => ({
          id: c.id, label: c.label,
          ...(c.icon ? { icon: c.icon } : {}),
          ...(c.description ? { description: c.description } : {}),
          ...(c.prompt_addition ? { prompt_addition: c.prompt_addition } : {}),
        }))
      }
      return base
    }),
  }
}

// ── 响应式状态 ───────────────────────────────────────────────
const projects = ref<Project[]>([])
const skills = ref<Skill[]>([])
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const modal = ref<'create' | 'edit' | null>(null)
const deleteTarget = ref<Project | null>(null)
const isEdit = ref(false)
const editingId = ref('')
const saveError = ref('')

const form = ref({
  name: '', slug: '', description: '', cover_url: '',
  type: 'image_processing', enabled: true,
  skill_id: null as string | null,
  option_groups: [] as OptionGroup[],
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [pr, sk] = await Promise.all([listProjects(), listSkills()])
    projects.value = pr.items
    skills.value = sk.items
  }
  catch { /* ignore */ }
  finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false
  form.value = { name: '', slug: '', description: '', cover_url: '', type: 'image_processing', enabled: true, skill_id: null, option_groups: [] }
  saveError.value = ''
  modal.value = 'create'
}

function openEdit(p: Project) {
  isEdit.value = true
  editingId.value = p.id
  form.value = {
    name: p.name, slug: p.slug,
    description: p.description ?? '',
    cover_url: p.cover_url ?? '',
    type: p.type,
    enabled: p.enabled,
    skill_id: p.skill_id ?? null,
    option_groups: parseOptions(p.options),
  }
  saveError.value = ''
  modal.value = 'edit'
}

async function save() {
  saveError.value = ''
  saving.value = true
  try {
    const body = {
      name: form.value.name,
      slug: form.value.slug,
      description: form.value.description || undefined,
      cover_url: form.value.cover_url || undefined,
      type: form.value.type,
      enabled: form.value.enabled,
      skill_id: form.value.skill_id || null,
      options: serializeOptions(form.value.option_groups),
    }
    if (isEdit.value) await updateProject(editingId.value, body)
    else await createProject(body)

    modal.value = null
    await load()
  } catch (e: unknown) { saveError.value = e instanceof Error ? e.message : '操作失败' }
  finally { saving.value = false }
}

function confirmDelete(p: Project) { deleteTarget.value = p }

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try { await deleteProject(deleteTarget.value.id); deleteTarget.value = null; await load() }
  catch { /* ignore */ }
  finally { deleting.value = false }
}

// ── 选项组操作 ───────────────────────────────────────────────
function addOptionGroup() { form.value.option_groups.push(emptyGroup()) }
function removeOptionGroup(i: number) { form.value.option_groups.splice(i, 1) }
function moveGroup(i: number, dir: -1 | 1) {
  const arr = form.value.option_groups
  const j = i + dir
  if (j < 0 || j >= arr.length) return;
  [arr[i], arr[j]] = [arr[j], arr[i]]
}

function addChoice(gi: number) { form.value.option_groups[gi].choices.push(emptyChoice()) }
function removeChoice(gi: number, ci: number) { form.value.option_groups[gi].choices.splice(ci, 1) }
function moveChoice(gi: number, ci: number, dir: -1 | 1) {
  const arr = form.value.option_groups[gi].choices
  const j = ci + dir
  if (j < 0 || j >= arr.length) return;
  [arr[ci], arr[j]] = [arr[j], arr[ci]]
}

function fmtDate(s: string) { return new Date(s).toLocaleDateString('zh-CN') }
</script>

<style scoped>
.pv-wrap { padding: 32px 36px; max-width: 1100px; margin: 0 auto; }
.pv-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }
.pv-title { font-size: 1.7rem; font-weight: 700; }
.pv-sub { color: #64748B; margin-top: 4px; font-size: 0.9rem; }
.btn-primary { padding: 10px 20px; background: linear-gradient(135deg,#8B5CF6,#EC4899); color: white; border: none; border-radius: 10px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.table-card { background: white; border-radius: 16px; box-shadow: 0 2px 16px rgba(0,0,0,0.06); overflow: hidden; }
.table-loading { padding: 40px; text-align: center; color: #94A3B8; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.87rem; }
.data-table th { padding: 13px 16px; text-align: left; background: #F8FAFC; color: #64748B; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #E2E8F0; }
.data-table td { padding: 13px 16px; border-bottom: 1px solid #F1F5F9; vertical-align: middle; color: #334155; }
.data-table tr:last-child td { border-bottom: none; }
.td-name { display: flex; align-items: center; gap: 10px; font-weight: 600; }
.td-cover { width: 36px; height: 36px; border-radius: 8px; background: linear-gradient(135deg,#8B5CF6,#EC4899); background-size: cover; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.slug-code { background: #F1F5F9; color: #7C3AED; padding: 2px 8px; border-radius: 6px; font-size: 0.82rem; font-family: monospace; }
.badge-type { background: #EDE9FE; color: #7C3AED; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.badge-on { background: #DCFCE7; color: #15803D; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.badge-off { background: #FEE2E2; color: #B91C1C; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.td-date { color: #94A3B8; font-size: 0.82rem; }
.td-actions { white-space: nowrap; }
.td-empty { text-align: center; color: #94A3B8; padding: 40px !important; }
.btn-edit { padding: 5px 12px; border-radius: 7px; border: 1.5px solid #E2E8F0; background: white; color: #475569; font-size: 0.8rem; font-weight: 600; cursor: pointer; margin-right: 6px; transition: border-color 0.15s; }
.btn-edit:hover { border-color: #8B5CF6; color: #8B5CF6; }
.btn-del { padding: 5px 12px; border-radius: 7px; border: 1.5px solid #FEE2E2; background: white; color: #EF4444; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-del:hover { background: #FEE2E2; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-box { background: white; border-radius: 20px; width: 100%; max-width: 780px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.modal-sm { max-width: 420px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 24px 28px 0; }
.modal-header h2 { font-size: 1.2rem; font-weight: 700; }
.modal-close { background: none; border: none; cursor: pointer; color: #94A3B8; font-size: 1.1rem; }
.modal-body { padding: 20px 28px; display: flex; flex-direction: column; gap: 12px; }
.modal-footer { padding: 16px 28px 24px; display: flex; justify-content: flex-end; gap: 10px; }
.field-label { font-size: 0.82rem; font-weight: 600; color: #475569; display: flex; align-items: center; justify-content: space-between; }
.req { color: #EF4444; }
.field-input { width: 100%; padding: 9px 12px; border: 1.5px solid #E2E8F0; border-radius: 9px; font-size: 0.9rem; outline: none; transition: border-color 0.15s; box-sizing: border-box; }
.field-input:focus { border-color: #8B5CF6; }
.field-textarea { width: 100%; padding: 9px 12px; border: 1.5px solid #E2E8F0; border-radius: 9px; font-size: 0.9rem; outline: none; resize: vertical; font-family: inherit; transition: border-color 0.15s; box-sizing: border-box; }
.field-textarea:focus { border-color: #8B5CF6; }
.json-error { color: #EF4444; font-size: 0.82rem; }
.toggle-row { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.toggle-switch { width: 44px; height: 24px; border-radius: 12px; background: #E2E8F0; position: relative; transition: background 0.2s; flex-shrink: 0; }
.toggle-switch.on { background: #8B5CF6; }
.toggle-thumb { position: absolute; top: 2px; left: 2px; width: 20px; height: 20px; background: white; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: transform 0.2s; }
.toggle-switch.on .toggle-thumb { transform: translateX(20px); }
.btn-cancel { padding: 9px 18px; border-radius: 9px; border: 1.5px solid #E2E8F0; background: white; color: #64748B; font-weight: 600; cursor: pointer; }
.btn-save { padding: 9px 22px; border-radius: 9px; background: linear-gradient(135deg,#8B5CF6,#EC4899); color: white; border: none; font-weight: 600; cursor: pointer; }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-del-confirm { padding: 9px 22px; border-radius: 9px; background: #EF4444; color: white; border: none; font-weight: 600; cursor: pointer; }
.btn-del-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.badge-skill { background: #DBEAFE; color: #1D4ED8; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.badge-none { color: #94A3B8; font-size: 0.82rem; }
.hint { color: #94A3B8; font-weight: 400; font-size: 0.78rem; margin-left: 4px; }

/* ── 选项配置编辑器 ── */
.og-section { background: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.og-section-header { display: flex; align-items: center; justify-content: space-between; }
.og-empty { text-align: center; color: #94A3B8; font-size: 0.85rem; padding: 16px 0; }
.btn-add-group { padding: 6px 14px; border-radius: 8px; border: 1.5px dashed #8B5CF6; background: white; color: #8B5CF6; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
.btn-add-group:hover { background: #EDE9FE; }

/* Option group card */
.og-card { background: white; border: 1.5px solid #E2E8F0; border-radius: 10px; overflow: hidden; }
.og-head { display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; flex-wrap: wrap; }
.og-body { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.og-btns { display: flex; gap: 4px; margin-left: auto; flex-shrink: 0; }

/* Shared compact input */
.inp { padding: 6px 9px; border: 1.5px solid #E2E8F0; border-radius: 7px; font-size: 0.82rem; outline: none; transition: border-color 0.15s; background: white; box-sizing: border-box; }
.inp:focus { border-color: #8B5CF6; }
.inp-icon { width: 46px; text-align: center; font-size: 1rem; padding: 4px 6px; }
.inp-id { width: 110px; font-family: monospace; color: #7C3AED; }
.inp-label { width: 130px; }
.inp-desc { flex: 1; min-width: 100px; }
.sel-type { width: 150px; cursor: pointer; }

/* Sub label */
.sub-label { font-size: 0.78rem; font-weight: 600; color: #64748B; }
.sm-area { font-size: 0.85rem; padding: 7px 10px; }

/* Toggle body two-column */
.row-two { display: flex; gap: 16px; align-items: flex-start; }
.field-col { display: flex; flex-direction: column; gap: 6px; }
.flex-1 { flex: 1; }

/* Choices */
.choices-header { display: flex; align-items: center; justify-content: space-between; }
.choices-empty { text-align: center; color: #94A3B8; font-size: 0.82rem; padding: 8px 0; }
.choices-list { display: flex; flex-direction: column; gap: 8px; }
.btn-add-choice { padding: 4px 12px; border-radius: 7px; border: 1.5px dashed #CBD5E1; background: white; color: #64748B; font-size: 0.78rem; font-weight: 600; cursor: pointer; }
.btn-add-choice:hover { border-color: #8B5CF6; color: #8B5CF6; }
.choice-card { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 6px; }
.ch-row1 { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ch-row2 { display: flex; align-items: flex-start; gap: 8px; }
.og-default-row { display: flex; align-items: center; gap: 10px; padding-top: 4px; }

/* Icon buttons */
.icon-btn { width: 26px; height: 26px; border-radius: 6px; border: 1.5px solid #E2E8F0; background: white; color: #64748B; font-size: 0.78rem; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; transition: border-color 0.15s, color 0.15s; }
.icon-btn:hover:not(:disabled) { border-color: #8B5CF6; color: #8B5CF6; }
.icon-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.icon-btn.danger:hover:not(:disabled) { border-color: #EF4444; color: #EF4444; }
</style>
