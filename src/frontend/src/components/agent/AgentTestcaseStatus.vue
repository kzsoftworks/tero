<script setup lang="ts">
import { computed } from 'vue'
import { IconLoader2, IconSquareCheckFilled, IconExclamationMark, IconSquareXFilled, IconClockPlay, IconSquareChevronsRightFilled } from '@tabler/icons-vue'
import { TestCaseResultStatus } from '@/services/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
    status?: TestCaseResultStatus
}>()

const statusConfig = computed(() => {
    switch (props.status) {
        case TestCaseResultStatus.RUNNING:
            return {
                icon: IconLoader2,
                label: t('running'),
                iconClass: 'text-light-gray animate-spin',
                size: undefined
            }
        case TestCaseResultStatus.SUCCESS:
            return {
                icon: IconSquareCheckFilled,
                label: t('success'),
                iconClass: 'text-success',
                size: undefined
            }
        case TestCaseResultStatus.ERROR:
            return {
                icon: IconExclamationMark,
                label: t('error'),
                iconClass: 'text-white bg-warn rounded-md p-0.5',
                size: 20
            }
        case TestCaseResultStatus.FAILURE:
            return {
                icon: IconSquareXFilled,
                label: t('failure'),
                iconClass: 'text-error',
                size: undefined
            }
        case TestCaseResultStatus.PENDING:
            return {
                icon: IconClockPlay,
                label: t('pending'),
                iconClass: 'text-light-gray',
                size: undefined
            }
        case TestCaseResultStatus.SKIPPED:
            return {
                icon: IconSquareChevronsRightFilled,
                label: t('skipped'),
                iconClass: 'text-light-gray',
                size: undefined
            }
        default:
            return null
    }
})
</script>

<template>
    <div v-if="statusConfig" class="flex flex-row items-center gap-2">
        <component :is="statusConfig.icon" :class="statusConfig.iconClass" :size="statusConfig.size" />
        <span>{{ statusConfig.label }}</span>
    </div>
</template>

<i18n lang="json">
{
    "en": {
        "running": "Running",
        "success": "Success",
        "failure": "Failed",
        "error": "Error running",
        "pending": "Pending",
        "skipped": "Skipped"
    },
    "es": {
        "running": "Ejecutando",
        "success": "Pasó",
        "failure": "Falló",
        "error": "Error al ejecutar",
        "pending": "Pendiente",
        "skipped": "Omitido"
    }
}
</i18n>
