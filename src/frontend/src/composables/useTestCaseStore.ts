import { reactive } from 'vue'
import { ApiService, TestCase } from '@/services/api'

const testCasesStore = reactive({
  testCases: [] as TestCase[],
  selectedTestCase: undefined as TestCase | undefined,
  async setTestCases(testCases: TestCase[]) {
    this.testCases = testCases
    this.selectedTestCase = testCases.find(tc => tc.thread.id === this.selectedTestCase?.thread.id)
  },
  addTestCase(testCase: TestCase) {
    this.testCases.push(testCase)
  },
  removeTestCase(testCaseThreadId: number) {
    this.testCases = this.testCases.filter((tc) => tc.thread.id !== testCaseThreadId)
    if (this.selectedTestCase?.thread.id === testCaseThreadId) {
      this.selectedTestCase = this.testCases.length > 0 ? this.testCases[0] : undefined
    }
  },
  updateTestCase(testCaseThreadId: number, updatedTestCase: TestCase) {
    const index = this.testCases.findIndex((tc) => tc.thread.id === testCaseThreadId)
    if (index !== -1) {
      this.testCases[index] = updatedTestCase
      if (this.selectedTestCase?.thread.id === testCaseThreadId) {
        this.selectedTestCase = updatedTestCase
      }
    }
  },
  setSelectedTestCase(testCase: TestCase | undefined) {
    this.setSelectedTestCaseById(testCase?.thread.id)
  },
  setSelectedTestCaseById(testCaseId: number | undefined) {
    this.selectedTestCase = testCaseId ? this.testCases.find(tc => tc.thread.id === testCaseId) : undefined
  },
  clearTestCases() {
    this.testCases = []
    this.selectedTestCase = undefined
  }
})

export function useTestCaseStore() {
  const api = new ApiService()

  async function loadTestCases(agentId: number) {
    testCasesStore.setTestCases(await api.findTestCases(agentId))
  }

  async function addTestCase(agentId: number) {
    const testCase = await api.addTestCase(agentId)
    if (testCasesStore.testCases.find(tc => tc.thread.id === testCase.thread.id)) {
      testCasesStore.updateTestCase(testCase.thread.id, testCase)
    } else {
      testCasesStore.addTestCase(testCase)
    }
    return testCase
  }

  async function deleteTestCase(agentId: number, testCaseThreadId: number) {
    await api.deleteTestCase(agentId, testCaseThreadId)
    testCasesStore.removeTestCase(testCaseThreadId)
  }

  async function updateTestCase(agentId: number, testCaseThreadId: number, name: string) {
    const updatedTestCase = await api.updateTestCase(agentId, testCaseThreadId, name)
    testCasesStore.updateTestCase(testCaseThreadId, updatedTestCase)
  }

  async function refreshTestCase(agentId: number, testCaseThreadId: number) {
    const testCase = await api.findTestCase(agentId, testCaseThreadId)
    testCasesStore.updateTestCase(testCaseThreadId, testCase)
    return testCase
  }

  async function cloneTestCase(agentId: number, testCaseThreadId: number) {
    const clonedTestCase = await api.cloneTestCase(agentId, testCaseThreadId)
    testCasesStore.addTestCase(clonedTestCase)
    return clonedTestCase
  }

  function clearTestCases() {
    testCasesStore.clearTestCases()
  }

  function setSelectedTestCase(testCase: TestCase | undefined) {
    testCasesStore.setSelectedTestCase(testCase)
  }

  function setSelectedTestCaseById(testCaseId: number | undefined) {
    testCasesStore.setSelectedTestCaseById(testCaseId)
  }

  return {
    testCasesStore,
    loadTestCases,
    addTestCase,
    deleteTestCase,
    updateTestCase,
    refreshTestCase,
    cloneTestCase,
    clearTestCases,
    setSelectedTestCase,
    setSelectedTestCaseById
  }
}
