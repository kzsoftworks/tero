<script lang="ts" setup>
import { onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const { t } = useI18n();

onBeforeMount(() => {
  const { state, error, code } = route.query;
  const channel = new BroadcastChannel('oauth_channel');
  try {
    channel.postMessage({
      type: 'oauth_callback',
      toolId: route.params.toolId,
      state: state,
      error: error,
      code: code,
    });
  } finally {
    channel.close();
    window.close();
  }
});
</script>

<template>
  <div class="flex items-center justify-center h-screen">
    <p>{{ t('processingAuthentication') }}</p>
  </div>
</template>

<i18n lang="json">
  {
    "en": {
      "processingAuthentication": "Processing authentication..."
    },
    "es": {
      "processingAuthentication": "Procesando autenticación..."
    }
  }
</i18n>
