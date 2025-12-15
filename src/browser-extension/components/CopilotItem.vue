<script lang="ts" setup>
import { Agent } from '~/utils/agent'

defineProps<{ agent: Agent }>()
defineEmits<{
  (e: 'activate', agentId: string): void
}>()
</script>

<template>
  <div class="flex flex-row flex-auto self-center items-center cursor-pointer gap-2 min-w-0" @click="$emit('activate', agent.manifest.id!)">
    <div class="w-7 h-7 flex flex-row items-center rounded-full overflow-hidden flex-shrink-0">
      <img :src="agent.logo" class="w-full h-full object-contain m-0" />
    </div>
    <div class="text-lg font-medium truncate min-w-0">
      {{ agent.manifest.name! }}
    </div>
  </div>
</template>
