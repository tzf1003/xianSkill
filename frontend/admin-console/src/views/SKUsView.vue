<template>
  <div>
    <div class="toolbar">
      <span class="total-hint">共 {{ total }} 条</span>
      <button class="btn btn-primary" @click="openCreate">＋ 新建 SKU</button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>名称</th><th>Skill ID</th><th>价格（分）</th>
            <th>次数</th><th>交付模式</th><th>状态</th><th>创建时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="8" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="s in items" :key="s.id">
            <td><b>{{ s.name }}</b></td>
            <td><code class="tiny">{{ s.skill_id.slice(0,8) }}…</code></td>
            <td>{{ s.price_cents }}</td>
            <td>{{ s.total_uses }}</td>
            <td><span :class="'badge badge-' + s.delivery_mode">{{ s.delivery_mode }}</span></td>
            <td><span :class="s.enabled ? 'badge badge-enabled' : 'badge badge-disabled'">{{ s.enabled ? '启用' : '禁用' }}</span></td>
            <td>{{ fmt(s.created_at) }}</td>
            <td><button class="btn btn-secondary btn-sm" @click="openEdit(s)">编辑</button></td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= 20; load()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="offset + 20 >= total" @click="offset += 20; load()">下一页</button>
      </div>
    </div>

    <Modal v-model="showModal" :title="editing ? '编辑 SKU' : '新建 SKU'">
      <div class="form-grid">
        <div class="form-group" style="grid-column:1/-1">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="高级修复套餐" />
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>Skill ID *</label>
          <select v-model="form.skill_id">
            <option value="">— 选择 Skill —</option>
            <option v-for="sk in skills" :key="sk.id" :value="sk.id">{{ sk.name }}</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>所属项目</label>
          <select v-model="form.project_id">
            <option :value="null">— 不绑定项目 —</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>价格（分）</label>
          <input v-model.number="form.price_cents" type="number" min="0" />
        </div>
        <div class="form-group">
          <label>次数</label>
          <input v-model.number="form.total_uses" type="number" min="1" />
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>交付模式</label>
          <select v-model="form.delivery_mode">
            <option value="auto">auto（自动）</option>
            <option value="human">human（人工）</option>
          </select>
        </div>
      </div>
      <p v-if="err" class="error-text">{{ err }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleSave">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listSKUs, createSKU, updateSKU, listSkills as apiListSkills, listProjects, type SKU, type Skill, type Project } from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<SKU[]>([])
const skills = ref<Skill[]>([])
const projects = ref<Project[]>([])
const total = ref(0)
const offset = ref(0)
const page = computed(() => Math.floor(offset.value / 20) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))

const showModal = ref(false)
const editing = ref<SKU | null>(null)
const saving = ref(false)
const err = ref('')

const defaultForm = () => ({ name: '', skill_id: '', project_id: null as string | null, price_cents: 0, total_uses: 1, delivery_mode: 'auto' })
const form = ref(defaultForm())

async function load() {
  const [r, s, p] = await Promise.all([listSKUs(undefined, 20, offset.value), apiListSkills(200), listProjects(200)])
  items.value = r.items; total.value = r.total; skills.value = s.items; projects.value = p.items
}

function openCreate() { editing.value = null; form.value = defaultForm(); err.value = ''; showModal.value = true }
function openEdit(s: SKU) {
  editing.value = s
  form.value = { name: s.name, skill_id: s.skill_id, project_id: s.project_id ?? null, price_cents: s.price_cents, total_uses: s.total_uses, delivery_mode: s.delivery_mode }
  err.value = ''; showModal.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.skill_id) { err.value = '名称和 Skill 不能为空'; return }
  saving.value = true; err.value = ''
  try {
    if (editing.value) await updateSKU(editing.value.id, form.value)
    else await createSKU(form.value as { skill_id: string; name: string; price_cents: number; delivery_mode: string; total_uses: number; project_id?: string | null })
    showModal.value = false; await load()
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : '操作失败' }
  finally { saving.value = false }
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.tiny { font-size: .75rem; font-family: monospace; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
</style>
