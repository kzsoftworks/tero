<script lang="ts" setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Agent, TestCase } from '@/services/api'
import { IconPencil, IconTrash, IconPlayerPlay, IconPlus, IconHistory, IconSettings, IconCopyPlus } from '@tabler/icons-vue'
import { AnimationEffect } from '../../../../common/src/utils/animations'
import AgentAvatar from './AgentAvatar.vue'
import SimpleMenu from '../common/SimpleMenu.vue'
import { useTestCaseStore } from '@/composables/useTestCaseStore'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { ApiService, Evaluator } from '@/services/api'

const props = defineProps<{
    agent?: Agent
}>()

const emit = defineEmits<{
    (e: 'runTestCase', testCaseThreadId: number): void
    (e: 'runTests'): void
    (e: 'showPastExecutions'): void
    (e: 'testCaseDeleted'): void
    (e: 'configureEvaluator'): void
}>()

const { t } = useI18n()
const { handleError } = useErrorHandler()
const api = new ApiService()
const { testCasesStore, deleteTestCase, updateTestCase, addTestCase, cloneTestCase } = useTestCaseStore()

const deletingTestCaseId = ref<number | null>(null)
const renamingTestCaseId = ref<number | null>(null)
const evaluatorTestCaseId = ref<number>()

const showEvaluatorModal = ref<boolean>(false)


const onDeleteTestCase = (testCase: TestCase) => {
    deletingTestCaseId.value = testCase.thread.id
}

const onRenameTestCase = (testCase: TestCase) => {
    renamingTestCaseId.value = testCase.thread.id
}

const onConfirmDeleteTestCase = async () => {
    if (deletingTestCaseId.value && props.agent?.id) {
        try {
            await deleteTestCase(props.agent.id, deletingTestCaseId.value)
            emit('testCaseDeleted')
            deletingTestCaseId.value = null
        } catch (error) {
            handleError(error)
        }
    }
}

const onCancelDeleteTestCase = () => {
    deletingTestCaseId.value = null
}

const onSaveTestCaseName = async (newName: string) => {
    try {
        await updateTestCase(props.agent!.id, renamingTestCaseId.value!, newName)
        renamingTestCaseId.value = null
    } catch (error) {
        handleError(error)
    }
}

const onCancelRenameTestCase = () => {
    renamingTestCaseId.value = null
}

const onNewTestCase = async () => {
    try {
        const testCase = await addTestCase(props.agent?.id!)
        testCasesStore.setSelectedTestCase(testCase)
    } catch (e) {
        handleError(e)
    }
}

const handleConfigureEvaluator = (evalTestCaseId?: number) => {
  evaluatorTestCaseId.value = evalTestCaseId
  showEvaluatorModal.value = true
}

const handleSaveEvaluator = async (evaluator: Evaluator) => {
  try {
    if (evaluatorTestCaseId.value) {
      await api.saveTestCaseEvaluator(props.agent!.id!, evaluatorTestCaseId.value!, evaluator)
    } else {
      await api.saveAgentEvaluator(props.agent!.id!, evaluator)
    }
  } catch (error) {
    handleError(error)
  }
}

const onCloneTestCase = async (testCase: TestCase) => {
    try {
        const clonedTestCase = await cloneTestCase(props.agent!.id, testCase.thread.id)
        testCasesStore.setSelectedTestCase(clonedTestCase)
    } catch (error) {
        handleError(error)
    }
}
</script>

