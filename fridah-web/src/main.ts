import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { useThemeStore } from './stores/theme'
import { vReveal } from './directives/reveal'
import { vSpot } from './directives/spot'
import './assets/main.css'
import './assets/skins.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(i18n)
app.directive('reveal', vReveal)
app.directive('spot', vSpot)
app.mount('#app')

useThemeStore(pinia).init()
