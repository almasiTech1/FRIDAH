<template>
  <div class="flex h-[calc(100vh-8rem)] gap-4">
    <!-- Thread list -->
    <div class="w-80 flex-shrink-0 card overflow-hidden flex flex-col">
      <div class="p-4 border-b border-gray-100 flex items-center justify-between">
        <h2 class="font-bold text-gray-900">Chats</h2>
        <button class="btn-outline border-gray-200 text-xs" @click="showNewChat = !showNewChat">+ New</button>
      </div>

      <!-- New chat picker -->
      <div v-if="showNewChat" class="p-3 border-b border-gray-100 bg-gray-50 space-y-2 max-h-72 overflow-y-auto">
        <div v-if="canCreateGroups" class="flex gap-1 bg-white rounded-lg p-0.5 mb-2">
          <button :class="['flex-1 text-xs py-1.5 rounded-md font-medium', newChatTab === 'direct' ? `bg-${accent}-600 text-white` : 'text-gray-500']"
            @click="newChatTab = 'direct'">Direct Message</button>
          <button :class="['flex-1 text-xs py-1.5 rounded-md font-medium', newChatTab === 'group' ? `bg-${accent}-600 text-white` : 'text-gray-500']"
            @click="newChatTab = 'group'; loadMyProperties()">Group Chat</button>
        </div>

        <!-- Direct -->
        <template v-if="newChatTab === 'direct'">
          <p v-if="loadingRelationships" class="text-xs text-gray-400">Loading contacts…</p>
          <p v-else-if="!relationships.length" class="text-xs text-gray-400">
            No contacts yet — you'll see people here once you have an active lease, tenancy, or assignment.
          </p>
          <button v-for="r in relationships" :key="r.id" class="w-full text-left px-3 py-2 rounded-lg hover:bg-white flex items-center gap-2 text-sm"
            @click="openNewChat(r.id)">
            <span :class="`w-7 h-7 rounded-full bg-${accent}-100 text-${accent}-700`" class="flex items-center justify-center text-xs font-bold flex-shrink-0">{{ r.name[0]?.toUpperCase() }}</span>
            <span class="flex-1 truncate">{{ r.name }}</span>
            <span class="text-xs text-gray-400 capitalize">{{ r.relationships[0] }}</span>
          </button>
        </template>

        <!-- Group -->
        <template v-else>
          <div>
            <label class="text-xs text-gray-500 font-medium">Property</label>
            <select v-model="groupForm.property_id" class="input text-sm mt-0.5">
              <option value="" disabled>Select a property</option>
              <option v-for="p in myProperties" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div>
            <label class="text-xs text-gray-500 font-medium">Group Name</label>
            <input v-model="groupForm.subject" class="input text-sm mt-0.5" placeholder="e.g. Sunset Apartments Tenants"/>
          </div>
          <div>
            <label class="text-xs text-gray-500 font-medium">Add People</label>
            <div class="max-h-24 overflow-y-auto mt-0.5 space-y-1">
              <label v-for="r in relationships" :key="r.id" class="flex items-center gap-2 text-sm px-1 py-1 rounded hover:bg-white cursor-pointer">
                <input type="checkbox" :value="r.id" v-model="groupForm.participant_ids" class="rounded"/>
                <span class="truncate">{{ r.name }}</span>
              </label>
            </div>
          </div>
          <button :class="`bg-${accent}-600 hover:bg-${accent}-700`" class="btn-primary w-full text-sm" :disabled="!groupForm.property_id || creatingGroup" @click="createGroup">
            <span v-if="creatingGroup" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
            <span v-else>Create Group</span>
          </button>
          <p v-if="groupError" class="text-xs text-red-600">{{ groupError }}</p>
        </template>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="loadingThreads" class="p-4 space-y-2">
          <div v-for="i in 4" :key="i" class="h-14 bg-gray-100 rounded-xl animate-pulse"/>
        </div>
        <button v-for="t in threads" :key="t.id"
          class="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-gray-50 border-b border-gray-50 transition-colors"
          :class="activeThreadId === t.id ? `bg-${accent}-50` : ''" @click="openThread(t.id)">
          <span :class="`bg-${accent}-100 text-${accent}-700`" class="w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
            {{ (t.participants[0]?.name || t.subject || '?')[0]?.toUpperCase() }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-800 truncate">{{ threadLabel(t) }}</p>
            <p class="text-xs text-gray-400 truncate">{{ lastMessagePreview(t) }}</p>
          </div>
          <span v-if="t.unread_count > 0" :class="`bg-${accent}-600`" class="text-white text-xs font-bold rounded-full px-1.5 py-0.5 flex-shrink-0">{{ t.unread_count }}</span>
        </button>
        <p v-if="!loadingThreads && !threads.length" class="p-6 text-center text-sm text-gray-400">No conversations yet.</p>
      </div>
    </div>

    <!-- Message pane -->
    <div class="flex-1 card overflow-hidden flex flex-col">
      <div v-if="!activeThreadId" class="flex-1 flex items-center justify-center text-gray-400 text-sm px-8 text-center">
        Select a conversation, or start a new one with your landlord, tenant, agency, caretaker, or an assigned service provider.
      </div>
      <template v-else>
        <div class="p-4 border-b border-gray-100">
          <p class="font-bold text-gray-900">{{ activeThreadLabel }}</p>
        </div>

        <div ref="scrollArea" class="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50/50">
          <div v-if="loadingMessages" class="text-center text-xs text-gray-400 py-6">Loading…</div>
          <div v-for="m in messages" :key="m.id" :class="['group flex flex-col', m.sender_id === auth.user?.id ? 'items-end' : 'items-start']">
            <div :class="['max-w-md rounded-2xl px-4 py-2 text-sm relative', m.sender_id === auth.user?.id
              ? `bg-${accent}-600 text-white rounded-br-sm` : 'bg-white border border-gray-100 text-gray-800 rounded-bl-sm']">

              <!-- Text -->
              <p v-if="m.message_type === 'text'" class="whitespace-pre-wrap">{{ m.body }}</p>

              <!-- Image -->
              <div v-else-if="m.message_type === 'image'" class="space-y-1">
                <div v-if="m.body" class="mb-1">{{ m.body }}</div>
                <div class="grid grid-cols-2 gap-1">
                  <img v-for="a in m.attachments" :key="a.id" :src="a.url" class="rounded-lg max-h-40 object-cover w-full cursor-zoom-in hover:opacity-90 transition-opacity"
                    @click="lightboxUrl = a.url" />
                </div>
              </div>

              <!-- Document -->
              <a v-else-if="m.message_type === 'document'" v-for="a in m.attachments" :key="a.id" :href="a.url" target="_blank"
                class="flex items-center gap-2 underline">
                <FileText class="w-4 h-4 flex-shrink-0" /> {{ a.url.split('/').pop() }}
              </a>

              <!-- Voice note -->
              <div v-else-if="m.message_type === 'voice_note'" v-for="a in m.attachments" :key="a.id" class="flex items-center gap-2">
                <Mic class="w-4 h-4 flex-shrink-0" />
                <audio :src="a.url" controls class="h-8 max-w-[220px]" />
              </div>

              <!-- Shared object card -->
              <div v-else-if="m.shared_object" class="text-xs min-w-[180px]">
                <p class="font-bold mb-1 capitalize">{{ m.shared_object.object_type.replace('_', ' ') }}</p>
                <div class="space-y-0.5 opacity-90">
                  <p v-for="(v, k) in m.shared_object.card_data" :key="k" class="capitalize">{{ String(k).replace('_',' ') }}: {{ v }}</p>
                </div>
              </div>

              <p v-else class="italic opacity-70 capitalize">{{ m.message_type.replace('_', ' ') }}</p>

              <div class="flex items-center gap-1 mt-1">
                <p :class="['text-[10px]', m.sender_id === auth.user?.id ? 'text-white/60' : 'text-gray-400']">
                  {{ new Date(m.created_at).toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit' }) }}
                </p>
                <!-- Read receipt ticks (own messages only) -->
                <span v-if="m.sender_id === auth.user?.id" class="text-[10px]" :title="m.delivery_status">
                  <CheckCheck v-if="m.delivery_status === 'read'" class="w-3.5 h-3.5 text-sky-300" />
                  <CheckCheck v-else-if="m.delivery_status === 'delivered'" class="w-3.5 h-3.5 text-white/60" />
                  <Check v-else class="w-3.5 h-3.5 text-white/60" />
                </span>
              </div>

              <!-- Quick react (shows on hover) -->
              <div class="hidden group-hover:flex absolute -bottom-3 gap-0.5 bg-white border border-gray-100 rounded-full px-1 py-0.5 shadow-sm"
                :class="m.sender_id === auth.user?.id ? 'right-2' : 'left-2'">
                <button v-for="emoji in quickEmojis" :key="emoji" class="text-xs hover:scale-125 transition-transform px-0.5" @click="toggleReaction(m, emoji)">
                  {{ emoji }}
                </button>
              </div>
            </div>

            <!-- Reaction pills -->
            <div v-if="Object.keys(m.reactions || {}).length" class="flex gap-1 mt-3.5">
              <span v-for="(users, emoji) in m.reactions" :key="emoji"
                class="text-xs bg-white border border-gray-100 rounded-full px-1.5 py-0.5 cursor-pointer"
                @click="toggleReaction(m, String(emoji))">
                {{ emoji }} {{ users.length }}
              </span>
            </div>
          </div>
        </div>

        <!-- Recording indicator -->
        <div v-if="recording" class="px-4 py-2 bg-red-50 border-t border-red-100 flex items-center gap-2 text-red-600 text-sm">
          <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"/> Recording… {{ recordSeconds }}s
          <button class="ml-auto text-xs underline" @click="cancelRecording">Cancel</button>
        </div>

        <div class="p-3 border-t border-gray-100 flex items-center gap-2">
          <input ref="fileInput" type="file" class="hidden" multiple accept="image/*,.pdf,.doc,.docx" @change="onFilesSelected" />
          <button class="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-50" title="Attach file" @click="fileInput?.click()">
            <Paperclip class="w-4 h-4" />
          </button>
          <button class="p-2 rounded-lg hover:bg-gray-50" :class="recording ? 'text-red-600' : 'text-gray-400 hover:text-gray-600'"
            title="Record voice note" @click="recording ? stopRecording() : startRecording()">
            <Mic class="w-4 h-4" />
          </button>
          <input v-model="draft" class="input flex-1" placeholder="Type a message…" @keyup.enter="send"/>
          <button :class="`bg-${accent}-600 hover:bg-${accent}-700`" class="btn-primary" :disabled="!draft.trim() || sending" @click="send">Send</button>
        </div>
        <p v-if="uploadError" class="px-3 pb-2 text-xs text-red-600">{{ uploadError }}</p>
      </template>
    </div>

    <!-- Image lightbox -->
    <div v-if="lightboxUrl" class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-6" @click="lightboxUrl = null">
      <img :src="lightboxUrl" class="max-h-full max-w-full rounded-lg" />
      <button class="absolute top-4 right-4 text-white/80 hover:text-white" @click="lightboxUrl = null"><X class="w-8 h-8" /></button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { Paperclip, Mic, FileText, CheckCheck, Check, X } from 'lucide-vue-next'
import { chatApi, propertiesApi } from '@/api/services'
import { useAuthStore } from '@/stores/auth'
import type { ChatThreadSummary, ChatMessage, ChatRelationship } from '@/types'

const props = withDefaults(defineProps<{ accent?: string }>(), { accent: 'tenant' })
const accent = props.accent
const canCreateGroups = computed(() => accent === 'landlord' || accent === 'agency')

const auth = useAuthStore()
const threads = ref<ChatThreadSummary[]>([])
const messages = ref<ChatMessage[]>([])
const relationships = ref<ChatRelationship[]>([])
const activeThreadId = ref<string | null>(null)
const draft = ref('')
const loadingThreads = ref(true)
const loadingMessages = ref(false)
const loadingRelationships = ref(false)
const sending = ref(false)
const showNewChat = ref(false)
const scrollArea = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref('')
const lightboxUrl = ref<string | null>(null)

const newChatTab = ref<'direct' | 'group'>('direct')
const myProperties = ref<{ id: string; name: string }[]>([])
const creatingGroup = ref(false)
const groupError = ref('')
const groupForm = ref<{ property_id: string; subject: string; participant_ids: string[] }>({
  property_id: '', subject: '', participant_ids: [],
})

const quickEmojis = ['👍', '❤️', '😂', '😮', '🙏']

async function loadMyProperties() {
  if (myProperties.value.length) return
  try {
    const { data } = await propertiesApi.list()
    myProperties.value = ((data.data?.results || data.data || []) as { id: string; name: string }[])
  } catch { myProperties.value = [] }
}

async function createGroup() {
  if (!groupForm.value.property_id) return
  creatingGroup.value = true; groupError.value = ''
  try {
    const { data } = await chatApi.createGroup(groupForm.value.property_id, groupForm.value.participant_ids, groupForm.value.subject)
    const threadId = (data as any).data.thread_id
    showNewChat.value = false
    groupForm.value = { property_id: '', subject: '', participant_ids: [] }
    await loadThreads()
    await openThread(threadId)
  } catch (e: any) {
    groupError.value = e?.response?.data?.error?.message || 'Failed to create group.'
  } finally {
    creatingGroup.value = false
  }
}

// ---------- Voice recording ----------
const recording = ref(false)
const recordSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let recordedChunks: BlobPart[] = []
let recordTimer: ReturnType<typeof setInterval> | null = null

async function startRecording() {
  uploadError.value = ''
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    recordedChunks = []
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
    mediaRecorder.onstop = onRecordingStopped
    mediaRecorder.start()
    recording.value = true
    recordSeconds.value = 0
    recordTimer = setInterval(() => { recordSeconds.value++ }, 1000)
  } catch {
    uploadError.value = 'Microphone access denied or unavailable.'
  }
}

function stopRecording() {
  mediaRecorder?.stop()
  if (recordTimer) clearInterval(recordTimer)
  recording.value = false
}

function cancelRecording() {
  recordedChunks = []
  stopRecording()
}

async function onRecordingStopped() {
  if (!recordedChunks.length || !activeThreadId.value) return
  const blob = new Blob(recordedChunks, { type: 'audio/webm' })
  const file = new File([blob], `voice-note-${Date.now()}.webm`, { type: 'audio/webm' })
  const duration = recordSeconds.value
  try {
    await chatApi.uploadAttachment(activeThreadId.value, [file], 'voice_note', undefined, duration)
    await openThread(activeThreadId.value)
  } catch {
    uploadError.value = 'Failed to send voice note.'
  }
}

// ---------- File attachments ----------
async function onFilesSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []
  if (!files.length || !activeThreadId.value) return
  uploadError.value = ''
  const isImage = files.every((f) => f.type.startsWith('image/'))
  try {
    await chatApi.uploadAttachment(activeThreadId.value, files, isImage ? 'image' : 'document')
    await openThread(activeThreadId.value)
  } catch {
    uploadError.value = 'Failed to upload attachment.'
  } finally {
    input.value = ''
  }
}

