<script lang="ts">
import { v4 as uuidv4 } from 'uuid';

export interface StatusUpdate {
  action: string
  toolName?: string
  description?: string
  args?: any
  step?: string
  result?: string | string[]
  timestamp: Date
}

export class AgentTestcaseChatUiMessage{
    id?: number
    uuid: string
    text: string
    isUser: boolean
    isPlaceholder: boolean
    isStreaming?: boolean
    statusUpdates: StatusUpdate[] = []
    isStatusComplete: boolean = false

    constructor(text: string, isUser: boolean, isPlaceholder: boolean, id?: number, statusUpdates?: StatusUpdate[]){
        this.uuid = uuidv4()
        this.text = text
        this.isUser = isUser
        this.isPlaceholder = isPlaceholder
        this.id = id
        this.isStreaming = false
        this.statusUpdates = statusUpdates || []
        this.isStatusComplete = (statusUpdates?.length || 0) > 0
    }

    public addStatusUpdate(statusUpdate: StatusUpdate): void {
        this.statusUpdates.push(statusUpdate)
    }

    public completeStatus(): void {
        this.isStatusComplete = true
    }
}

</script>

<script setup lang="ts">
import { IconEditCircle } from '@tabler/icons-vue';
import { escapeHtml } from 'markdown-it/lib/common/utils'
import { useI18n } from 'vue-i18n'

defineProps<{
    message: AgentTestcaseChatUiMessage
    isSelected?: boolean
    actionsEnabled?: boolean
    selectable?: boolean
}>()

const emit = defineEmits<{
    (e: 'select', message: AgentTestcaseChatUiMessage): void
}>()

const { t } = useI18n()

</script>

<template>
    <div class="p-2 py-3 formatted-text w-full" @click="selectable ? emit('select', message) : null">
        <div class="flex flex-col gap-2" :class="{'items-end justify-end': message.isUser, 'items-start justify-start': !message.isUser}">
            <div class="flex gap-4 rounded-xl border-1 border-transparent" :class="{
                'justify-self-end overflow-hidden bg-pale max-w-3/4': message.isUser,
                'p-4': message.isPlaceholder || message.isUser,
                'cursor-pointer': selectable,
                'gap-2 max-w-full': !message.isUser,
                '!border-primary border-pulse-primary': message.isUser && isSelected,
                'p-4 !border-info border-pulse-info': !message.isUser && isSelected,
                '!border-auxiliar-gray': message.isPlaceholder && !message.isUser,
                'border-dashed': message.isPlaceholder
            }">
                <div class="overflow-x-auto">
                    <div class="break-words" :class="{'text-dark-gray': !message.isPlaceholder, 'text-light-gray': message.isPlaceholder}"
                        v-html="message.text ? escapeHtml(message.text).replace(/\n/g, '<br/>') : ''"></div>
                </div>
            </div>
            <div class="flex gap-2" :class="!actionsEnabled ? 'invisible' : ''">
                <InteractiveIcon v-tooltip.bottom="t('editMessageButton')" @click="$emit('select', message)"
                    :icon="IconEditCircle" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.border-pulse-primary {
    animation: border-pulse 1.5s ease-in-out infinite;
    color: var(--color-primary);
}

.border-pulse-info {
    animation: border-pulse 1.5s ease-in-out infinite;
    color: var(--color-info);
}
</style>

<i18n lang="json">
{
    "en": {
        "editMessageButton": "Edit message"
    },
    "es": {
        "editMessageButton": "Editar mensaje"
    }
}
</i18n>
