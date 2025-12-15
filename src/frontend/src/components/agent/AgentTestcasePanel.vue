<script setup lang="ts">
import { TestCase, ThreadMessage, ThreadMessageOrigin, TestCaseResultStatus, TestSuiteRunStatus, TestCaseNewThreadMessage, TestCaseThreadMessageUpdate } from '@/services/api';
import { useI18n } from 'vue-i18n';
import { onMounted, ref, watch, computed, nextTick } from 'vue';
import { ApiService, HttpError } from '@/services/api';
import { AgentTestcaseChatUiMessage } from './AgentTestcaseChatMessage.vue';
import ChatInput from '../../../../common/src/components/chat/ChatInput.vue';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { AnimationEffect } from '../../../../common/src/utils/animations';
import { useTestExecutionStore } from '@/composables/useTestExecutionStore';
import { useTestCaseStore } from '@/composables/useTestCaseStore';
import { IconArrowLeft, IconPencil, IconLoader2 } from '@tabler/icons-vue';

const api = new ApiService()
const { t } = useI18n()
const { handleError } = useErrorHandler()
const { testExecutionStore } = useTestExecutionStore()
const { testCasesStore, addTestCase, setSelectedTestCase, refreshTestCase } = useTestCaseStore()

const props = defineProps<{
    agentId: number,
    threadId?: number,
    isEditing?: boolean,
    isNewTestCase?: boolean
}>()

const emit = defineEmits<{
    (e: 'showEdit'): void
    (e: 'compareResultWithTestSpecStateChanged', isComparingResultWithTestSpec: boolean): void
}>()

const messages = ref<AgentTestcaseChatUiMessage[]>([])
const testSpecMessages = ref<AgentTestcaseChatUiMessage[]>([])
const inputText = ref('')
const selectedMessage = ref<AgentTestcaseChatUiMessage | undefined>()
const chatInputRef = ref<InstanceType<typeof ChatInput>>()
const isLoading = ref(false)
const isComparingResultWithTestSpec = ref(false)
const isRunning = computed(() => {
    if (executionState.value) {
        return executionState.value.phase === 'executing' || executionState.value.phase === 'evaluating'
    }
    return testCaseResult.value?.status === TestCaseResultStatus.RUNNING
})
const testCase = computed(() => testCasesStore.selectedTestCase)
const testCaseId = computed(() => testCase.value?.thread.id)
const testCaseResult = computed(() => { return testExecutionStore.selectedResult })
const testCaseResultTest = computed(() => {
    return testCaseResult.value ? testCasesStore.testCases.find(tc => tc.thread.id === testCaseResult.value!.testCaseId) : undefined
})
const executionState = computed(() => {
    return testCaseResult.value?.id ? testExecutionStore.getExecutionState(testCaseResult.value.id) : undefined
})

onMounted(async () => {
    isLoading.value = true
    try {
        if (testCaseId.value) {
            await loadTestCaseData()
        } else if (props.isNewTestCase) {
            messages.value = [
                new AgentTestcaseChatUiMessage(t('userMessagePlaceholder'), true, true),
                new AgentTestcaseChatUiMessage(t('agentMessagePlaceholder'), false, true),
            ]
            await selectNextMessageOrPlaceholder()
        }
    } finally {
        isLoading.value = false
    }
})

const loadTestCaseData = async () => {
    isLoading.value = true
    try {
        if (props.isEditing) {
            try {
                messages.value = mapMessagesToAgentTestcaseChatUi(await api.findTestCaseMessages(props.agentId, testCaseId.value!))
            } catch (error) {
                handleError(error)
            }
            await selectNextMessageOrPlaceholder()
        } else {
            try {
                if (testCaseResult.value?.testSuiteRunId && testCaseResult.value?.id) {
                    messages.value = mapMessagesToAgentTestcaseChatUi(
                        await api.findTestSuiteRunResultMessages(
                            props.agentId,
                            testCaseResult.value.testSuiteRunId,
                            testCaseResult.value.id
                        ),
                        false
                    )
                } else {
                    messages.value = []
                }
            } catch (error) {
                if (error instanceof HttpError && error.status === 404) {
                    messages.value = []
                } else {
                    handleError(error)
                }
            }
        }
    } finally {
        isLoading.value = false
    }
}

