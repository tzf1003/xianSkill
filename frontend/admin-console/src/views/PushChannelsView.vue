<template>
  <div>
    <div class="toolbar">
      <span class="total-hint">共 {{ total }} 条</span>
      <button class="btn btn-primary" @click="openCreate">＋ 新增推送途径</button>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>名称</th><th>类型</th><th>BASEURL</th><th>状态</th><th>创建时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="items.length === 0">
            <td colspan="6" class="empty-row">暂无数据</td>
          </tr>
          <tr v-for="item in items" :key="item.id">
            <td><b>{{ item.name }}</b></td>
            <td>{{ item.provider.toUpperCase() }}</td>
            <td><span class="url-text">{{ item.base_url }}</span></td>
            <td><span :class="item.enabled ? 'badge badge-enabled' : 'badge badge-disabled'">{{ item.enabled ? '启用' : '禁用' }}</span></td>
            <td>{{ fmt(item.created_at) }}</td>
            <td class="actions-cell">
              <button class="btn btn-secondary btn-sm" @click="openEdit(item)">编辑</button>
              <button class="btn btn-secondary btn-sm" @click="openTest(item)">测试</button>
              <button class="btn btn-danger btn-sm" @click="handleDelete(item.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? '编辑推送途径' : '新增推送途径'">
      <div class="form-grid">
        <div class="form-group">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="Bark 主通道" />
        </div>
        <div class="form-group">
          <label>类型</label>
          <select v-model="form.provider">
            <option value="bark">Bark</option>
          </select>
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model="form.enabled">
            <option :value="true">启用</option>
            <option :value="false">禁用</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>BASEURL *</label>
          <input v-model="form.base_url" placeholder="https://api.day.app/你的设备Key" />
          <small class="field-hint">当前仅支持 Bark。支持直接填写 Bark 设备地址，或以 /push 结尾的接口地址。</small>
        </div>
      </div>
      <p v-if="err" class="error-text">{{ err }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showModal = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleSave">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </Modal>

    <Modal v-model="showTestModal" title="推送测试">
      <div class="form-grid">
        <div class="form-group" style="grid-column:1/-1">
          <label>测试标题 *</label>
          <input v-model="testForm.title" placeholder="测试标题" />
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>测试推送内容 *</label>
          <textarea v-model="testForm.body" rows="5" placeholder="测试推送内容" />
        </div>
      </div>
      <p v-if="testErr" class="error-text">{{ testErr }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showTestModal = false">取消</button>
        <button class="btn btn-primary" :disabled="testing" @click="handleTest">{{ testing ? '发送中…' : '发送测试' }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createPushChannel,
  deletePushChannel,
  listPushChannels,
  testPushChannel,
  updatePushChannel,
  type PushChannel,
} from '@/api/client'
import Modal from '@/components/Modal.vue'

const items = ref<PushChannel[]>([])
const total = ref(0)

const showModal = ref(false)
const editing = ref<PushChannel | null>(null)
const saving = ref(false)
const err = ref('')

const showTestModal = ref(false)
const testingTarget = ref<PushChannel | null>(null)
const testing = ref(false)
const testErr = ref('')

const defaultForm = () => ({ name: '', provider: 'bark', base_url: '', enabled: true })
const form = ref(defaultForm())
const testForm = ref({ title: '测试标题', body: '测试推送内容' })

async function load() {
  const result = await listPushChannels(200)
  items.value = result.items
  total.value = result.total
}

function openCreate() {
  editing.value = null
  form.value = defaultForm()
  err.value = ''
  showModal.value = true
}

function openEdit(item: PushChannel) {
  editing.value = item
  form.value = {
    name: item.name,
    provider: item.provider,
    base_url: item.base_url,
    enabled: item.enabled,
  }
  err.value = ''
  showModal.value = true
}

function openTest(item: PushChannel) {
  testingTarget.value = item
  testForm.value = { title: '测试标题', body: '测试推送内容' }
  testErr.value = ''
  showTestModal.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.base_url.trim()) {
    err.value = '名称和 BASEURL 不能为空'
    return
  }
  saving.value = true
  err.value = ''
  try {
    if (editing.value) await updatePushChannel(editing.value.id, form.value)
    else await createPushChannel(form.value)
    showModal.value = false
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  if (!testingTarget.value) return
  if (!testForm.value.title.trim() || !testForm.value.body.trim()) {
    testErr.value = '测试标题和测试推送内容不能为空'
    return
  }
  testing.value = true
  testErr.value = ''
  try {
    await testPushChannel(testingTarget.value.id, testForm.value)
    showTestModal.value = false
  } catch (e: unknown) {
    testErr.value = e instanceof Error ? e.message : '测试推送失败'
  } finally {
    testing.value = false
  }
}

async function handleDelete(id: string) {
  if (!window.confirm('确认删除该推送途径吗？')) return
  await deletePushChannel(id)
  await load()
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.actions-cell { display: flex; gap: 6px; align-items: center; }
.url-text {
  display: inline-block;
  max-width: 360px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}
.field-hint { display: block; margin-top: 6px; color: var(--text-muted); font-size: .82rem; line-height: 1.5; }
</style>