<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MenuItem } from 'primevue/menuitem'
import { IconRefresh, IconTrashX } from '@tabler/icons-vue'
import Menu from 'primevue/menu'
import { IconDots } from '@tabler/icons-vue'

const { t } = useI18n()

const props = defineProps<{
  hubUrl?: string
  type?: 'hub' | 'agent'
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'remove'): void
}>()

const menu = ref()
const isMenuOpen = ref(false)

const handleCloseMenu = () => {
  isMenuOpen.value = false
}

const items = computed<MenuItem[]>(() => [
  {
    label: props.type === 'agent' ? t('refreshAgent') : t('refreshHub'),
    tablerIcon: IconRefresh,
    command: () => {
      emit('refresh')
      handleCloseMenu()
    }
  },
  {
    label: props.type === 'agent' ? t('removeAgent') : t('removeHub'),
    tablerIcon: IconTrashX,
    command: () => {
      emit('remove')
      handleCloseMenu()
    }
  }
])

const handleMenuToggle = (event: Event) => {
  menu.value?.toggle(event)
}
</script>

<template>
  <div class="flex items-center">
    <SimpleButton class="rounded-lg" variant="muted" size="small" @click.prevent="handleMenuToggle($event)">
      <IconDots stroke-width="2" :class="isMenuOpen ? 'text-abstracta' : 'text-light-gray'" />
    </SimpleButton>
    <Menu ref="menu" :model="items" :popup="true" @show="isMenuOpen = true" @hide="handleCloseMenu" @keydown.esc="handleCloseMenu">
      <template #item="{ item }">
        <MenuItemTemplate :item="item" />
      </template>
    </Menu>
  </div>
</template>

<i18n lang="json">
{
  "en": {
    "refreshHub": "Refresh",
    "removeHub": "Remove",
    "refreshAgent": "Refresh",
    "removeAgent": "Remove"
  },
  "es": {
    "refreshHub": "Refrescar",
    "removeHub": "Eliminar",
    "refreshAgent": "Refrescar",
    "removeAgent": "Eliminar"
  }
}
</i18n>
