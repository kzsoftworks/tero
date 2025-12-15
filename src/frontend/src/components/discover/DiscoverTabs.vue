<script lang="ts" setup>
import { ref, onMounted, computed, watch } from 'vue'
import type { Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Agent, ApiService, Team } from '@/services/api';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useDebounce } from '@/composables/useDebounce';
import { useAgentStore } from '@/composables/useAgentStore';
import { IconSparkles, IconEdit, IconSearch, IconLayoutGrid } from '@tabler/icons-vue';
import { AnimationEffect } from '../../../../common/src/utils/animations';
import UserTeamsSelect from '@/components/common/UserTeamsSelect.vue';

const { t } = useI18n();
const { handleError } = useErrorHandler();
const { agentsStore } = useAgentStore();

const shouldAnimate = ref(true);
const activeIndex = ref(0);
const tabIsChanging = ref(false);
enum SortOption {
  MOST_USED = 'mostUsed',
  NEWEST = 'newest'
}
const sortBy = ref<SortOption>(SortOption.MOST_USED);
const sortByOptions = [
  { id: SortOption.MOST_USED, name: t('topUsedAgents') },
  { id: SortOption.NEWEST, name: t('newestAgents') }
];
const myAgents = ref<Agent[]>([]);
const searchResults = ref<Agent[]>([]);
const discoverAgents = ref<Agent[]>([]);
const allAgents = ref<Agent[]>([]);
const discoverMostUsedAgents = ref<Agent[]>([]);
const discoverNewestAgents = ref<Agent[]>([]);
const isLoading = ref(false);
const loadingMoreAgents = ref(false);
const showCreateAgentOption = ref(true);
const defaultPageLimit = 12;
const defaultVisualPageLimit = defaultPageLimit + 1; // We need this to check if we should show the load more button
const team = ref<number | null>(1);
const defaultTeamOptions = ref<Team[]>([new Team(1, t('global'))]);
const userTeamsSelectRef = ref<InstanceType<typeof UserTeamsSelect>[]>([]);

const emit = defineEmits<{
  (e: 'searching', value: boolean): void
}>();

const props = defineProps<{
  searchQuery: string;
  isSearching: boolean;
}>();

enum TabId {
  SEARCH = 'search',
  DISCOVER = 'discover',
  ALL = 'all',
  OWN = 'own'
}

type TabState = {
  initialized: boolean;
  offset: number;
  hasMore: boolean;
};

type TabStates = Record<TabId, TabState>;

const createInitialTabState = (): TabState => ({
  initialized: false,
  offset: 0,
  hasMore: false
});

const tabStates = ref<TabStates>(
  Object.values(TabId).reduce(
    (item, tabId) => ({
      ...item,
      [tabId]: createInitialTabState()
    }),
    {} as TabStates
  )
);

const baseTabs = [
  {
    id: TabId.DISCOVER,
    icon: IconSparkles,
    label: 'discoverAgents',
    agents: discoverAgents
  },
  {
    id: TabId.ALL,
    icon: IconLayoutGrid,
    label: 'allAgents',
    agents: allAgents
  },
  {
    id: TabId.OWN,
    icon: IconEdit,
    label: 'myAgents',
    agents: myAgents
  }
];

const resetAnimation = () => {
  shouldAnimate.value = false;
  setTimeout(() => {
    shouldAnimate.value = true;
  }, 150);
};

const handleTabChange = async() => {
  const tabId = currentTabId.value;

  if (!tabStates.value[tabId].initialized) {
    await loadAgents();
    tabStates.value[tabId].initialized = true;
  }

  // We need to check if the tab is changing
  // to avoid showing the load more button flickering
  tabIsChanging.value = true;
  setTimeout(() => {
    tabIsChanging.value = false;
  }, 500);

  resetAnimation();
}

const emitSearching = (value: boolean) => {
  emit('searching', value);
}

const clearSearchResults = () => {
  searchResults.value = [];
  tabStates.value.search.offset = 0;
  activeIndex.value = 0;
}

const performSearch = async (query: string) => {
  if (!query) {
    emitSearching(false);
    return;
  }

  try {
    tabStates.value.search.initialized = false;
    await loadAgents();
    tabStates.value.search.initialized = true;
  } catch (error) {
    emitSearching(false);
    handleError(error);
  } finally {
    emitSearching(false);
    showCreateAgentOption.value = true;
  }
};

const loadMoreAgents = async() => {
  loadingMoreAgents.value = true;
  await loadAgents();
  loadingMoreAgents.value = false;
}

const handlePagination = (tab: TabState, agents: Agent[], targetArray: Ref<Agent[]>) => {
  tab.hasMore = agents.length > defaultPageLimit;
  agents = agents.slice(0, defaultPageLimit)
  targetArray.value = [...targetArray.value, ...agents];
  tab.offset += agents.length;
}

