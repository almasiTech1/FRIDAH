<template>
  <div class="space-y-4">
    <div v-if="loading" class="space-y-3" aria-busy="true">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-28 bg-gray-100 rounded-xl" />
    </div>

    <div v-else-if="error" class="card card-body text-center py-10" role="alert">
      <p class="text-red-600 font-medium">{{ error }}</p>
      <button class="btn-outline border-gray-200 mt-3 mx-auto" @click="load">Try again</button>
    </div>

    <div v-else-if="!items.length" class="card card-body text-center py-12 text-gray-400">
      {{ role === 'admin' ? 'Nothing is waiting for admin review.' : 'No properties are waiting for your approval.' }}
    </div>

    <div v-else class="space-y-3 stagger">
      <div v-for="p in items" :key="p.id" class="card card-body">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-gray-900">{{ p.name }}</p>
              <span class="badge" :class="statusColor(p.review_state)">{{ reviewStateLabel(p.review_state) }}</span>
              <span class="badge badge-gray">v{{ p.submission_version }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ p.town }}, {{ p.county }}
              <template v-if="p.submitted_by_agency"> · Submitted by {{ p.submitted_by_agency }}</template>
              <template v-if="role === 'admin'"> · Owner {{ p.landlord_name }}</template>
            </p>
            <p class="text-xs mt-1" :class="p.age_days >= 3 ? 'text-orange-600 font-medium' : 'text-gray-400'">
              Waiting {{ p.age_days }} day{{ p.age_days === 1 ? '' : 's' }}
            </p>
            <p v-if="p.requires_landlord_approval" class="text-xs text-gray-500 mt-1">
              Needs: <strong>{{ p.missing_approvals.map(partyLabel).join(' and ') }}</strong> approval
              before it can go live.
            </p>
          </div>

          <div class="flex items-center gap-2 flex-wrap">
            <button class="btn-outline border-gray-200 text-xs" @click="toggleHistory(p.id)">
              {{ openHistory === p.id ? 'Hide history' : 'History' }}
            </button>
            <button class="btn bg-emerald-600 text-white hover:bg-emerald-700" :disabled="busy === p.id"
                    @click="decide(p, 'approve')">Approve</button>
            <button class="btn-outline border-blue-200 text-blue-700" :disabled="busy === p.id"
                    @click="startComment(p.id, 'request_changes')">Request changes</button>
            <button class="btn-outline border-red-200 text-red-600" :disabled="busy === p.id"
                    @click="startComment(p.id, 'reject')">Reject</button>
          </div>
        </div>

        <form v-if="pending?.id === p.id" class="mt-4 space-y-2" @submit.prevent="submitComment(p)">
          <label class="text-sm font-medium text-gray-700" :for="`c-${p.id}`">
            {{ pending?.action === 'reject' ? 'Why are you rejecting this property?' : 'What needs to change?' }}
          </label>
          <textarea :id="`c-${p.id}`" v-model="comment" class="input" rows="3" required
                    placeholder="Required - the submitter will see this" />
          <div class="flex gap-2">
            <button type="submit" class="btn bg-gray-900 text-white" :disabled="!comment.trim() || busy === p.id">Send</button>
            <button type="button" class="btn-outline border-gray-200" @click="pending = null">Cancel</button>
          </div>
        </form>

        <div v-if="openHistory === p.id" class="mt-4 pt-3 border-t border-gray-100">
          <p v-if="!history.length" class="text-xs text-gray-400">No history yet.</p>
          <ol v-else class="space-y-2">
            <li v-for="h in history" :key="h.id" class="text-xs text-gray-600 flex gap-2">
              <span class="text-gray-400 w-32 shrink-0">{{ formatDate(h.created_at) }}</span>
              <span>
                <strong>{{ partyLabel(h.party) }}</strong>
                {{ h.decision.replace('_', ' ') }} (v{{ h.submission_version }})
                <template v-if="h.actor_name"> by {{ h.actor_name }}</template>
                <template v-if="h.comment"> - "{{ h.comment }}"</template>
              </span>
            </li>
          </ol>
        </div>
      </div>
    </div>

    <p v-if="message" class="text-sm text-emerald-700" role="status">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { approvalApi } from '@/api/services'
import { statusColor, formatDate, reviewStateLabel, partyLabel } from '@/utils/formatters'

const props = defineProps<{ role: 'landlord' | 'admin' }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const items = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref<string | null>(null)
const message = ref('')
const pending = ref<{ id: string; action: 'reject' | 'request_changes' } | null>(null)
const comment = ref('')
const openHistory = ref<string | null>(null)
const history = ref<any[]>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await approvalApi.queue()
    items.value = (res.data as any).data?.results || []
  } catch {
    error.value = 'Could not load the review queue.'
  } finally {
    loading.value = false
  }
}

function startComment(id: string, action: 'reject' | 'request_changes') {
  pending.value = { id, action }
  comment.value = ''
}

async function send(p: any, action: 'approve' | 'reject' | 'request_changes', text = '') {
  busy.value = p.id
  message.value = ''
  try {
    if (props.role === 'admin') await approvalApi.adminDecision(p.id, action, text)
    else await approvalApi.landlordDecision(p.id, action, text)
    message.value = action === 'approve' ? `"${p.name}" approved.` : `"${p.name}": your feedback was sent.`
    pending.value = null
    await load()
    emit('changed')
  } catch (e: any) {
    error.value = e?.response?.data?.error?.message || e?.response?.data?.detail || 'That action failed.'
  } finally {
    busy.value = null
  }
}

const decide = (p: any, action: 'approve') => send(p, action)
const submitComment = (p: any) => pending.value && send(p, pending.value.action, comment.value.trim())

async function toggleHistory(id: string) {
  if (openHistory.value === id) { openHistory.value = null; return }
  openHistory.value = id
  history.value = []
  try {
    const res = await approvalApi.history(id)
    history.value = (res.data as any).data?.results || (res.data as any).results || []
  } catch { history.value = [] }
}

onMounted(load)
</script>
