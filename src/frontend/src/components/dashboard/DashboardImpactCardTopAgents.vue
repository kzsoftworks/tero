<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, onMounted, watch } from 'vue';
import { AgentImpactItem, MY_TEAM_ID, ExternalAgent, Agent, UserImpactItem, PRIVATE_AGENT_ID } from '@/services/api';
import { ApiService } from '@/services/api';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useDebounce } from '@/composables/useDebounce';
import { useChatStore } from '@/composables/useChatStore';

const { t } = useI18n();
const { handleError } = useErrorHandler();
const api = new ApiService();
const { newChat } = useChatStore();
const props = defineProps<{
    fromDate: Date;
    toDate: Date;
    teamId: number;
}>();

const loading = ref<boolean>(false);
const topAgents = ref<AgentImpactItem[]>([]);
const agentPage = ref<number>(1);
const pageSize = 20;
const loadingMoreAgents = ref<boolean>(false);
const hasMoreAgents = ref<boolean>(true);
const isSearchingAgent = ref<boolean>(false);
const searchAgent = ref<string>('');
const showAgentInfoModal = ref<boolean>(false);
const selectedAgent = ref<AgentImpactItem | undefined>(undefined);
const showRegisterExternalAgentModal = ref<boolean>(false);
const externalAgents = ref<ExternalAgent[]>([]);
const topUsers = ref<UserImpactItem[]>([]);
const userPage = ref<number>(1);
const hasMoreUsers = ref<boolean>(true);
const usersPageSize = 10;
const loadingTopUsers = ref<boolean>(false);
const loadingMoreUsers = ref<boolean>(false);

onMounted(async () => {
    await loadAgentsData();
    await loadExternalAgents();
})

const loadAgentsData = async () => {
    try{
        loading.value = true;
        await loadData();
    } catch (error) {
        handleError(error);
    } finally {
        loading.value = false;
    }
}

const loadExternalAgents = async () => {
    try{
        externalAgents.value = await api.findExternalAgents();
    } catch (error) {
        handleError(error);
    }
}

const loadData = async () => {
    agentPage.value = 1;
    const agents = await api.getImpactTopAgents(t('privateAgents'), props.fromDate, props.toDate, props.teamId, searchAgent.value, pageSize + 1, 0);
    topAgents.value = agents.slice(0, pageSize);
    hasMoreAgents.value = agents.length === pageSize + 1;
    isSearchingAgent.value = false;
}

const handleLoadMoreAgents = async () => {
    try {
        loadingMoreAgents.value = true;
        agentPage.value++;
        const moreAgents = await api.getImpactTopAgents(t('privateAgents'), props.fromDate, props.toDate, props.teamId, searchAgent.value, pageSize + 1, (agentPage.value - 1) * pageSize);
        topAgents.value = [...topAgents.value, ...moreAgents.slice(0, pageSize)];

        hasMoreAgents.value = moreAgents.length === pageSize + 1;
    } catch (error) {
        handleError(error);
    } finally {
        loadingMoreAgents.value = false;
    }
}

watch(() => searchAgent.value, async () => {
    isSearchingAgent.value = true;
    performDebouncedAgentSearch();
});

const performDebouncedAgentSearch = useDebounce(loadData);

const showAgentInfo = async (agent: AgentImpactItem) => {
    selectedAgent.value = agent;
    showAgentInfoModal.value = true;
    await loadTopUsers();
};

const loadTopUsers = async () => {
    loadingTopUsers.value = true;
    try{
        userPage.value = 1;
        const users = await api.getImpactTopUsers(props.fromDate, props.toDate, props.teamId, undefined, usersPageSize + 1, 0, selectedAgent.value?.agentId, selectedAgent.value?.isExternalAgent);
        topUsers.value = users.slice(0, usersPageSize);
        hasMoreUsers.value = users.length === usersPageSize + 1;
    } catch (error) {
        handleError(error);
    } finally {
        loadingTopUsers.value = false;
    }
}

const handleLoadMoreUsers = async () => {
    try{
        loadingMoreUsers.value = true;
        userPage.value++;
        const users = await api.getImpactTopUsers(props.fromDate, props.toDate, props.teamId, undefined, usersPageSize + 1, (userPage.value - 1) * usersPageSize, selectedAgent.value?.agentId, selectedAgent.value?.isExternalAgent);
        topUsers.value = [...topUsers.value, ...users.slice(0, usersPageSize)];
        hasMoreUsers.value = users.length === usersPageSize + 1;
    } catch (error) {
        handleError(error);
    } finally {
        loadingMoreUsers.value = false;
    }
}

