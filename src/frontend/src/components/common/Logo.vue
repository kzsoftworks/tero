<script setup lang="ts">
import logo from '@/assets/images/logo.webp'

withDefaults(defineProps<{
    width?: string,
    height?: string
}>(), {
    width: 'auto',
    height: '56px'
});
</script>

<template>
  <img :src="logo" alt="Logo" :style="{ width: width, height: height }" class="object-contain hidden md:block"/>
</template>
