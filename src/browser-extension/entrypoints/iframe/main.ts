import { browser } from 'wxt/browser'
import { createApp, type Component } from "vue"
import { createI18n } from "vue-i18n"
import PrimeVue from 'primevue/config'
import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import Toast from "vue-toastification"
import "vue-toastification/dist/index.css"
import * as TablerIcons from '@tabler/icons-vue'
import "~/assets/styles.css"
import clickOutside from '../../../common/src/utils/clickOutside'

import App from "./App.vue"

const i18n = createI18n({
  legacy: false,
  locale: (await browser.i18n.getAcceptLanguages())[0],
  fallbackLocale: "en",
  missingWarn: false,
  fallbackWarn: false
})

const app = createApp(App)
const primeTheme = definePreset(Aura)
for (const [name, component] of Object.entries(TablerIcons)) {
  app.component(name, component as Component)
}
app.use(i18n)
app.use(PrimeVue, {
  theme: {
    preset: primeTheme,
    options: {
      darkModeSelector: false || 'none',
    }
  }
})
app.use(Toast, {})
app.directive('click-outside', clickOutside);
app.mount("body")

let elem: HTMLBodyElement = document.getElementsByTagName("body")[0]
elem!.onbeforeunload = () => app.unmount()