<template>
    <div v-if="!testCasesStore.testCases.length" class="flex flex-col gap-2">
        <span class="font-bold">{{ t('noTestCasesTitle') }}</span>
        <span class="">{{ t('noTestCasesDescription') }}</span>
    </div>
    <div v-else class="flex flex-col gap-6 h-full pb-4">
        <div class="flex justify-between items-center">
            <div class="flex flex-row items-center gap-2">
                <AgentAvatar v-if="agent" :agent="agent" :desaturated="true" />
                <div>{{ agent?.name }}</div>
            </div>
            <div class="flex flex-row items-center gap-2">
                <SimpleButton v-if="testCasesStore.testCases.length" shape="square" size="small"
                    @click="$emit('runTests')">
                    <IconPlayerPlay size="20" />
                    {{ t('runTestsButton') }}
                </SimpleButton>
                <SimpleButton shape="square" size="small" @click="onNewTestCase">
                    <IconPlus size="20" />
                    {{ t('newTestCaseButton') }}
                </SimpleButton>
                <SimpleMenu :items="[
                    {
                        label: t('pastExecutions'),
                        tablerIcon: IconHistory,
                        command: () => $emit('showPastExecutions')
                    },
                    {
                        label: t('configureEvaluator'),
                        tablerIcon: IconSettings,
                        command: () => handleConfigureEvaluator(),
                    }
                ]" />
            </div>
        </div>
        <div class="flex flex-col gap-2 min-h-0 overflow-y-auto">
            <div v-for="testCase in testCasesStore.testCases" :key="testCase.thread.id">
                <Animate v-if="deletingTestCaseId === testCase.thread.id" :effect="AnimationEffect.QUICK_SLIDE_DOWN">
                    <ItemConfirmation class="shadow-none !m-0"
                        :tooltip="t('deleteTestCaseConfirmation', { testCaseName: testCase.thread.name })"
                        @confirm="onConfirmDeleteTestCase" @cancel="onCancelDeleteTestCase" />
                </Animate>
                <Animate v-else-if="renamingTestCaseId === testCase.thread.id"
                    :effect="AnimationEffect.QUICK_SLIDE_DOWN" class="w-full">
                    <SidebarEditor :value="testCase.thread.name" :on-save="onSaveTestCaseName"
                        :on-cancel="onCancelRenameTestCase" class="w-full" />
                </Animate>
                <div v-else
                    class="border-1 border-auxiliar-gray rounded-xl px-3 py-2 cursor-pointer shadow-xs group h-[50px]"
                    @click="testCasesStore.setSelectedTestCase(testCase)"
                    :class="{ '!border-abstracta': testCasesStore.selectedTestCase?.thread.id === testCase.thread.id }">
                    <div class="flex items-center justify-between h-full">
                        <span class="flex-1">{{ testCase.thread.name }}</span>
                        <div class="flex flex-row items-center gap-2">
                            <SimpleMenu :items="[
                                {
                                    label: t('runTestCaseMenuItem'),
                                    tablerIcon: IconPlayerPlay,
                                    command: () => emit('runTestCase', testCase.thread.id),
                                },
                                {
                                    label: t('renameTestCaseTooltip'),
                                    tablerIcon: IconPencil,
                                    command: () => onRenameTestCase(testCase)
                                },
                                {
                                    label: t('cloneTestCaseTooltip'),
                                    tablerIcon: IconCopyPlus,
                                    command: () => onCloneTestCase(testCase)
                                },
                                {
                                    label: t('configureTestEvaluator'),
                                    tablerIcon: IconSettings,
                                    command: () => handleConfigureEvaluator(testCase.thread.id),
                                },
                                {
                                    label: t('deleteTestCaseTooltip'),
                                    tablerIcon: IconTrash,
                                    command: () => onDeleteTestCase(testCase)
                                }
                            ]" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <EvaluatorConfigurationModal
        v-model:show-modal="showEvaluatorModal"
        :agent-id="agent?.id!"
        :test-case-id="evaluatorTestCaseId"
        :test-case-name="evaluatorTestCaseId ? testCasesStore.testCases.find(tc => tc.thread.id === evaluatorTestCaseId)?.thread.name : undefined"
        @save="handleSaveEvaluator"
    />
</template>

<i18n lang="json">
{
    "en": {
        "newTestCaseButton": "Add",
        "renameTestCaseTooltip": "Rename",
        "cloneTestCaseTooltip": "Clone",
        "deleteTestCaseTooltip": "Delete",
        "deleteTestCaseConfirmation": "Delete {testCaseName}?",
        "runTestCaseMenuItem": "Run",
        "runTestsButton": "Run all",
        "pastExecutions": "Past Executions",
        "noTestCasesTitle": "You don't have test cases for this agent yet",
        "noTestCasesDescription": "Create your first test case to validate that the agent meets the expected requirements.",
        "configureEvaluator": "Configure agent evaluator",
        "configureTestEvaluator": "Configure test evaluator"
    },
    "es": {
        "newTestCaseButton": "Agregar",
        "renameTestCaseTooltip": "Renombrar",
        "cloneTestCaseTooltip": "Clonar",
        "deleteTestCaseTooltip": "Eliminar",
        "deleteTestCaseConfirmation": "¿Eliminar {testCaseName}?",
        "runTestCaseMenuItem": "Ejecutar",
        "runTestsButton": "Ejecutar todos",
        "pastExecutions": "Ejecuciones pasadas",
        "noTestCasesTitle": "Aún no tienes test cases para este agente",
        "noTestCasesDescription": "Crea tu primer test case para validar que el agente cumple los requisitos esperados.",
        "configureEvaluator": "Configurar evaluador del agente",
        "configureTestEvaluator": "Configurar evaluador del test"
    }
}
</i18n>