const startChat = async () => {
  try {
    await newChat(new Agent(selectedAgent.value!.agentId, selectedAgent.value!.agentName));
    showAgentInfoModal.value = false;
  } catch (e) {
    handleError(e);
  }
};

watch(() => props.teamId, async () => {
    await loadAgentsData();
});
</script>

<template>
    <div v-if="loading" class="w-full">
        <div class="w-full bg-pale rounded-lg p-4 animate-pulse">
            <div class="h-5 bg-auxiliar-gray rounded w-32 mb-4"></div>
            <div>
                <div v-for="i in pageSize" :key="i" class="flex justify-between items-center py-2">
                    <div class="flex items-center gap-2">
                        <div class="h-8 w-8 bg-auxiliar-gray rounded-full"></div>
                        <div class="h-4 bg-auxiliar-gray rounded w-32"></div>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="h-4 bg-auxiliar-gray rounded w-16"></div>
                        <div class="h-4 bg-auxiliar-gray rounded w-8"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <DashboardCard v-else :title="t('agentsTitle')">
        <template #actions>
            <div class="flex items-center gap-4">
                <SimpleButton v-if="teamId == MY_TEAM_ID" shape="square"  @click="showRegisterExternalAgentModal = true">
                    <IconStopwatch/>
                    {{ t('externalAgentsButton') }}
                </SimpleButton>
                <InteractiveInput v-model="searchAgent" :placeholder="t('searchAgent')" start-icon="IconSearch"
                    :loading="isSearchingAgent" />
            </div>
        </template>
        <DataTable :value="topAgents" size="small">
            <Column field="agentName">
                <template #body="slotProps">
                    <div class="flex items-center gap-2" v-tooltip.top="slotProps.data.authorName ? `${t('author')}: ${slotProps.data.authorName}` : ''">
                        <div class="flex-shrink-0 flex items-center relative">
                            <AgentAvatar  v-if="!slotProps.data.isExternalAgent" :agent="slotProps.data" :show-shared-status="true" />
                            <DashboardExternalAgentAvatar v-else :external-agent="slotProps.data" :bordered="true" />
                        </div>
                        {{ slotProps.data.agentName }}
                    </div>
                </template>
            </Column>
            <Column field="minutesSaved" class="w-15">
                <template #body="slotProps">
                    <div class="flex items-center gap-1" :class="{'border-r-1 border-auxiliar-gray pr-4': teamId != MY_TEAM_ID}">
                        <DashboardTableDataComparisonCell
                            :previous-value="slotProps.data.previousMinutesSaved / 60"
                            :current-value="slotProps.data.minutesSaved / 60"
                            :value-tooltip="t('savedHoursTooltip')" icon="IconClock"
                            :number-decimals="1"
                            :compact-number="true"
                        />
                    </div>
                </template>
            </Column>
            <Column field="activeUsers" class="w-15" v-if="teamId != MY_TEAM_ID">
                <template #body="slotProps">
                    <div class="flex items-center gap-1">
                        <DashboardTableDataComparisonCell
                            :previous-value="slotProps.data.previousActiveUsers"
                            :current-value="slotProps.data.activeUsers"
                            :value-tooltip="t('activeUsersTooltip')"
                            icon="IconUsers"
                            :number-decimals="0"
                            :compact-number="true"
                        />
                    </div>
                </template>
            </Column>
            <Column field="" class="w-10" v-if="teamId != MY_TEAM_ID">
                <template #body="slotProps">
                    <div class="flex items-center gap-1 h-8">
                        <SimpleButton shape="square" size="small" variant="secondary" @click="showAgentInfo(slotProps.data)" v-tooltip.bottom="t('viewDetailsTooltip')">
                                <IconInfoCircle size="24" />
                        </SimpleButton>
                    </div>
                </template>
            </Column>
        </DataTable>
        <span v-if="topAgents.length === 0" class="text-light-gray">
            {{ t('noAgentsFound') }}
        </span>
        <template #footer>
            <SimpleButton v-if="hasMoreAgents" :disabled="loadingMoreAgents" @click="handleLoadMoreAgents"
                shape="rounded" shadow="gradient">
                <span v-if="loadingMoreAgents">{{ t('loadingMoreAgents') }}</span>
                <span v-else>{{ t('loadMoreAgents') }}</span>
            </SimpleButton>
        </template>
    </DashboardCard>
    <DashboardCardRecordDialog v-if="selectedAgent"
        :showModal="showAgentInfoModal"
        :title="selectedAgent.agentName"
        :has-more-data="hasMoreUsers"
        :loading-more-data="loadingMoreUsers"
        :is-loading="loadingTopUsers"
        @close="showAgentInfoModal = false"
        @load-more-data="handleLoadMoreUsers" >
            <template #avatar>
                <AgentAvatar :agent="new Agent(selectedAgent.agentId, selectedAgent.agentName, undefined, selectedAgent.icon, selectedAgent.iconBgColor)" size="normal"/>
            </template>
            <template #subtitle v-if="selectedAgent?.authorName">
                <span>{{ t('by') }} <span class="font-semibold">{{ selectedAgent?.authorName }}</span></span>
            </template>
            <template #summary>
                <div class="flex items-center gap-1 pr-4 border-r-1 border-auxiliar-gray">
                    <DashboardTableDataComparisonCell
                        :previous-value="selectedAgent.previousMinutesSaved / 60"
                        :current-value="selectedAgent.minutesSaved / 60"
                        :value-tooltip="t('savedHoursTooltip')" icon="IconClock"
                        :number-decimals="2"
                        :compact-number="true"
                    />
                </div>
                <div class="flex items-center gap-1">
                    <DashboardTableDataComparisonCell
                        :previous-value="selectedAgent.previousActiveUsers"
                        :current-value="selectedAgent.activeUsers"
                        :value-tooltip="t('activeUsersTooltip')"
                        icon="IconUsers"
                        :number-decimals="0"
                        :compact-number="true"
                    />
                </div>
            </template>
            <template #details>
                <span class="text-md font-medium">{{ t('usersTitle') }}</span>
                <DataTable :value="topUsers" size="small" :show-headers="false" class="max-h-[369px] overflow-y-auto" >
                    <Column field="userName">
                        <template #body="slotProps">
                            <div class="flex items-center gap-2">
                                {{ slotProps.data.userName }}
                            </div>
                        </template>
                    </Column>
                    <Column field="minutesSaved" class="w-15">
                        <template #body="slotProps">
                            <div class="flex items-center gap-1">
                                <DashboardTableDataComparisonCell
                                    :previous-value="slotProps.data.previousMinutesSaved / 60"
                                    :current-value="slotProps.data.minutesSaved / 60"
                                    :value-tooltip="t('savedHoursTooltip')" icon="IconClock"
                                    :number-decimals="2"
                                    :compact-number="true"
                                />
                            </div>
                        </template>
                    </Column>
                    <template #empty>
                        <div class="p-4 text-center text-gray-500">
                        {{ t('noUsersFound') }}
                        </div>
                    </template>
                </DataTable>
            </template>
            <template #footerAction v-if="selectedAgent.agentId !== PRIVATE_AGENT_ID && !selectedAgent.isExternalAgent">
                <SimpleButton size="small" shape="square" class="px-3" @click="startChat" variant="primary">
                    {{ t('startChatButtonLabel') }}
                    <IconArrowUpRight />
                </SimpleButton>
            </template>
    </DashboardCardRecordDialog>
    <DashboardRegisterExternalAgentModal :show-modal="showRegisterExternalAgentModal" @update:show-modal="showRegisterExternalAgentModal = $event" @new-external-agent-entry="loadAgentsData" />
