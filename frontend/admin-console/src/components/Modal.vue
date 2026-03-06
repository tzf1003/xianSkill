<template>
  <teleport to="body">
    <div v-if="modelValue" class="modal-overlay">
      <div class="modal-box" :style="{ width: width }">
        <div class="modal-header">
          <span class="modal-title">{{ title }}</span>
          <button class="modal-close" @click="$emit('update:modelValue', false)">✕</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div v-if="$slots.footer" class="modal-footer">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean; title: string; width?: string }>()
defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-box {
  background: #fff; border-radius: 12px; width: 520px; max-width: 95vw;
  max-height: 90vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px 14px; border-bottom: 1px solid #eee;
}
.modal-title { font-size: 1rem; font-weight: 700; }
.modal-close { background: none; border: none; font-size: 1rem; cursor: pointer; color: #888; }
.modal-body { padding: 20px 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
.modal-footer { padding: 14px 24px 18px; border-top: 1px solid #eee; display: flex; gap: 10px; justify-content: flex-end; }
</style>