const loadAgents = async () => {
  const api = new ApiService();
  const tabId = currentTabId.value;
  try {
    isLoading.value = true;
    let agents: Agent[] = [];
    const tabState = tabStates.value[tabId];
    const offset = tabState.offset;

    switch (tabId) {
      case TabId.DISCOVER:
        const [topUsed, newest] = await Promise.all([
          api.findTopUsedAgents(3, 0),
          api.findNewestAgents(3, 0)
        ]);
        discoverMostUsedAgents.value = topUsed;
        discoverNewestAgents.value = newest;
        break;
      case TabId.ALL:
        if (sortBy.value === SortOption.MOST_USED) {
          agents = await api.findTopUsedAgents(defaultVisualPageLimit, offset, team.value);
        } else {
          agents = await api.findNewestAgents(defaultVisualPageLimit, offset, team.value);
        }
        handlePagination(tabState, agents, allAgents);
        break;
      case TabId.OWN:
        agents = await api.findOwnAgents(defaultVisualPageLimit, offset);
        handlePagination(tabState, agents, myAgents);
        break;
      case TabId.SEARCH:
        if (props.searchQuery) {
          agents = await api.findAgentsByText(props.searchQuery, defaultVisualPageLimit, offset);
          handlePagination(tabState, agents, searchResults);
        }
        break;
    }
  } catch (error) {
    handleError(error);
  } finally {
    isLoading.value = false;
  }
};

const handleSortChange = async() => {
  allAgents.value = [];
  tabStates.value.all.offset = 0;
  await loadAgents();
}

const tabs = computed(() => {
  if (props.searchQuery) {
    return [
      {
        id: TabId.SEARCH,
        icon: IconSearch,
        label: 'searchResults',
        agents: searchResults
      },
      ...baseTabs
    ];
  }

  return baseTabs;
});

const currentTabId = computed<TabId>(() => {
  return tabs.value[Number(activeIndex.value)]?.id;
});

const currentAgents = computed<Agent[]>(() => {
  const tab = tabs.value[Number(activeIndex.value)];
  if (!tab || !tab.agents) return [];
  return tab.agents.value;
});

const showLoadMoreButton = computed(() => {
  if(isLoading.value || tabIsChanging.value || props.isSearching) return false;
  return tabStates.value[currentTabId.value].hasMore;
});

const debouncedSearch = useDebounce(() => {
  performSearch(props.searchQuery);
});

watch(() => props.searchQuery, (newQuery) => {
  if (newQuery || currentTabId.value != TabId.SEARCH) {
    clearSearchResults();
  }
  emitSearching(true);
  // Fix for when the user clears the search query
  // and the create agent button has to be shown
  if (!props.searchQuery) showCreateAgentOption.value = true;
  else showCreateAgentOption.value = false;

  debouncedSearch();
});

watch(() => agentsStore.agents, () => {
  if (currentTabId.value === TabId.OWN) {
    myAgents.value = myAgents.value.filter(agent => agent.team || agentsStore.agents.some(a => a.id === agent.id));
  }
});

watch(() => team.value, () => {
  allAgents.value = [];
  tabStates.value.all.offset = 0;
  loadAgents();
});

const refreshTabs = async () => {
  Object.keys(tabStates.value).forEach(tabId => {
    tabStates.value[tabId as TabId] = createInitialTabState();
  });

  myAgents.value = [];
  searchResults.value = [];
  discoverAgents.value = [];
  allAgents.value = [];
  discoverMostUsedAgents.value = [];
  discoverNewestAgents.value = [];

  await loadAgents();
  tabStates.value[currentTabId.value].initialized = true;

  for (const userTeamsSelect of userTeamsSelectRef.value) {
    await userTeamsSelect?.refreshTeams();
  }
};

defineExpose({
  refreshTabs
});

onMounted(async () => {
  await loadAgents();
  tabStates.value[currentTabId.value].initialized = true;
});

</script>

