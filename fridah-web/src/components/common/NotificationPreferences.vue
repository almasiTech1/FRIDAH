<template>
  <section class="card card-body space-y-4" aria-labelledby="np-title">
    <div>
      <h2 id="np-title" class="font-semibold text-gray-900">Notifications</h2>
      <p class="text-xs text-gray-500">Choose how Fridah reaches you. Payment reminders are held back during your quiet hours.</p>
    </div>
    <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>
    <div v-if="loading" class="animate-pulse h-24 bg-gray-100 rounded-lg" aria-busy="true" />
    <form v-else class="space-y-3" @submit.prevent="save">
      <label v-for="t in toggles" :key="t.key" class="flex items-center justify-between text-sm text-gray-700">
        <span>{{ t.label }}</span>
        <input v-model="prefs[t.key]" type="checkbox" class="h-4 w-4" />
      </label>
      <div class="grid grid-cols-2 gap-3 pt-2">
        <div><label class="text-xs font-medium text-gray-600" for="qh-start">Quiet hours start</label>
          <input id="qh-start" v-model="prefs.quiet_hours_start" type="time" class="input" /></div>
        <div><label class="text-xs font-medium text-gray-600" for="qh-end">Quiet hours end</label>
          <input id="qh-end" v-model="prefs.quiet_hours_end" type="time" class="input" /></div>
      </div>
      <p class="text-xs text-gray-400">Leave both empty to use the default (9 pm – 7 am).</p>
      <div class="flex items-center gap-3">
        <button class="btn bg-gray-900 text-white" :disabled="saving">{{ saving ? 'Saving…' : 'Save preferences' }}</button>
        <span v-if="saved" class="text-sm text-emerald-700" role="status">Saved</span>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { notificationsApi } from '@/api/services'

const toggles = [
  { key: 'sms_enabled', label: 'SMS messages' },
  { key: 'push_enabled', label: 'Push notifications' },
  { key: 'email_enabled', label: 'Email' },
  { key: 'payment_alerts', label: 'Rent & payment reminders (SMS/push)' },
  { key: 'maintenance_alerts', label: 'Maintenance updates' },
] as const

const prefs = reactive<Record<string, any>>({ quiet_hours_start: '', quiet_hours_end: '' })
const loading = ref(true); const saving = ref(false); const saved = ref(false); const error = ref('')
const hhmm = (v: string | null) => (v ? v.slice(0, 5) : '')

onMounted(async () => {
  try {
    const { data } = await notificationsApi.preferences()
    const d: any = (data as any).data || data
    Object.assign(prefs, d, { quiet_hours_start: hhmm(d.quiet_hours_start), quiet_hours_end: hhmm(d.quiet_hours_end) })
  } catch { error.value = 'Could not load your preferences.' } finally { loading.value = false }
})

async function save() {
  error.value = ''
  if (!!prefs.quiet_hours_start !== !!prefs.quiet_hours_end) { error.value = 'Set both quiet-hours times, or leave both empty.'; return }
  saving.value = true; saved.value = false
  try {
    await notificationsApi.updatePreferences({
      ...Object.fromEntries(toggles.map((t) => [t.key, !!prefs[t.key]])),
      quiet_hours_start: prefs.quiet_hours_start || null, quiet_hours_end: prefs.quiet_hours_end || null,
    } as any)
    saved.value = true; setTimeout(() => (saved.value = false), 2500)
  } catch { error.value = 'Could not save your preferences.' } finally { saving.value = false }
}
</script>
