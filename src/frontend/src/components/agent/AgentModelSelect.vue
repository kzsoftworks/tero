<script lang="ts" setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { LlmModel, LlmModelVendor, LlmTemperature, ReasoningEffort } from '@/services/api'
import openAiIcon from '@/assets/images/open-ai.svg'
import googleIcon from '@/assets/images/gemini.svg'
import anthropicIcon from '@/assets/images/anthropic.svg'
import LlmModelSettings from './LlmModelSettings.vue'

const props = defineProps<{
  modelId?: string
  models: LlmModel[]
  temperature?: LlmTemperature
  reasoningEffort?: ReasoningEffort
}>()

const emit = defineEmits<{
  (e: 'update:modelId', value: string): void
  (e: 'update:temperature', value: LlmTemperature): void
  (e: 'update:reasoningEffort', value: ReasoningEffort): void
  (e: 'change'): void
}>()

const { t } = useI18n()

const showAllModels = ref(false)

const findSelectedModel = (): LlmModel | undefined => {
  return props.models.find((m) => m.id === props.modelId)
}

const updateShowAllModels = () => {
  const selectedModel = findSelectedModel()
  if (selectedModel && !selectedModel.isBasic) {
    showAllModels.value = true
  } else if (!selectedModel) {
    showAllModels.value = false
  }
}

watch(() => props.modelId, () => {
  updateShowAllModels()
})

onMounted(() => {
  updateShowAllModels()
})

const onShowAllModels = () => {
  showAllModels.value = true
}

const modelOptions = computed(() => {
  if (showAllModels.value) {
    return props.models
  }
  return props.models.filter((m) => m.isBasic)
})

const groupedModelsByVendor = (modelsToGroup: LlmModel[]) => {
  const map = new Map<LlmModelVendor, LlmModel[]>();

  for (const model of modelsToGroup) {
    if (!map.has(model.modelVendor)) {
      map.set(model.modelVendor, []);
    }
    map.get(model.modelVendor)!.push(model);
  }

  return Array.from(map.values());
}

const flatOptions = computed(() => {
  const modelsToGroup = modelOptions.value
  const models = groupedModelsByVendor(modelsToGroup);
  return models.flatMap((vendorModels) => vendorModels.map((m, i) => ({ ...m, vendor: m.modelVendor, showVendor: i === 0 })));
});

const vendorLogos: Record<LlmModelVendor, string | undefined> = {
  [LlmModelVendor.OPENAI]: openAiIcon,
  [LlmModelVendor.GOOGLE]: googleIcon,
  [LlmModelVendor.ANTHROPIC]: anthropicIcon
}

const onModelChange = (value: string) => {
  emit('update:modelId', value)
  emit('change')
}

const modelType = computed(() => findSelectedModel()?.modelType)

const onSettingsChange = () => {
  emit('change')
}
</script>

<template>
  <div class="flex flex-row gap-3" id="agent-model-container">
    <div class="form-field w-full">
      <label for="model">{{ t('modelLabel') }}</label>
      <Select
        id="model"
        :model-value="modelId"
        @update:model-value="onModelChange"
        option-label="name"
        option-value="id"
        class="w-full"
        appendTo="#agent-model-container"
        overlay-class="left-8! mt-[-20px]! w-[calc(100%-64px)]! p-2! pr-0!"
        :options="flatOptions"
      >
        <template #option="slotProps">
          <div class="flex items-stretch gap-3 w-full">
            <div class="w-32 flex items-center self-stretch">
              <img v-if="slotProps.option.showVendor && slotProps.option.vendor && vendorLogos[slotProps.option.vendor as LlmModelVendor]"
                :src="vendorLogos[slotProps.option.vendor as LlmModelVendor]"
                :alt="slotProps.option.vendor"
                 />
            </div>
            <div :class="['flex-1 flex flex-col gap-1 hover:bg-pale rounded-md p-3', slotProps.selected ? 'selected-option' : '']">
              <div class="font-medium">{{ slotProps.option.name }}</div>
              <div class="text-sm font-normal break-words whitespace-normal">{{ slotProps.option.description }}</div>
            </div>
          </div>
        </template>
        <template #dropdownicon>
          <IconCaretRightFilled />
        </template>
        <template #footer>
          <div class="p-3 flex justify-center" v-if="!showAllModels">
            <SimpleButton @click="onShowAllModels" shape="square">{{ t('showAllModels') }}</SimpleButton>
          </div>
        </template>
      </Select>
    </div>
    <LlmModelSettings
      :model-type="modelType"
      :temperature="props.temperature"
      :reasoning-effort="props.reasoningEffort"
      @update:temperature="(value) => emit('update:temperature', value)"
      @update:reasoning-effort="(value) => emit('update:reasoningEffort', value)"
      @change="onSettingsChange"
    />
  </div>
</template>

<i18n lang="json">
  {
    "en": {
      "showAllModels": "Show all",
      "modelLabel": "Model"
    },
    "es": {
      "showAllModels": "Mostrar todos",
      "modelLabel": "Modelo"
    }
  }
</i18n>
<style scoped lang="scss">

:deep(.p-select-list) {
  gap: 8px !important;
}

:deep(.p-select-option) {
  padding: 0 !important;
}

:deep(.p-select-option.p-select-option-selected) {
  background: transparent !important;
}

:deep(.p-select-option.p-focus) {
  background: transparent !important;
  border-color: transparent !important;
}

.selected-option {
  background-color: #f4f4f4;
}

:deep(.p-select-overlay) {
  max-height: 50vh!important;
  display: flex!important;
  flex-direction: column!important;
}

:deep(.p-select-list-container) {
  max-height: calc(45vh - 60px)!important;
  overflow-y: auto!important;
  flex: 1!important;
}

:deep(.p-select-footer) {
  flex-shrink: 0!important;
  border-top: 1px solid #e5e7eb!important;
}
</style>