// ---------- Reactions ----------
async function toggleReaction(m: ChatMessage, emoji: string) {
  const already = (m.reactions[emoji] || []).includes(auth.user?.id || '')
  try {
    if (already) await chatApi.unreact(m.id, emoji)
    else await chatApi.react(m.id, emoji)
    if (activeThreadId.value) await openThread(activeThreadId.value)
  } catch { /* non-critical */ }
}

// ---------- Threads / messages ----------
const activeThreadLabel = computed(() => {
  const t = threads.value.find(t => t.id === activeThreadId.value)
  return t ? threadLabel(t) : ''
})

function threadLabel(t: ChatThreadSummary) {
  if (t.subject) return t.subject
  return t.participants.map(p => p.name).join(', ') || 'Conversation'
}

function lastMessagePreview(t: ChatThreadSummary) {
  if (!t.last_message) return 'No messages yet'
  const typeLabels: Record<string, string> = {
    image: '📷 Photo', video: '🎥 Video', document: '📄 Document', voice_note: '🎤 Voice note',
    property_card: '🏠 Property', invoice_card: '🧾 Invoice', payment_request: '💰 Payment request',
    maintenance_card: '🔧 Maintenance', booking_card: '📅 Booking', lease_card: '📋 Lease', system: 'System',
  }
  return t.last_message.message_type === 'text' ? t.last_message.body : (typeLabels[t.last_message.message_type] || t.last_message.body)
}