const mapMessagesToAgentTestcaseChatUi = (msgs: ThreadMessage[], usePlaceholders: boolean = true): AgentTestcaseChatUiMessage[] => {
    const result: AgentTestcaseChatUiMessage[] = msgs.map((msg, index) => {
        const isUser = index % 2 === 0
        const placeholderText = isUser ? t('userMessagePlaceholder') : t('agentMessagePlaceholder')
        const text = msg.text || (usePlaceholders ? placeholderText : '')

        return new AgentTestcaseChatUiMessage(
            text,
            isUser,
            usePlaceholders && !msg.text,
            msg.id,
            msg.statusUpdates
        )
    })

    if (usePlaceholders) {
        if (result.length === 0) {
            result.push(new AgentTestcaseChatUiMessage(t('userMessagePlaceholder'), true, true))
            result.push(new AgentTestcaseChatUiMessage(t('agentMessagePlaceholder'), false, true))
        } else if (result[result.length - 1].isUser) {
            result.push(new AgentTestcaseChatUiMessage(t('agentMessagePlaceholder'), false, true))
        } else if (!result[result.length - 1].isPlaceholder) {
            result.push(new AgentTestcaseChatUiMessage(t('userMessagePlaceholder'), true, true))
            result.push(new AgentTestcaseChatUiMessage(t('agentMessagePlaceholder'), false, true))
        }
    }

    return result
}

const handleSelectMessage = async (message: AgentTestcaseChatUiMessage) => {
    selectedMessage.value = message
    await nextTick()
    chatInputRef.value?.focus()
    inputText.value = message.isPlaceholder ? '' : message.text
}

const handleSelectTestCase = async (newTestCase: TestCase | undefined) => {
    selectedMessage.value = undefined
    if (newTestCase) {
        if(!isRunning.value) await loadTestCaseData()
    } else if (props.isNewTestCase) {
        inputText.value = ''
        messages.value = [
            new AgentTestcaseChatUiMessage(t('userMessagePlaceholder'), true, true),
            new AgentTestcaseChatUiMessage(t('agentMessagePlaceholder'), false, true),
        ]
        await selectNextMessageOrPlaceholder()
    }
}

watch(() => testCase.value, async (newVal, oldVal) => {
    if ((newVal?.thread.id !== oldVal?.thread.id || props.isNewTestCase) && testCasesStore.testCases.length > 1) {
        await handleSelectTestCase(newVal)
    }
})

watch(() => testCaseResult.value, async () => {
    loadTestCaseData()
})

watch([() => props.isEditing, () => props.isNewTestCase], async () => {
    await handleSelectTestCase(testCase.value)
})

watch(executionState, (newState) => {
    if (!newState) {
        return
    }

    if (newState.userMessage) {
        const userMessage = newState.userMessage
        const existingUserMsg = messages.value.find((m: AgentTestcaseChatUiMessage) => m.isUser && m.id === userMessage.id)
        if (!existingUserMsg) {
            messages.value.push(new AgentTestcaseChatUiMessage(
                userMessage.text || '',
                true,
                false,
                userMessage.id
            ))
        }
    }

    if (newState.agentMessage) {
        const agentText = newState.agentMessage.text || ''

        let agentMsg = messages.value.slice().reverse().find((m: AgentTestcaseChatUiMessage) => !m.isUser)

        if (!agentMsg || agentMsg.id !== newState.agentMessage.id) {
            agentMsg = new AgentTestcaseChatUiMessage(
                agentText,
                false,
                false,
                newState.agentMessage?.id
            )
            messages.value.push(agentMsg)
        } else {
            agentMsg.text = agentText
        }

        agentMsg.id = newState.agentMessage.id
        agentMsg.isStreaming = newState.phase === 'executing' && !newState.agentMessage?.complete


        if (newState.statusUpdates && newState.statusUpdates.length > 0) {
            agentMsg.statusUpdates = newState.statusUpdates.map((su: any) => ({
                action: su.action,
                toolName: su.toolName,
                description: su.description,
                args: su.args,
                step: su.step,
                result: su.result,
                timestamp: su.timestamp || new Date()
            }))
        }

        if (newState.agentMessage?.complete === true) {
            agentMsg.completeStatus()
            agentMsg.isStreaming = false
        }
    }
}, { deep: true })

const onMessageSend = async () => {
    if (!selectedMessage.value) return

    const message = selectedMessage.value
    message.text = inputText.value
    message.isPlaceholder = false
    inputText.value = ''
    let currentTestCase = testCase.value;
    if (!currentTestCase) {
        currentTestCase = await addTestCase(props.agentId)
        setSelectedTestCase(currentTestCase)
    }
    saveMessageAsync(message, currentTestCase)

    const allMessagesSaved = messages.value.every(m => !m.isPlaceholder)
    if (allMessagesSaved) {
        const newUserPlaceholder = new AgentTestcaseChatUiMessage(
            t('userMessagePlaceholder'),
            true,
            true
        )
        const newAgentPlaceholder = new AgentTestcaseChatUiMessage(
            t('agentMessagePlaceholder'),
            false,
            true
        )
        messages.value.push(newUserPlaceholder)
        messages.value.push(newAgentPlaceholder)

        selectedMessage.value = newUserPlaceholder
        inputText.value = ''
        await nextTick()
        chatInputRef.value?.focus()
        return
    }

    if(getLastPlaceholder()) await selectNextMessageOrPlaceholder()
    else selectedMessage.value = undefined
}

