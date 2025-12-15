<script lang="ts" setup>
import { ref, watch } from 'vue'
import { IconCaretRightFilled } from '@tabler/icons-vue'

const props = defineProps<{
  title: string
  defaultExpanded?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:expanded', value: boolean): void
}>()

const collapsed = ref(!props.defaultExpanded)

watch(() => props.defaultExpanded, (newValue) => {
  if (newValue !== undefined) {
    collapsed.value = !newValue
  }
})

watch(collapsed, (newValue) => {
  emit('update:expanded', !newValue)
})

defineExpose({
  isExpanded: () => !collapsed.value,
  toggleExpanded: () => {
    collapsed.value = !collapsed.value
  }
})
</script>

<template>
  <Panel 
    class="collapsable-section" 
    toggleable 
    :collapsed="collapsed" 
    @update:collapsed="collapsed = $event"
    :style="{ border: 'none' }"
  >
    <template #header>
      <div class="flex items-center gap-2 w-full py-2 pr-2 border-b-1 border-auxiliar-gray">
        <div class="flex items-center gap-2 cursor-pointer flex-auto" @click.stop="collapsed = !collapsed">
          <IconCaretRightFilled :class="['w-4 h-4 transition-transform text-light-gray', { 'rotate-90': !collapsed }]" />
          <span class="text-base text-light-gray">{{ title }}</span>
        </div>
        <slot name="actions" />
      </div>
    </template>
    <template #toggleicon>
      <span></span>
    </template>
    <slot />
  </Panel>
</template>

<style scoped>
:deep(.p-panel-header) {
  padding: 0 !important;
}

:deep(.p-panel-toggle-button) {
  display: none !important;
}
</style>