</template>

<i18n lang="json">
{
    "en": {
        "agentsTitle": "Agents",
        "loadingMoreAgents": "Loading more agents...",
        "loadMoreAgents": "Load more agents",
        "searchAgent": "Search agent",
        "noAgentsFound": "No agents found",
        "savedHoursTooltip": "Total estimated hours saved in the last 30 days",
        "activeUsersTooltip": "Total number of active users in the last 30 days",
        "author": "Created by",
        "privateAgents": "Private agents",
        "externalAgentsButton": "Register other agents",
        "noUsersFound": "No users found",
        "usersTitle": "Users",
        "startChatButtonLabel": "Use now",
        "viewDetailsTooltip": "View details"
    },
    "es": {
        "agentsTitle": "Agentes",
        "loadingMoreAgents": "Cargando más agentes...",
        "loadMoreAgents": "Cargar más agentes",
        "searchAgent": "Buscar agente",
        "noAgentsFound": "No se encontraron agentes",
        "savedHoursTooltip": "Horas totales estimadas ahorradas en los últimos 30 días",
        "activeUsersTooltip": "Total de usuarios activos en los ultimos 30 dias",
        "author": "Creado por",
        "privateAgents": "Agentes privados",
        "externalAgentsButton": "Registrar otros agentes",
        "noUsersFound": "No se encontraron usuarios",
        "usersTitle": "Usuarios",
        "startChatButtonLabel": "Usar ahora",
        "viewDetailsTooltip": "Ver detalles"
    }
}
</i18n>
