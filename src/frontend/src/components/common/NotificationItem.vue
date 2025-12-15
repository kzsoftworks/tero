<script setup lang="ts">
import { IconChevronDown, IconChevronUp } from '@tabler/icons-vue';
import { TeamRole } from '@/services/api';
import { useI18n } from 'vue-i18n';
import { ref } from 'vue';

const { t } = useI18n();

defineProps<{
    invitation: TeamRole;
}>();

const emits = defineEmits<{
    (e: 'acceptInvitation', teamId: number): void;
    (e: 'rejectInvitation', teamId: number): void;
}>();

const collapsed = ref<boolean>(true);
</script>

<template>
    <Panel class="invitation-panel" toggleable :collapsed="collapsed" @update:collapsed="collapsed = $event">
        <template #header>
            <div class="flex items-center gap-2">
                <span class="">{{ t('invitationText') }}</span>
                <span class="font-semibold">{{ invitation.name }}</span>
            </div>
        </template>
        <template #toggleicon>
            <InteractiveIcon :icon="collapsed ? IconChevronDown : IconChevronUp" />
        </template>
        <div class="flex flex-col gap-4">
            <div class="flex flex-col">
                <span class="mb-2">{{ t('acceptText') }}:</span>
                <ol class="pl-2 list-disc list-inside">
                    <li>{{ t('usageMetricsText') }}</li>
                    <li>{{ t('editAgentsText') }}</li>
                </ol>
            </div>
            <div class="flex items-center justify-end gap-4">
                <SimpleButton shape="square" @click="emits('rejectInvitation', invitation.id)">
                    {{ t('rejectButton') }}
                </SimpleButton>
                <SimpleButton variant="primary" shape="square" @click="emits('acceptInvitation', invitation.id)">
                    {{ t('acceptButton') }}
                </SimpleButton>
            </div>
        </div>
    </Panel>
</template>

<i18n lang="json">{
    "en": {
        "accept": "Accept",
        "reject": "Reject",
        "invitationText": "You have been invited to join the team",
        "acceptText": "By accepting, the leaders of this team will be able to",
        "usageMetricsText": "See your metrics of hours saved with AI and the number of chats.",
        "editAgentsText": "Edit the agents you publish in this new team.",
        "acceptButton": "Accept invitation",
        "rejectButton": "Reject"
    },
    "es": {
        "accept": "Aceptar",
        "reject": "Rechazar",
        "invitationText": "Has sido invitado para unirte al equipo",
        "acceptText": "Al aceptar, los lideres de este equipo podrán",
        "usageMetricsText": "Ver las métricas de tus horas ahorradas con IA y el número de chats.",
        "editAgentsText": "Editar los agentes que publiques en este nuevo equipo.",
        "acceptButton": "Aceptar invitación",
        "rejectButton": "Rechazar"
    }
}</i18n>

<style lang="scss">
@import '@/assets/styles.css';

.p-panel.invitation-panel {
    @apply border-t-0 border-l-0 border-b-1 border-r-0 rounded-none;

    &:last-child {
        @apply border-b-0;
    }

    .p-panel-header {
        @apply px-2 py-1
    }
}
</style>
