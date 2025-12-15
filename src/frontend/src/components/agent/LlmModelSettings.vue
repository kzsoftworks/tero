<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { LlmModelType, LlmTemperature, ReasoningEffort } from '@/services/api'

const props = defineProps<{
  modelType?: LlmModelType
  temperature?: LlmTemperature
  reasoningEffort?: ReasoningEffort
}>()

const emit = defineEmits<{
  (e: 'update:temperature', value: LlmTemperature): void
  (e: 'update:reasoningEffort', value: ReasoningEffort): void
  (e: 'change'): void
}>()

const { t } = useI18n()
const temperatures = computed(() => [
  { name: t('preciseTemperature'), value: LlmTemperature.PRECISE },
  { name: t('neutralTemperature'), value: LlmTemperature.NEUTRAL },
  { name: t('creativeTemperature'), value: LlmTemperature.CREATIVE }
])

const reasoningEfforts = computed(() => [
  { name: t('lowEffort'), value: ReasoningEffort.LOW },
  { name: t('mediumEffort'), value: ReasoningEffort.MEDIUM },
  { name: t('highEffort'), value: ReasoningEffort.HIGH }
])

const onChangeTemperature = (value: LlmTemperature) => {
  emit('update:temperature', value)
  emit('change')
}

const onChangeReasoningEffort = (value: ReasoningEffort) => {
  emit('update:reasoningEffort', value)
  emit('change')
}
</script>

<template>
  <div class="form-field" v-if="modelType === LlmModelType.CHAT">
    <label for="temperature">{{ t('temperatureLabel') }}</label>
    <SelectButton
      id="temperature"
      :model-value="temperature"
      :options="temperatures"
      option-label="name"
      option-value="value"
      :allow-empty="false"
      @update:model-value="onChangeTemperature"
    />
  </div>
  <div class="form-field" v-else-if="modelType === LlmModelType.REASONING">
    <label for="reasoningEffort">{{ t('reasoningEffortLabel') }}</label>
    <SelectButton
      id="reasoningEffort"
      :model-value="reasoningEffort"
      :options="reasoningEfforts"
      option-label="name"
      option-value="value"
      :allow-empty="false"
      @update:model-value="onChangeReasoningEffort"
    />
  </div>
</template>

<i18n lang="json">
{
  "en": {
    "temperatureLabel": "Temperature",
    "reasoningEffortLabel": "Reasoning",
    "preciseTemperature": "Precise",
    "neutralTemperature": "Neutral",
    "creativeTemperature": "Creative",
    "lowEffort": "Low",
    "mediumEffort": "Medium",
    "highEffort": "High"
  },
  "es": {
    "temperatureLabel": "Temperatura",
    "reasoningEffortLabel": "Razonamiento",
    "preciseTemperature": "Preciso",
    "neutralTemperature": "Neutro",
    "creativeTemperature": "Creativo",
    "lowEffort": "Bajo",
    "mediumEffort": "Medio",
    "highEffort": "Alto"
  }
}
</i18n>
