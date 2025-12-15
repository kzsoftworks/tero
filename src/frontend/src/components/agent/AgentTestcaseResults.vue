<script lang="ts" setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { TestCaseResultStatus, TestSuiteRunStatus, TestCaseResult } from '@/services/api'
import moment from 'moment'
import { useTestExecutionStore } from '@/composables/useTestExecutionStore'
import { useErrorHandler } from '@/composables/useErrorHandler'

const emit = defineEmits<{
    (e: 'closeResults'): void
}>()

const { t } = useI18n()
const {
    testExecutionStore,
    setSelectedResult,
    stopSuiteRun
} = useTestExecutionStore()
const { handleError } = useErrorHandler()

const isLoading = computed(() => {
    return testExecutionStore.selectedSuiteRun !== undefined && testExecutionStore.testCaseResults.length === 0
})

const countResultWithStatus = (status: TestCaseResultStatus) => {
    return testExecutionStore.testCaseResults.filter((result) => result.status === status).length || 0
}

const handleResultClick = (result: TestCaseResult) => {
    setSelectedResult(result)
}

const handleStopSuiteRun = async () => {
    try {
        await stopSuiteRun()
    } catch (error) {
        handleError(error)
    }
}
</script>

<template>
    <AgentTestcaseResultsSkeleton v-if="isLoading" />
    <div v-else class="flex flex-col gap-2 h-full">
        <div class="flex justify-between items-center">
            <div v-if="testExecutionStore.selectedSuiteRun" class="flex justify-between items-center flex-1 px-2 py-2">
                <span v-if="testExecutionStore.selectedSuiteRun?.status === TestSuiteRunStatus.RUNNING"
                    v-html="t('running')"></span>
                <span v-else
                    v-html="t('runResultTitle', { date: testExecutionStore.selectedSuiteRun?.executedAt ? moment(testExecutionStore.selectedSuiteRun?.executedAt).format('D MMM YYYY HH:mm') : '' })"></span>
                <AgentTestcaseRunStatus class="bg-pale rounded-xl px-2 py-1"
                    :passed="countResultWithStatus(TestCaseResultStatus.SUCCESS)"
                    :failed="countResultWithStatus(TestCaseResultStatus.FAILURE)"
                    :error="countResultWithStatus(TestCaseResultStatus.ERROR)"
                    :skipped="countResultWithStatus(TestCaseResultStatus.SKIPPED)" />
            </div>
            <div class="flex flex-row items-center gap-2">
                <SimpleButton
                    v-if="testExecutionStore.selectedSuiteRun?.status === TestSuiteRunStatus.RUNNING"
                    shape="square"
                    size="small"
                    :disabled="testExecutionStore.isStoppingSuite"
                    @click="handleStopSuiteRun"
                >
                    <IconPlayerStop size="20" />
                    {{ t('stopSuiteRun') }}
                </SimpleButton>
                <SimpleButton
                    v-if="testExecutionStore.selectedSuiteRun?.status !== TestSuiteRunStatus.RUNNING"
                    @click="$emit('closeResults')"
                >
                    <IconX />
                </SimpleButton>
            </div>
        </div>
        <div class="flex flex-col gap-2 min-h-0 overflow-y-auto">
            <div v-for="result in testExecutionStore.testCaseResults" :key="result.testCaseId">
                <div class="border-1 border-auxiliar-gray rounded-xl px-3 py-2 cursor-pointer shadow-xs group h-[50px]"
                    @click="handleResultClick(result)"
                    :class="{ '!border-abstracta': testExecutionStore.selectedResult?.testCaseId === result.testCaseId }">
                    <div class="flex items-center justify-between h-full">
                        <span class="flex-1">{{ result.testCaseName }}</span>
                        <div class="flex flex-row items-center gap-2">
                            <AgentTestcaseStatus :status="result.status" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<i18n lang="json">
{
    "en": {
        "running": "Running...",
        "runResultTitle": "Results from {'<'}b>{date}{'<'}/b>",
        "stopSuiteRun": "Stop"
    },
    "es": {
        "running": "Ejecutando...",
        "runResultTitle": "Resultados de {'<'}b>{date}{'<'}/b>",
        "stopSuiteRun": "Detener"
    }
}
</i18n>
