<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { Dialog } from 'primevue'
import { useI18n } from 'vue-i18n'
import { IconHistory, IconX, IconTrash } from '@tabler/icons-vue'
import { ApiService, TestSuiteRun } from '@/services/api'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { AnimationEffect } from '../../../../common/src/utils/animations'
import moment from 'moment'

const props = defineProps<{
  agentId: number
}>()

const visible = defineModel<boolean>("visible")
const emit = defineEmits<{
  (e: 'selectExecution', suiteRun: TestSuiteRun): void
}>()

const { t } = useI18n()
const { handleError } = useErrorHandler()
const api = new ApiService()

const executions = ref<TestSuiteRun[]>([])
const isLoading = ref(false)
const deletingExecutionId = ref<number | null>(null)

const loadExecutions = async () => {
  isLoading.value = true
  executions.value = []

  try {
    executions.value = await api.findTestSuiteRuns(props.agentId, 100, 0)
  } catch (e) {
    handleError(e)
  } finally {
    isLoading.value = false
  }
}

const handleDeleteClick = (execution: TestSuiteRun, event: MouseEvent) => {
  event.stopPropagation()
  deletingExecutionId.value = execution.id
}

const handleConfirmDelete = async () => {
  if (!deletingExecutionId.value) return

  try {
    await api.deleteTestSuiteRun(props.agentId, deletingExecutionId.value)
    executions.value = executions.value.filter(execution => execution.id !== deletingExecutionId.value)
    deletingExecutionId.value = null
  } catch (e) {
    handleError(e)
  }
}

const handleCancelDelete = () => {
  deletingExecutionId.value = null
}

watch(visible, (isVisible) => {
  if (isVisible && props.agentId) {
    loadExecutions()
  }
})

onMounted(() => {
  if (visible.value && props.agentId) {
    loadExecutions()
  }
})
</script>

<template>
  <Dialog v-model:visible="visible" :modal="true" :draggable="false" :resizable="false" :closable="false" class="basic-dialog w-150">
    <FlexCard>
      <template #header>
        <div class="flex flex-row items-center justify-between">
          <div class="flex gap-2 items-center">
            <IconHistory />
            <span>{{ t('pastExecutionsTitle') }}</span>
          </div>
          <SimpleButton @click="visible = false">
            <IconX />
          </SimpleButton>
        </div>
      </template>
      <div class="flex flex-col gap-2 overflow-y-auto pb-4 max-h-[60vh] min-h-0">
        <div v-if="isLoading" class="animate-pulse space-y-2 flex flex-col gap-2 py-4">
          <div v-for="n in 6" :key="n" class="flex flex-col bg-auxiliar-gray rounded animate-pulse w-full h-10"></div>
        </div>
        <div v-else-if="executions.length === 0" class="flex flex-col items-center justify-center py-8 text-light-gray">
          <IconHistory size="48" class="mb-4 opacity-50" />
          <span>{{ t('noPastExecutions') }}</span>
        </div>
        <div v-else class="flex flex-col">
          <div v-for="(execution, index) in executions" :key="execution.id">
            <Animate v-if="deletingExecutionId === execution.id" :effect="AnimationEffect.QUICK_SLIDE_DOWN">
              <ItemConfirmation
                class="shadow-none !m-0"
                :tooltip="t('deleteConfirmDescription')"
                @confirm="handleConfirmDelete"
                @cancel="handleCancelDelete"
              />
            </Animate>
            <div
              v-else
              class="flex flex-row items-center justify-between px-4 py-2 cursor-pointer hover:bg-pale transition-colors rounded-lg"
              @click="emit('selectExecution', execution)"
            >
              <span>{{ moment(execution.executedAt).format('D MMM YYYY HH:mm') }}</span>
              <div class="flex flex-row items-center gap-4">
                  <div class="bg-white rounded-xl px-2 py-1">
                    <AgentTestcaseRunStatus
                      :passed="execution.passedTests"
                      :failed="execution.failedTests"
                      :error="execution.errorTests"
                      :skipped="execution.skippedTests"
                    />
                  </div>
                  <SimpleButton
                      @click="handleDeleteClick(execution, $event)"
                      shape="rounded"
                      class="ml-2"
                  >
                      <IconTrash size="16" />
                  </SimpleButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FlexCard>
  </Dialog>
</template>

<i18n lang="json">
{
  "en": {
    "pastExecutionsTitle": "Past Executions",
    "noPastExecutions": "No past executions found",
    "deleteConfirmDescription": "Delete execution?"
  },
  "es": {
    "pastExecutionsTitle": "Ejecuciones Pasadas",
    "noPastExecutions": "No se encontraron ejecuciones pasadas",
    "deleteConfirmDescription": "¿Eliminar ejecución?"
  }
}
</i18n>
