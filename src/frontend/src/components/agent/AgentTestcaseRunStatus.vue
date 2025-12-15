<script setup lang="ts">
import { IconSquareCheckFilled, IconSquareXFilled, IconExclamationMark, IconSquareChevronsRightFilled } from '@tabler/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  passed: number
  failed: number
  error: number
  skipped: number
}>()
</script>

<template>
  <div class="flex flex-row items-center gap-1">
    <div class="flex flex-row items-center gap-2 min-w-14" v-tooltip.bottom="t('passed')">
      <IconSquareCheckFilled class="text-success" />
      <span>{{ passed }}</span>
    </div>
    <div class="flex flex-row items-center gap-2 min-w-14" v-tooltip.bottom="t('failed')">
      <IconSquareXFilled class="text-error" />
      <span>{{ failed }}</span>
    </div>
    <div class="flex flex-row items-center gap-2 min-w-14" v-tooltip.bottom="t('error')">
      <IconExclamationMark class="text-white bg-warn rounded-sm p-0.5" size="20"/>
      <span>{{ error }}</span>
    </div>
    <div class="flex flex-row items-center gap-2 min-w-14" v-tooltip.bottom="t('skipped')">
      <IconSquareChevronsRightFilled class="text-light-gray" />
      <span>{{ skipped }}</span>
    </div>
  </div>
</template>

<i18n lang="json">
{
    "en": {
        "passed": "Passed",
        "failed": "Failed",
        "error": "Error",
        "skipped": "Skipped"
    },
    "es": {
        "passed": "Pasó",
        "failed": "Falló",
        "error": "Error",
        "skipped": "Omitido"
    }
}
</i18n>