const saveMessageAsync = (message: AgentTestcaseChatUiMessage, currentTestCase: TestCase) => {
    const apiCall = message.id
        ? api.updateTestCaseMessage(props.agentId, currentTestCase.thread.id, message.id, new TestCaseThreadMessageUpdate(message.text))
        : api.addTestCaseMessage(props.agentId, currentTestCase.thread.id,
            new TestCaseNewThreadMessage(message.text, message.isUser ? ThreadMessageOrigin.USER : ThreadMessageOrigin.AGENT))

    apiCall
        .then(async (updatedMessage: ThreadMessage) => {
            message.id = updatedMessage.id

            const firstUserMessage = messages.value[0]
            const firstAgentMessage = messages.value[1]
            const hasFirstUserMessage = firstUserMessage?.isUser && firstUserMessage?.text?.trim().length > 0 && !firstUserMessage.isPlaceholder
            const hasFirstAgentMessage = firstAgentMessage && !firstAgentMessage.isUser && firstAgentMessage?.text?.trim().length > 0 && !firstAgentMessage.isPlaceholder
            if (currentTestCase && currentTestCase.thread.id && hasFirstUserMessage && hasFirstAgentMessage) {
                await refreshTestCase(props.agentId, currentTestCase.thread.id)
            }
        })
        .catch((error: unknown) => {
            handleError(error)
        })
}

const selectNextMessageOrPlaceholder = async () => {
    if (selectedMessage.value) {
        const currentIndex = messages.value.findIndex(m => m.uuid === selectedMessage.value?.uuid)
        if (currentIndex !== -1 && currentIndex < messages.value.length - 1) {
            selectedMessage.value = messages.value[currentIndex + 1]
        }
    } else {
        selectedMessage.value = getLastPlaceholder()
    }
    await nextTick()
    inputText.value = selectedMessage.value?.isPlaceholder ? '' : selectedMessage.value?.text || ''
    if (selectedMessage.value) {
        chatInputRef.value?.focus()
    }
}

const getLastPlaceholder = () => {
    return messages.value.find(m => m.isPlaceholder)
}

const isMessageSelectable = (message: AgentTestcaseChatUiMessage) => {
    return getLastPlaceholder()?.uuid === message.uuid
}

const statusDescription = computed(() => {
    switch (testCaseResult.value?.status) {
        case TestCaseResultStatus.SUCCESS:
            return t('successDescription')
        case TestCaseResultStatus.FAILURE:
            return testCaseResult.value?.evaluatorAnalysis || t('failureDescription')
        case TestCaseResultStatus.ERROR:
            return t('errorDescription')
        default:
            return ''
    }
})

const toggleCompare = async () => {
    if (isComparingResultWithTestSpec.value) {
        isComparingResultWithTestSpec.value = false
        testSpecMessages.value = []
    } else {
        isComparingResultWithTestSpec.value = true
        await loadTestSpecMessages()
    }
    emit('compareResultWithTestSpecStateChanged', isComparingResultWithTestSpec.value)
}

const loadTestSpecMessages = async () => {
    try {
        const specMsgs = await api.findTestCaseMessages(props.agentId, testCaseResult.value!.testCaseId!)
        testSpecMessages.value = mapMessagesToAgentTestcaseChatUi(specMsgs, false)
    } catch (error) {
        handleError(error)
        testSpecMessages.value = []
    }
}

const showCompare = computed(() => {
    return testCaseResult.value && !isRunning.value && !props.isEditing && (testCaseResult.value?.status === TestCaseResultStatus.SUCCESS || testCaseResult.value?.status === TestCaseResultStatus.FAILURE)
})

const isCompareDisabled = computed(() => {
    return !existsTestCaseResultTest.value || isTestCaseResultTestModifiedAfterExecution.value
})

const compareButtonTooltip = computed(() => {
    if (isComparingResultWithTestSpec.value) {
        return t('closeCompare')
    }
    if (!existsTestCaseResultTest.value) {
        return t('compareDisabledReasonTestDeleted')
    }
    if (isTestCaseResultTestModifiedAfterExecution.value) {
        return t('compareDisabledReasonTestModified')
    }
    return t('compare')
})

