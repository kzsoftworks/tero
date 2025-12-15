<script setup lang="ts">
import { ref } from 'vue';
import type { MenuItem } from 'primevue/menuitem';
import SimpleButton from '../../../../common/src/components/common/SimpleButton.vue';
import MenuItemTemplate from '../../../../common/src/components/common/MenuItemTemplate.vue';

defineProps<{
  items?: MenuItem[];
}>();

const menu = ref();
const isMenuOpen = ref(false);

const emit = defineEmits<{
  (e: 'toggleActive'): void;
  (e: 'closeMenu'): void;
}>();

const toggle = (event: Event) => {
  menu.value?.toggle(event);
  emit('toggleActive');
};

const closeMenu = () => {
  menu.value?.hide();
}

const handleShow = () => {
  isMenuOpen.value = true;
};

const handleHide = () => {
  isMenuOpen.value = false;
  emit('closeMenu');
};

defineExpose({
  menu,
  isMenuOpen,
  toggle
});
</script>

<template>
  <div v-click-outside="closeMenu">
    <SimpleButton
      class="rounded-lg"
      variant="muted"
      size="small"
      @click.stop.prevent="toggle">
      <IconDots stroke-width="2" :class="!isMenuOpen ? 'text-light-gray' : 'text-abstracta'" />
    </SimpleButton>

    <Menu
      ref="menu"
      :model="items ?? []"
      :popup="true"
      @show="handleShow"
      @hide="handleHide"
      @keydown.esc="closeMenu">
      <template #item="{ item }">
        <MenuItemTemplate :item="item"/>
      </template>
    </Menu>
  </div>
</template>