async function loadThreads() {
  loadingThreads.value = true
  try {
    const { data } = await chatApi.threads()
    threads.value = (data as any).data || []
  } finally {
    loadingThreads.value = false
  }
}

async function openThread(id: string) {
  activeThreadId.value = id
  loadingMessages.value = true
  try {
    const { data } = await chatApi.messages(id)
    messages.value = (data as any).data || []
    await nextTick()
    scrollArea.value?.scrollTo({ top: scrollArea.value.scrollHeight })
  } finally {
    loadingMessages.value = false
  }
  await loadThreads() // refresh unread counts
}

async function openNewChat(participantId: string) {
  showNewChat.value = false
  const { data } = await chatApi.startThread(participantId)
  const threadId = (data as any).data.thread_id
  await loadThreads()
  await openThread(threadId)
}

async function send() {
  if (!draft.value.trim() || !activeThreadId.value) return
  sending.value = true
  try {
    await chatApi.sendMessage(activeThreadId.value, draft.value.trim())
    draft.value = ''
    await openThread(activeThreadId.value)
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  await loadThreads()
  loadingRelationships.value = true
  try {
    const { data } = await chatApi.relationships()
    relationships.value = (data as any).data || []
  } catch { relationships.value = [] } finally { loadingRelationships.value = false }
})
</script>
