<template>
  <div>
    <!-- 工具栏 -->
    <div class="toolbar">
      <span class="total-hint">共 {{ total }} 条</span>
      <button class="btn btn-primary" @click="openCreate">＋ 新建 Skill</button>
    </div>

    <!-- 表格 -->
    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>名称</th><th>类型</th><th>版本</th><th>状态</th>
            <th>创建时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="6" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="s in items" :key="s.id">
            <td>
              <div class="cell-name">{{ s.name }}</div>
              <div class="cell-sub">{{ s.description }}</div>
            </td>
            <td><span class="badge badge-queued">{{ s.type }}</span></td>
            <td>{{ s.version }}</td>
            <td>
              <span :class="s.enabled ? 'badge badge-enabled' : 'badge badge-disabled'">
                {{ s.enabled ? '启用' : '禁用' }}
              </span>
            </td>
            <td>{{ fmt(s.created_at) }}</td>
            <td class="action-cell">
              <button class="btn btn-secondary btn-sm" @click="openEdit(s)">编辑</button>
              <button v-if="s.enabled" class="btn btn-danger btn-sm" @click="handleDisable(s.id)">禁用</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= limit; load()">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="offset + limit >= total" @click="offset += limit; load()">下一页</button>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <Modal v-model="showModal" :title="editing ? '编辑 Skill' : '新建 Skill'" width="600px">
      <div class="form-grid">
        <div class="form-group">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="photo_restore" />
        </div>
        <div class="form-group">
          <label>类型 *</label>
          <select v-model="form.type">
            <option value="prompt">prompt</option>
            <option value="external_service">external_service</option>
            <option value="workflow">workflow</option>
            <option value="client_exec">client_exec</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>描述</label>
          <input v-model="form.description" placeholder="简短说明" />
        </div>
        <div class="form-group">
          <label>版本</label>
          <input v-model="form.version" placeholder="1.0.0" />
        </div>
        <div class="form-group">
          <label>启用</label>
          <select v-model="form.enabled">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>Prompt 模板</label>
          <textarea v-model="form.prompt_template" rows="4" placeholder="Prompt 文本…" />
        </div>
      </div>
      <p v-if="err" class="error-text">{{ err }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listSkills, createSkill, updateSkill, disableSkill, type Skill } from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<Skill[]>([])
const total = ref(0)
const limit = 20
const offset = ref(0)
const page = computed(() => Math.floor(offset.value / limit) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

const showModal = ref(false)
const editing = ref<Skill | null>(null)
const saving = ref(false)
const err = ref('')

const defaultForm = () => ({
  name: '', type: 'prompt', description: '', version: '1.0.0',
  prompt_template: '', enabled: true,
})
const form = ref(defaultForm())

async function load() {
  const r = await listSkills(limit, offset.value)
  items.value = r.items
  total.value = r.total
}

function openCreate() {
  editing.value = null
  form.value = defaultForm()
  err.value = ''
  showModal.value = true
}

function openEdit(s: Skill) {
  editing.value = s
  form.value = {
    name: s.name, type: s.type, description: s.description ?? '',
    version: s.version, prompt_template: '', enabled: s.enabled,
  }
  err.value = ''
  showModal.value = true
}

async function handleSave() {
  if (!form.value.name.trim()) { err.value = '名称不能为空'; return }
  saving.value = true; err.value = ''
  try {
    if (editing.value) {
      await updateSkill(editing.value.id, form.value)
    } else {
      await createSkill(form.value)
    }
    showModal.value = false
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    saving.value = false
  }
}

async function handleDisable(id: string) {
  if (!confirm('确认禁用此 Skill？')) return
  await disableSkill(id)
  await load()
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.total-hint { font-size: 0.85rem; color: #888; }
.cell-name { font-weight: 600; font-size: 0.88rem; }
.cell-sub { font-size: 0.77rem; color: #888; margin-top: 2px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.action-cell { display: flex; gap: 6px; white-space: nowrap; }
</style>
