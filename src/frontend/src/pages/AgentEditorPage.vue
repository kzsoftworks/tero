<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { useRoute, useRouter, onBeforeRouteUpdate } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ApiService, Thread, HttpError, TestCaseResultStatus, TestSuiteRun, TestSuiteRunStatus } from '@/services/api';
import type { TestSuiteExecutionStreamEvent } from '@/services/api';
import AgentTestcasePanel from '@/components/agent/AgentTestcasePanel.vue';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useToast } from 'vue-toastification';
import ToastMessage from '@/components/common/ToastMessage.vue';
import { useTestCaseStore } from '@/composables/useTestCaseStore';
import { useTestExecutionStore } from '@/composables/useTestExecutionStore';
import { handleOAuthRequestsIn, AuthenticationError } from '@/services/toolOAuth';

export type { TestCaseExecutionState } from '@/composables/useTestExecutionStore';

const { t } = useI18n()
const { handleError } = useErrorHandler()
const toast = useToast()
const { testCasesStore, loadTestCases: loadTestCasesFromStore, clearTestCases } = useTestCaseStore()
const { testExecutionStore, loadSuiteRunResults, processStreamEvent, initializeTestRun, clear: clearExecutionStore } = useTestExecutionStore()
const api = new ApiService();
const route = useRoute();
const router = useRouter();
const agentId = ref<number>();
const threadId = ref<number>();
const showTestCaseEditor = ref<boolean>(false);
const isEditingTestCase = ref<boolean>(true);
const testCasePanel = ref<InstanceType<typeof AgentTestcasePanel>>();
const loadingTests = ref<boolean>(true);
const testRunStartedByCurrentUser = ref<boolean>(false);
const isComparingResultWithTestSpec = ref<boolean>(false);

const startChat = async () => {
  try {
    const thread = await api.startThread(agentId.value!);
    threadId.value = thread.id;
  } catch (e: unknown) {
    if (e instanceof HttpError && e.status === 400 && e.message.includes("Agent not found")) {
      router.push('/not-found');
    }
  }
}

const handleSelectChat = (chat: Thread) => {
  threadId.value = chat.id;
}

const handleSelectExecution = async (execution: TestSuiteRun) => {
  testExecutionStore.clear()
  testExecutionStore.setSelectedSuiteRun(execution)
  try {
    const results = await loadSuiteRunResults(agentId.value!, execution.id)
    testExecutionStore.setSelectedResult(results[0])
  } catch (error) {
    handleError(error)
  }
  isEditingTestCase.value = false
}

const processSuiteExecutionStream = async (
  eventStream: AsyncIterable<TestSuiteExecutionStreamEvent>,
) => {
  let currentTestCaseResultId: number | undefined = undefined;
  try {
    for await (const event of eventStream) {
      const updatedResultId = processStreamEvent(event, {
        agentId: agentId.value,
        currentTestCaseResultId
      });
      currentTestCaseResultId = updatedResultId ?? currentTestCaseResultId;

      if (event.type === 'suite.error') {
        toast.error(
          { component: ToastMessage, props: { message: t('suiteExecutionFailed') } },
          { timeout: 5000, icon: false }
        );
      }
    }
  } catch (error) {
    if (currentTestCaseResultId) {
      const testCaseResult = testExecutionStore.testCaseResults.find(tr => tr.id === currentTestCaseResultId);
      if (testCaseResult) {
        testCaseResult.status = TestCaseResultStatus.ERROR;
      }
      testExecutionStore.setExecutionState(currentTestCaseResultId, {
        phase: 'completed',
        status: TestCaseResultStatus.ERROR
      });
    }
    handleError(error)
  } finally {
    testExecutionStore.clearExecutionStates();
    testRunStartedByCurrentUser.value = false;
  }
}

const runTestSuite = async (testCaseIds?: number[]) => {
  isEditingTestCase.value = false
  testRunStartedByCurrentUser.value = true

  try {
    initializeTestRun(agentId.value!, testCasesStore.testCases, testCaseIds?.[0])
    const suiteRun = await handleOAuthRequestsIn(
      () => api.runTestSuite(agentId.value!, testCaseIds),
      api
    )
    testExecutionStore.setSelectedSuiteRun(suiteRun)
    await processSuiteExecutionStream(api.streamTestSuiteUpdates(agentId.value!, suiteRun.id))
  } catch (error) {
    if (error instanceof AuthenticationError) {
      toast.error(
        { component: ToastMessage, props: { message: t('authenticationCancelled') } },
        { timeout: 5000, icon: false }
      )
      isEditingTestCase.value = true
      testRunStartedByCurrentUser.value = false
      return
    }
    await handleRunError(error)
  }
}