const existsTestCaseResultTest = computed(() => {
    return testCaseResultTest.value !== undefined
})

const isTestCaseResultTestModifiedAfterExecution = computed(() => {
    return testCaseResultTest.value?.lastUpdate! > testCaseResult.value?.executedAt!
})

defineExpose({
    loadTestCaseData,
    isComparingResultWithTestSpec,
    testSpecMessages
})
</script>

<template>
    <Animate v-if="isLoading" :effect="AnimationEffect.FADE_IN" class="h-full">
        <AgentTestcasePanelSkeleton />
    </Animate>
    <FlexCard v-else header-height="auto">
        <template #header>
            <div class="flex flex-row items-center gap-4 h-10">
              <SimpleButton v-if="!isEditing && testCaseResult && testExecutionStore.selectedSuiteRun?.status !== TestSuiteRunStatus.RUNNING && !isComparingResultWithTestSpec" @click="$emit('showEdit')">
                  <IconArrowLeft />
              </SimpleButton>
              <div v-if="isEditing" class="flex flex-row gap-2">
                  <IconPencil v-if="testCase?.thread.name"/>
                  {{ testCase?.thread.name ? t('editTestCaseTitle', { testCaseName: testCase.thread.name }) :
                      t('newTestCaseTitle') }}
              </div>
              <div v-else class="flex gap-2 items-center">
                  <IconLoader2 v-if="isRunning" class="text-light-gray animate-spin" />
                  <div v-if="testCaseResult" class="flex flex-row items-center gap-2">
                    <IconSquareCheckFilled class="text-success" v-if="testCaseResult.status === TestCaseResultStatus.SUCCESS" v-tooltip.bottom="t('success')" />
                    <IconSquareXFilled class="text-error" v-if="testCaseResult.status === TestCaseResultStatus.FAILURE" v-tooltip.bottom="t('failure')" />
                    <IconExclamationMark class="text-white bg-warn rounded-sm p-0.5" size="20" v-if="testCaseResult.status === TestCaseResultStatus.ERROR" v-tooltip.bottom="t('error')" />
                    <IconSquareChevronsRightFilled class="text-light-gray" v-if="testCaseResult.status === TestCaseResultStatus.SKIPPED" v-tooltip.bottom="t('skipped')" />
                    {{ testCaseResult ? isRunning ? t('runningTestCase', { testCaseName: testCaseResult.testCaseName }) : t('testCaseResult', { testCaseName: testCaseResult.testCaseName }) : t('noRunResults') }}
                </div>
              </div>
              <div v-if="showCompare" class="ml-auto">
                  <SimpleButton @click="toggleCompare" :disabled="isCompareDisabled" v-tooltip.bottom="compareButtonTooltip">
                      <IconColumns v-if="!isComparingResultWithTestSpec"/>
                      <IconX v-else/>
                  </SimpleButton>
              </div>
            </div>
        </template>
        <div class="max-w-[837px] mx-auto flex-1 w-full min-h-0">
            <div class="flex flex-col h-full gap-4 py-4">
                <div class="flex flex-1 min-h-0 gap-2 w-full overflow-y-auto">
                    <div v-if="messages.length > 0 && (isEditing || (testCaseResult?.status !== TestCaseResultStatus.ERROR && testCaseResult?.status !== TestCaseResultStatus.PENDING))" class="flex flex-col w-full">
                        <div v-for="message in messages" :key="message.uuid">
                            <div v-if="!message.isUser && message.statusUpdates.length > 0" class="px-2 py-3">
                                <ChatStatus :status-updates="message.statusUpdates" :is-complete="message.isStatusComplete" />
                            </div>
                            <AgentTestcaseChatMessage :message="message"
                                :actions-enabled="!message.isPlaceholder && isEditing"
                                :is-selected="selectedMessage?.uuid === message.uuid" @select="handleSelectMessage"
                                :selectable="isMessageSelectable(message)" />
                        </div>
                    </div>
                </div>
                <div v-if="isEditing && selectedMessage"
                    class="flex flex-col gap-1 p-3 relative rounded-xl border border-auxiliar-gray focus-within:border-abstracta bg-white shadow-sm"
                    :class="selectedMessage ? selectedMessage?.isUser ? '!border-primary' : '!border-info' : ''">
                    <span class="absolute top-[-.85rem] right-20 font-semibold rounded-full px-4 py-1 text-sm z-10"
                        :class="{ 'bg-abstracta text-white': selectedMessage?.isUser, 'bg-info text-white': !selectedMessage?.isUser }">
                        {{ selectedMessage?.isUser ? t('user') : t('agent') }}</span>
                    <ChatInput
                        v-model="inputText"
                        ref="chatInputRef"
                        :chat="{
                            supportsStopResponse: () => false,
                            findPrompts: async () => [],
                            savePrompt: async () => {},
                            deletePrompt: async (id: number) => {},
                            supportsFileUpload: () => false,
                            supportsTranscriptions: () => false,
                            transcribe: async (blob: Blob) => '',
                            handleError: handleError
                        }"
                        :borderless="true"
                        @send="onMessageSend">
                    </ChatInput>
                </div>
                <div v-else-if="!isEditing && (testCaseResult || executionState)"
                    class="h-40 min-h-40 flex-shrink-0 border-t-1 border-auxiliar-gray p-4">
                    <div class="flex flex-col gap-4 h-full">
                        <AgentTestcaseStatus v-if="!isRunning && testCaseResult" :status="testCaseResult.status" />
                        <div class="h-full overflow-y-auto">
                            <div v-if="executionState && (executionState.phase === 'executing' || executionState.phase === 'evaluating')" class="flex flex-row items-center gap-2">
                                <IconLoader2 class="text-light-gray animate-spin" />
                                <span v-if="executionState.phase === 'executing'">{{ t('phaseExecuting') }}</span>
                                <span v-else>{{ t('phaseEvaluating') }}</span>
                            </div>
                            <div v-else-if="isRunning" class="flex flex-row items-center gap-2">
                                <IconLoader2 class="text-light-gray animate-spin" />
                                <span>{{ t('testRunning') }}</span>
                            </div>
                            <div v-else-if="testCaseResult" class="flex flex-row items-center gap-2">
                                {{ statusDescription }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </FlexCard>
</template>

<i18n lang="json">
{
    "en": {
        "newTestCaseTitle": "Create a new test case",
        "editTestCaseTitle": "Editing: {testCaseName}",
        "userMessagePlaceholder": "Message that a person would send to the agent…",
        "agentMessagePlaceholder": "Expected response from the agent…",
        "user": "Message from the user",
        "agent": "Expected response",
        "noRunResults": "No execution results yet",
        "successDescription": "The agent's response matched the expected output. No formatting or content deviations were detected.",
        "failureDescription": "The agent's response did not match the expected output. Formatting or content deviations were detected.",
        "errorDescription": "An error occurred while running the test case",
        "runningTestCase": "Running: {testCaseName}",
        "testCaseResult": "Test case result: {testCaseName}",
        "testRunning": "Test is running...",
        "phaseExecuting": "Executing test case...",
        "phaseEvaluating": "Evaluating response...",
        "compare": "Compare with specification",
        "closeCompare": "Close compare",
        "compareDisabledReasonTestModified": "Compare is disabled because the test case was modified after the test execution",
        "compareDisabledReasonTestDeleted": "Compare is disabled because the test case was deleted",
        "success": "Success",
        "failure": "Failed",
        "error": "Error running",
        "skipped": "Skipped"
    },
    "es": {
        "newTestCaseTitle": "Crea un nuevo test case",
        "editTestCaseTitle": "Editando: {testCaseName}",
        "userMessagePlaceholder": "Mensaje que enviaría una persona al agente…",
        "agentMessagePlaceholder": "Respuesta esperada del agente…",
        "user": "Mensaje del usuario",
        "agent": "Respuesta esperada",
        "noRunResults": "No hay resultados de ejecución aún",
        "successDescription": "La respuesta del agente coincidió con la salida esperada. No se detectaron desvíos de formato o contenido.",
        "failureDescription": "La respuesta del agente no coincidió con la salida esperada. Se detectaron desvíos de formato o contenido.",
        "errorDescription": "Ocurrió un error al ejecutar el test case",
        "runningTestCase": "Ejecutando: {testCaseName}",
        "testCaseResult": "Resultado del test case: {testCaseName}",
        "testRunning": "El test está ejecutándose...",
        "phaseExecuting": "Ejecutando test case...",
        "phaseEvaluating": "Evaluando respuesta...",
        "compare": "Comparar con la especificación",
        "closeCompare": "Cerrar comparación",
        "compareDisabledReasonTestModified": "La comparación está deshabilitada porque el test case fue modificado después de la ejecución del test",
        "compareDisabledReasonTestDeleted": "La comparación está deshabilitada porque el test case fue eliminado",
        "success": "Pasó",
        "failure": "Falló",
        "error": "Error al ejecutar",
        "skipped": "Omitido"
    }
}
</i18n>
