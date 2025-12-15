import { reactive } from 'vue'
import { ApiService, type AgentPromptUpdate } from '@/services/api'
import { AgentPrompt } from '../../../common/src/utils/domain'

const agentsPromptStore = reactive({
  prompts: [] as AgentPrompt[],
  async setPrompts(prompts: AgentPrompt[]) {
    this.prompts = prompts
  },
  addPrompt(prompt: AgentPrompt) {
    this.prompts.unshift(prompt)
  },
  removePrompt(promptId: number) {
    this.prompts = this.prompts.filter((a) => a.id !== promptId)
  },
  updatePrompt(updatedPrompt: AgentPrompt) {
    this.removePrompt(updatedPrompt.id!)
    this.addPrompt(updatedPrompt)
  }
})

export function useAgentPromptStore() {
  const api = new ApiService()

  async function newPrompt(agentId: number, prompt: AgentPrompt) {
    const newPrompt = await api.newAgentPrompt(agentId, prompt)
    prompt.id = newPrompt.id
    agentsPromptStore.addPrompt(newPrompt)
  }

  async function removePrompt(agentId: number, prompId: number) {
    await api.deleteAgentPrompt(agentId, prompId)
    agentsPromptStore.removePrompt(prompId)
  }

  async function loadAgentPrompts(agentId: number) {
    agentsPromptStore.setPrompts(await api.findAgentPrompts(agentId))
  }

  async function updatePrompt(agentId: number, promptId: number, prompt: AgentPromptUpdate) {
    const updatedPrompt = await api.updateAgentPrompt(agentId, promptId, prompt)
    agentsPromptStore.updatePrompt(updatedPrompt)
  }

  async function setPrompts(prompts: AgentPrompt[]) {
    agentsPromptStore.setPrompts(prompts)
  }

  return { agentsPromptStore, loadAgentPrompts, removePrompt, updatePrompt, newPrompt, setPrompts }
}