const handleRunError = async (error: unknown) => {
  if (error instanceof HttpError && error.status === 409) {
    try {
      toast.info(
        { component: ToastMessage, props: { message: t('suiteAlreadyRunning') } },
        { timeout: 5000, icon: false }
      )
      testRunStartedByCurrentUser.value = false
      const suiteRuns = await api.findTestSuiteRuns(agentId.value!, 1, 0)
      if (suiteRuns.length && suiteRuns[0].status === TestSuiteRunStatus.RUNNING) {
        testExecutionStore.setSelectedSuiteRun(suiteRuns[0])
        const results = await loadSuiteRunResults(agentId.value!, suiteRuns[0].id)
        testExecutionStore.setSelectedResult(results[0])
        await processSuiteExecutionStream(api.streamTestSuiteUpdates(agentId.value!, suiteRuns[0].id))
      }
    } catch (error) {
      handleError(error)
    }
  } else {
    handleError(error)
    testRunStartedByCurrentUser.value = false
  }
}

onMounted(async () => {
  agentId.value = parseInt(route.params.agentId as string);
  await startChat();
  if (agentId.value) {
    await loadTestCases(agentId.value);
  }
});

const loadTestCases = async (id: number) => {
  try {
    await loadTestCasesFromStore(id)

    if(testCasesStore.testCases.length) {
      testCasesStore.setSelectedTestCase(testCasesStore.testCases[0])
    }

    const suiteRuns = await api.findTestSuiteRuns(id, 1, 0)
    if (suiteRuns.length && suiteRuns[0].status === TestSuiteRunStatus.RUNNING) {
      isEditingTestCase.value = false
      testExecutionStore.setSelectedSuiteRun(suiteRuns[0])
      const results = await loadSuiteRunResults(id, suiteRuns[0].id)
      testExecutionStore.setSelectedResult(results[0])
      processSuiteExecutionStream(api.streamTestSuiteUpdates(id, suiteRuns[0].id))
    }
  } catch (e) {
    handleError(e)
  } finally {
    loadingTests.value = false
  }
}

const onEditingTestCase = (editing: boolean) => {
  if(testExecutionStore.selectedSuiteRun?.status == TestSuiteRunStatus.RUNNING) return
  isEditingTestCase.value = editing
}

onBeforeRouteUpdate(async (to) => {
  testRunStartedByCurrentUser.value = false;
  clearTestCases();
  clearExecutionStore();

  agentId.value = parseInt(to.params.agentId as string);
  await startChat();
  if (agentId.value) {
    await loadTestCases(agentId.value);
  }
});
</script>

<template>
  <PageLayout left-column-class="w-[calc(40%-var(--spacing)*3/2)] min-w-[670px]"
    right-column-class="w-[calc(60%-var(--spacing)*3/2)]">
    <template #left>
      <AgentEditorPanel v-if="threadId" :selected-thread-id="threadId"
        @show-test-case-editor="showTestCaseEditor = $event" :loading-tests="loadingTests"
        @editing-testcase="onEditingTestCase" :editing-testcase="isEditingTestCase"
        @import-agent="loadTestCases(agentId!)" :test-cases="testCasesStore.testCases" @run-tests="runTestSuite()"
        @run-single-test="(id: number) => runTestSuite([id])" @select-execution="handleSelectExecution"
        :is-comparing-result-with-test-spec="isComparingResultWithTestSpec"
        :test-spec-messages="testCasePanel?.testSpecMessages"/>
    </template>
    <template #right>
      <ChatPanel :thread-id="threadId" v-if="threadId && !showTestCaseEditor" :editing-agent="true"
        @new-chat="startChat" @select-chat="handleSelectChat" />
      <AgentTestcasePanel v-if="agentId && showTestCaseEditor" :agent-id="agentId" :thread-id="threadId"
        :is-editing="isEditingTestCase" @show-edit="isEditingTestCase = true"
        :is-new-test-case="testCasesStore.testCases.length === 0" ref="testCasePanel"
        @compare-result-with-test-spec-state-changed="isComparingResultWithTestSpec = $event" />
    </template>
  </PageLayout>
</template>

<i18n lang="json">
{
  "en": {
    "suiteExecutionFailed": "Test suite execution failed",
    "suiteAlreadyRunning": "Please wait for the test suite to finish running before starting a new execution",
    "authenticationCancelled": "Tool authentication was cancelled. Please authenticate to run tests."
  },
  "es": {
    "suiteExecutionFailed": "Falló la ejecución de la suite de tests",
    "suiteAlreadyRunning": "Espera a que el test suite termine de correr para lanzar una nueva ejecucion",
    "authenticationCancelled": "La autenticación de la herramienta fue cancelada. Por favor autentícate para ejecutar los tests."
  }
}
</i18n>