<template>
  <div class="flex flex-col items-center">
    <div class="w-auto">
      <Tabs :value="activeIndex" @update:value="($event) => {
          activeIndex = Number($event);
          handleTabChange();
        }">
        <TabList>
          <Tab v-for="tab in tabs" :key="tab.id" :value="tabs.indexOf(tab)">
            <div class="flex items-center gap-2 mx-1">
              <component :is="tab.icon" />
              <span>{{ t(tab.label) }}</span>
            </div>
          </Tab>
        </TabList>
        <div class="overflow-y-auto">
        <TabPanel v-for="tab in tabs" :key="tab.id" :value="tabs.indexOf(tab)">
          <div class="h-[calc(100vh-240px)] flex flex-col relative">
            <div class="flex-1">
              <div class="grid-wrapper pb-16">
                <div v-if="currentTabId === TabId.ALL" class="flex flex-row justify-between items-center gap-2">
                  <div class="flex flex-row items-center gap-2">
                    <span class="text-light-gray">{{ t('sortBy') }}:</span>
                    <Select
                      id="sortBy"
                      v-model="sortBy"
                      :options="sortByOptions"
                      option-label="name"
                      option-value="id"
                      class="w-40"
                      @change="handleSortChange"
                    />
                  </div>
                  <div class="flex flex-row items-center gap-2">
                    <span class="text-light-gray">{{ t('team') }}:</span>
                    <UserTeamsSelect v-model="team" ref="userTeamsSelectRef" :default-teams="defaultTeamOptions" :default-selected-team="team" />
                  </div>
                </div>
                <div v-if="currentTabId === TabId.DISCOVER">
                  <div v-for="(section, index) in [
                        { title: 'topUsedAgents', agents: discoverMostUsedAgents },
                        { title: 'newestAgents', agents: discoverNewestAgents }
                      ]"
                      :key="section.title"
                      class="mb-8">
                      <Animate
                        v-if="!isLoading"
                        :effect="AnimationEffect.SLIDE_IN_LEFT_SPRING"
                        :index="index"
                        :enabled="shouldAnimate">
                        <h4 class="text-light-gray">{{ t(section.title) }}</h4>
                      </Animate>
                      <div class="column-gap !py-2">
                        <template v-for="(agent, agentIndex) in section.agents" :key="agentIndex">
                          <Animate
                            :effect="AnimationEffect.SLIDE_UP"
                            :index="agentIndex"
                            :enabled="shouldAnimate">
                            <DiscoverAgent :agent="agent" :show-team-badge="true" />
                          </Animate>
                        </template>
                      </div>
                    </div>
                </div>
                <div v-else-if="currentTabId === TabId.SEARCH && !currentAgents.length" class="flex flex-col items-center justify-center h-64 col text-center">
                  <div class="text-light-gray mb-4">
                    <IconSearch size="48" :class="{ 'animate-magnify-search': isSearching }" />
                  </div>
                  <h3 class="text-light-gray mb-2">{{ isSearching ? t('searchingAgents') : t('noAgentsFound') }}</h3>
                  <p class="text-light-gray/70 max-w-md">{{ isSearching ? t('searchingAgentsDescription') : t('noAgentsFoundDescription') }}</p>
                </div>
                <div v-else-if="currentTabId === TabId.OWN && !currentAgents.length && !isLoading" class="flex flex-col items-center text-center">
                  <p class="text-light-gray pt-5">{{ t('noAgentsCreated') }}</p>
                </div>
                <div class="column-gap" v-else>
                  <DiscoverSkeleton v-if="isLoading && !loadingMoreAgents" />
                  <template v-else>
                    <template v-for="(agent, index) in currentAgents" :key="index">
                      <Animate
                        :effect="AnimationEffect.SLIDE_UP"
                        :index="index"
                        :enabled="shouldAnimate">
                        <DiscoverAgent :agent="agent" :show-team-badge="currentTabId === TabId.SEARCH || currentTabId === TabId.OWN" />
                      </Animate>
                    </template>
                  </template>
                </div>
              </div>
            </div>
            <GradientBottom>
              <Animate :effect="AnimationEffect.SLIDE_UP" :key="`load-more-button-${shouldAnimate}`" :index="1" :base-delay="800" :enabled="shouldAnimate">
                <SimpleButton
                  shape="rounded"
                  v-if="showLoadMoreButton"
                  @click="loadMoreAgents"
                  class="w-xs">
                  {{ t('seeMoreAgents') }}
                </SimpleButton>
              </Animate>
            </GradientBottom>
          </div>
        </TabPanel>
       </div>
      </Tabs>
    </div>
  </div>
</template>

<i18n lang="json">
  {
    "en": {
      "discoverAgents": "Discover",
      "allAgents": "All",
      "topUsedAgents": "Most used",
      "newestAgents": "Latest",
      "myAgents": "My agents",
      "searchResults": "Results",
      "seeMoreAgents": "See more agents",
      "sortBy": "Sort by",
      "team": "Team",
      "global": "Global",
      "searchingAgents": "Searching agents",
      "searchingAgentsDescription": "We are searching agents that match your search",
      "noAgentsFound": "No agents found",
      "noAgentsFoundDescription": "We couldn't find any agents that match your search. Please try a different search term",
      "noAgentsCreated": "You haven't created agents"
    },
    "es": {
      "discoverAgents": "A descubrir",
      "allAgents": "Todos",
      "topUsedAgents": "Más usados",
      "newestAgents": "Nuevos",
      "myAgents": "Mis agentes",
      "searchResults": "Resultados",
      "seeMoreAgents": "Ver más agentes",
      "sortBy": "Ordenar por",
      "team": "Equipo",
      "global": "Global",
      "searchingAgents": "Buscando agentes",
      "searchingAgentsDescription": "Estamos buscando agentes que coincidan con tu búsqueda",
      "noAgentsFound": "No se encontraron agentes",
      "noAgentsFoundDescription": "No pudimos encontrar agentes que coincidan con tu búsqueda. Por favor, intenta con otro término de búsqueda",
      "noAgentsCreated": "No has creado agentes"
    }
  }
</i18n>
