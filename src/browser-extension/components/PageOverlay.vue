<script lang="ts" setup>
import headerBg from '../assets/header.webp'

defineProps<{ minimized?: boolean }>()
</script>

<template>
    <div class="h-full flex flex-col">
        <div v-if="minimized">
            <slot name="minimizedContent" />
        </div>
        <div v-else>
            <div class="flex flex-row items-center p-2 bg-cover bg-center bg-no-repeat rounded-tl-3xl text-white"
                :style="`background-image: url(${headerBg})`">
                <img src="../assets/logo.webp" style="height: 48px" />
                <div class="flex-auto text-right items-center justify-end flex gap-4">
                    <slot name="headerActions"/>
                </div>
            </div>
            <div class="border-t border-gray-300 absolute left-0 right-0"></div>
        </div>
        <main v-if="!minimized" class="grow overflow-y-auto overflow-x-hidden p-2">
            <slot name="content" />
        </main>
        <slot name="modalsContainer" />
        <slot name="footer" />
    </div>
</template>
