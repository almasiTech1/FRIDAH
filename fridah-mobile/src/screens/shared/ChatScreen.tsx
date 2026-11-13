import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, TextInput, StyleSheet,
  RefreshControl, ActivityIndicator, KeyboardAvoidingView, Platform, Alert, Image, Modal, Linking,
  PermissionsAndroid,
} from 'react-native'
import { useRoute } from '@react-navigation/native'
import { chatApi } from '@/api/services'
import { useAuthStore } from '@/stores/authStore'
import { EmptyState } from '@/components/common/Cards'
import { colors, spacing, typography, radius, getSurfaceColors } from '@/theme'
import type { PortalTheme } from '@/theme'
import { useThemeStore } from '@/stores/themeStore'
import type { ChatThreadSummary, ChatMessage, ChatRelationship, MessageType } from '@/types'

// These three native modules require the ios/ and android/ platform projects
// (CocoaPods / Gradle linking, camera & microphone permission entries) that
// aren't part of this source-only repo snapshot. The integration below is
// written to their documented APIs and passes TypeScript, but has not been
// run on a device or simulator — see NATIVE_SETUP.md for what's still needed.
import { launchImageLibrary, launchCamera } from 'react-native-image-picker'
import { pick, isErrorWithCode, errorCodes } from '@react-native-documents/picker'
import AudioRecorderPlayer, { type RecordBackType } from 'react-native-audio-recorder-player'

// v4's default export is already a ready-to-use singleton, not a class to `new`.
const audioRecorderPlayer = AudioRecorderPlayer

const TYPE_PREVIEW: Record<MessageType, string> = {
  text: '', image: '📷 Photo', video: '🎥 Video', document: '📄 Document', voice_note: '🎤 Voice note',
  property_card: '🏠 Property', invoice_card: '🧾 Invoice', payment_request: '💰 Payment request',
  maintenance_card: '🔧 Maintenance', booking_card: '📅 Booking', lease_card: '📋 Lease', system: 'System',
}

const QUICK_EMOJIS = ['👍', '❤️', '😂', '😮', '🙏']

interface Props {
  theme: PortalTheme
  canCreateGroups?: boolean
}

export const ChatScreen: React.FC<Props> = ({ theme }) => {
  const { user } = useAuthStore()
  const isDark = useThemeStore((s) => s.mode === 'dark')
  const surface = getSurfaceColors(isDark)
  // Present when this screen was opened via a push-notification tap for a specific
  // conversation (see src/services/push.ts), so it can jump straight to that thread.
  const route = useRoute<any>()
  const deepLinkedThreadId: string | undefined = route.params?.threadId

  const [threads, setThreads] = useState<ChatThreadSummary[]>([])
  const [activeThread, setActiveThread] = useState<ChatThreadSummary | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [relationships, setRelationships] = useState<ChatRelationship[]>([])
  const [draft, setDraft] = useState('')
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [showNewChat, setShowNewChat] = useState(false)
  const [sending, setSending] = useState(false)
  const [reactingId, setReactingId] = useState<string | null>(null)
  const [showAttachMenu, setShowAttachMenu] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordSeconds, setRecordSeconds] = useState(0)
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const listRef = useRef<FlatList>(null)

  const threadLabel = (t: ChatThreadSummary) => t.subject || t.participants.map((p) => p.name).join(', ') || 'Conversation'
  const previewFor = (t: ChatThreadSummary) => {
    if (!t.last_message) return 'No messages yet'
    return t.last_message.message_type === 'text' ? t.last_message.body : (TYPE_PREVIEW[t.last_message.message_type] || t.last_message.body)
  }

  const loadThreads = useCallback(async () => {
    try {
      const { data } = await chatApi.threads()
      setThreads((data as any).data || [])
    } catch {
      setThreads([])
    } finally {
      setLoadingThreads(false); setRefreshing(false)
    }
  }, [])

  const loadRelationships = useCallback(async () => {
    try {
      const { data } = await chatApi.relationships()
      setRelationships((data as any).data || [])
    } catch {
      setRelationships([])
    }
  }, [])

  const openThread = useCallback(async (thread: ChatThreadSummary) => {
    setActiveThread(thread)
    setLoadingMessages(true)
    try {
      const { data } = await chatApi.messages(thread.id)
      setMessages((data as any).data || [])
    } catch {
      setMessages([])
    } finally {
      setLoadingMessages(false)
      loadThreads() // refresh unread counts in background
    }
  }, [loadThreads])

  const startNewChat = async (otherUserId: string) => {
    setShowNewChat(false)
    const { data } = await chatApi.startThread(otherUserId)
    const threadId = (data as any).data.thread_id
    const { data: refreshed } = await chatApi.threads()
    const list: ChatThreadSummary[] = (refreshed as any).data || []
    setThreads(list)
    const newThread = list.find((t) => t.id === threadId)
    if (newThread) await openThread(newThread)
  }

  const send = async () => {
    if (!draft.trim() || !activeThread) return
    setSending(true)
    try {
      await chatApi.sendMessage(activeThread.id, draft.trim())
      setDraft('')
      await openThread(activeThread)
    } finally {
      setSending(false)
    }
  }

  const toggleReaction = async (m: ChatMessage, emoji: string) => {
    const already = (m.reactions[emoji] || []).includes(user?.id || '')
    setReactingId(null)
    try {
      if (already) await chatApi.unreact(m.id, emoji)
      else await chatApi.react(m.id, emoji)
      if (activeThread) await openThread(activeThread)
    } catch { /* non-critical */ }
  }

  // ─── Photo / camera attachment ────────────────────────────────────────────
  const pickAndSendImage = async (fromCamera: boolean) => {
    setShowAttachMenu(false)
    if (!activeThread) return
    const launcher = fromCamera ? launchCamera : launchImageLibrary
    launcher({ mediaType: 'photo', quality: 0.8 }, async (response) => {
      if (response.didCancel || response.errorCode) return
      const asset = response.assets?.[0]
      if (!asset?.uri) return
      setUploading(true)
      try {
        await chatApi.uploadAttachment(
          activeThread.id,
          [{ uri: asset.uri, name: asset.fileName || `photo-${Date.now()}.jpg`, type: asset.type || 'image/jpeg' }],
          'image',
        )
        await openThread(activeThread)
      } catch {
        Alert.alert('Error', 'Failed to send photo.')
      } finally {
        setUploading(false)
      }
    })
  }

  // ─── Document attachment ──────────────────────────────────────────────────
  const pickAndSendDocument = async () => {
    setShowAttachMenu(false)
    if (!activeThread) return
    try {
      const [result] = await pick({ type: ['application/pdf', 'application/msword', 'image/*'] })
      setUploading(true)
      await chatApi.uploadAttachment(
        activeThread.id,
        [{ uri: result.uri, name: result.name || `document-${Date.now()}`, type: result.type || 'application/octet-stream' }],
        'document',
      )
      await openThread(activeThread)
    } catch (err) {
      if (isErrorWithCode(err) && err.code === errorCodes.OPERATION_CANCELED) return
      Alert.alert('Error', 'Failed to send document.')
    } finally {
      setUploading(false)
    }
  }

  // ─── Voice note recording ─────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
          {
            title: 'Microphone Permission',
            message: 'FRIDAH needs microphone access to record voice notes in chat.',
            buttonPositive: 'Allow',
            buttonNegative: 'Deny',
          },
        )
        if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
          Alert.alert('Permission needed', 'Microphone access is required to record a voice note.')
          return
        }
      }
      await audioRecorderPlayer.startRecorder()
      setRecording(true)
      setRecordSeconds(0)
      audioRecorderPlayer.addRecordBackListener((e: RecordBackType) => {
        setRecordSeconds(Math.floor(e.currentPosition / 1000))
      })
    } catch {
      Alert.alert('Error', 'Microphone access denied or unavailable.')
    }
  }

  const stopRecordingAndSend = async () => {
    if (!activeThread) return
    try {
      const uri = await audioRecorderPlayer.stopRecorder()
      audioRecorderPlayer.removeRecordBackListener()
      setRecording(false)
      const duration = recordSeconds
      setUploading(true)
      await chatApi.uploadAttachment(
        activeThread.id,
        [{ uri, name: `voice-note-${Date.now()}.m4a`, type: 'audio/m4a' }],
        'voice_note',
        undefined,
        duration,
      )
      await openThread(activeThread)
    } catch {
      Alert.alert('Error', 'Failed to send voice note.')
    } finally {
      setUploading(false)
    }
  }

  const cancelRecording = async () => {
    try {
      await audioRecorderPlayer.stopRecorder()
      audioRecorderPlayer.removeRecordBackListener()
    } catch { /* already stopped */ }
    setRecording(false)
  }

  useEffect(() => { loadThreads(); loadRelationships() }, [loadThreads, loadRelationships])

  // Jump straight into the relevant conversation when opened from a chat push notification.
  useEffect(() => {
    if (!deepLinkedThreadId || activeThread) return
    const target = threads.find((t) => t.id === deepLinkedThreadId)
    if (target) {
      openThread(target)
    } else if (!loadingThreads && threads.length) {
      // Thread not in the cached list yet (e.g. brand new) — fetch fresh and try again.
      chatApi.threads().then(({ data }) => {
        const fresh: ChatThreadSummary[] = (data as any).data || []
        setThreads(fresh)
        const found = fresh.find((t) => t.id === deepLinkedThreadId)
        if (found) openThread(found)
      }).catch(() => {})
    }
  }, [deepLinkedThreadId, threads, loadingThreads, activeThread, openThread])

  // ─── Message detail view ──────────────────────────────────────────────────
  if (activeThread) {
    return (
      <KeyboardAvoidingView
        style={[styles.container, { backgroundColor: surface.background }]}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <View style={[styles.threadHeader, { backgroundColor: theme.primary }]}>
          <TouchableOpacity onPress={() => { setActiveThread(null); setMessages([]) }} style={styles.backBtn}>
            <Text style={styles.backText}>‹ Back</Text>
          </TouchableOpacity>
          <Text style={styles.threadHeaderTitle} numberOfLines={1}>{threadLabel(activeThread)}</Text>
        </View>

        {loadingMessages ? (
          <ActivityIndicator style={{ marginTop: 30 }} color={theme.primary} />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            contentContainerStyle={styles.messageList}
            renderItem={({ item: m }) => {
              const mine = m.sender_id === user?.id
              return (
                <TouchableOpacity
                  activeOpacity={0.85}
                  onLongPress={() => setReactingId(reactingId === m.id ? null : m.id)}
                  style={[styles.bubbleRow, mine ? styles.bubbleRowMine : styles.bubbleRowTheirs]}
                >
                  <View style={[
                    styles.bubble,
                    mine ? { backgroundColor: theme.primary, borderBottomRightRadius: 4 }
                      : { backgroundColor: surface.surface, borderColor: surface.border, borderWidth: 1, borderBottomLeftRadius: 4 },
                  ]}>
                    {m.message_type === 'text' ? (
                      <Text style={[styles.bubbleText, { color: mine ? colors.white : surface.text }]}>{m.body}</Text>
                    ) : m.message_type === 'image' && m.attachments.length ? (
                      <View>
                        {m.body ? <Text style={[styles.bubbleText, { color: mine ? colors.white : surface.text, marginBottom: 4 }]}>{m.body}</Text> : null}
                        <View style={styles.imageGrid}>
                          {m.attachments.map((a: ChatMessage['attachments'][number]) => (
                            <TouchableOpacity key={a.id} onPress={() => setLightboxUrl(a.url)}>
                              <Image source={{ uri: a.url }} style={styles.attachmentImage} />
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>
                    ) : m.message_type === 'document' && m.attachments.length ? (
                      m.attachments.map((a: ChatMessage['attachments'][number]) => (
                        <TouchableOpacity key={a.id} style={styles.docRow} onPress={() => Linking.openURL(a.url)}>
                          <Text style={styles.docIcon}>📄</Text>
                          <Text style={[styles.docLink, { color: mine ? colors.white : surface.text }]} numberOfLines={1}>
                            {a.url.split('/').pop()}
                          </Text>
                        </TouchableOpacity>
                      ))
                    ) : m.message_type === 'voice_note' && m.attachments.length ? (
                      m.attachments.map((a: ChatMessage['attachments'][number]) => (
                        <TouchableOpacity key={a.id} style={styles.voiceRow} onPress={() => Linking.openURL(a.url)}>
                          <Text style={styles.docIcon}>🎤</Text>
                          <Text style={[styles.docLink, { color: mine ? colors.white : surface.text }]}>
                            Voice note{a.duration_seconds ? ` · ${a.duration_seconds}s` : ''}
                          </Text>
                        </TouchableOpacity>
                      ))
                    ) : m.shared_object ? (
                      <View>
                        <Text style={[styles.bubbleText, styles.bold, { color: mine ? colors.white : surface.text }]}>
                          {m.shared_object.object_type.replace('_', ' ')}
                        </Text>
                        {Object.entries(m.shared_object.card_data).map(([k, v]) => (
                          <Text key={k} style={[styles.bubbleSub, { color: mine ? 'rgba(255,255,255,0.8)' : surface.textMuted }]}>
                            {k.replace('_', ' ')}: {String(v)}
                          </Text>
                        ))}
                      </View>
                    ) : (
                      <Text style={[styles.bubbleText, styles.italic, { color: mine ? 'rgba(255,255,255,0.8)' : surface.textMuted }]}>
                        {TYPE_PREVIEW[m.message_type as MessageType] || m.message_type}
                      </Text>
                    )}
                    <Text style={[styles.bubbleTime, { color: mine ? 'rgba(255,255,255,0.6)' : surface.textMuted }]}>
                      {new Date(m.created_at).toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit' })}
                    </Text>
                  </View>

                  {Object.keys(m.reactions || {}).length > 0 && (
                    <View style={styles.reactionRow}>
                      {(Object.entries(m.reactions) as [string, string[]][]).map(([emoji, users]) => (
                        <TouchableOpacity key={emoji} style={[styles.reactionPill, { backgroundColor: surface.surface, borderColor: surface.border }]} onPress={() => toggleReaction(m, emoji)}>
                          <Text style={styles.reactionText}>{emoji} {users.length}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  )}

                  {reactingId === m.id && (
                    <View style={[styles.quickReactRow, { backgroundColor: surface.surface, borderColor: surface.border }]}>
                      {QUICK_EMOJIS.map((emoji) => (
                        <TouchableOpacity key={emoji} onPress={() => toggleReaction(m, emoji)} style={styles.quickReactBtn}>
                          <Text style={{ fontSize: 18 }}>{emoji}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  )}
                </TouchableOpacity>
              )
            }}
            ListEmptyComponent={<EmptyState emoji="💬" message="No messages yet. Say hello!" />}
          />
        )}

        {recording && (
          <View style={styles.recordingBar}>
            <View style={styles.recordingDot} />
            <Text style={styles.recordingText}>Recording… {recordSeconds}s</Text>
            <TouchableOpacity onPress={cancelRecording}><Text style={styles.recordingCancel}>Cancel</Text></TouchableOpacity>
          </View>
        )}
        {uploading && (
          <View style={styles.uploadingBar}>
            <ActivityIndicator size="small" color={theme.primary} />
            <Text style={[styles.recordingText, { color: theme.primaryDark }]}>Sending…</Text>
          </View>
        )}

        <View style={[styles.inputRow, { backgroundColor: surface.surface, borderTopColor: surface.border }]}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => setShowAttachMenu(true)}>
            <Text style={styles.iconBtnText}>📎</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconBtn} onPress={recording ? stopRecordingAndSend : startRecording}>
            <Text style={[styles.iconBtnText, recording && { color: colors.red600 }]}>🎤</Text>
          </TouchableOpacity>
          <TextInput
            style={[styles.input, { color: surface.text, backgroundColor: surface.surfaceAlt }]}
            placeholder="Type a message…"
            placeholderTextColor={colors.gray400}
            value={draft}
            onChangeText={setDraft}
            multiline
          />
          <TouchableOpacity
            style={[styles.sendBtn, { backgroundColor: theme.primary, opacity: draft.trim() ? 1 : 0.5 }]}
            disabled={!draft.trim() || sending}
            onPress={send}
          >
            {sending ? <ActivityIndicator size="small" color={colors.white} /> : <Text style={styles.sendText}>Send</Text>}
          </TouchableOpacity>
        </View>

        <Modal visible={showAttachMenu} transparent animationType="fade" onRequestClose={() => setShowAttachMenu(false)}>
          <TouchableOpacity style={styles.attachOverlay} activeOpacity={1} onPress={() => setShowAttachMenu(false)}>
            <View style={[styles.attachMenu, { backgroundColor: surface.surface }]}>
              <TouchableOpacity style={styles.attachOption} onPress={() => pickAndSendImage(true)}>
                <Text style={styles.attachOptionIcon}>📷</Text>
                <Text style={[styles.attachOptionText, { color: surface.text }]}>Take Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.attachOption} onPress={() => pickAndSendImage(false)}>
                <Text style={styles.attachOptionIcon}>🖼️</Text>
                <Text style={[styles.attachOptionText, { color: surface.text }]}>Choose Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.attachOption} onPress={pickAndSendDocument}>
                <Text style={styles.attachOptionIcon}>📄</Text>
                <Text style={[styles.attachOptionText, { color: surface.text }]}>Document</Text>
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        </Modal>

        <Modal visible={!!lightboxUrl} transparent animationType="fade" onRequestClose={() => setLightboxUrl(null)}>
          <TouchableOpacity style={styles.lightbox} activeOpacity={1} onPress={() => setLightboxUrl(null)}>
            {lightboxUrl && <Image source={{ uri: lightboxUrl }} style={styles.lightboxImage} resizeMode="contain" />}
          </TouchableOpacity>
        </Modal>
      </KeyboardAvoidingView>
    )
  }

  // ─── Thread list view ─────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: surface.background }]}>
      <View style={[styles.listHeader, { backgroundColor: theme.primary }]}>
        <Text style={styles.listHeaderTitle}>Chats</Text>
        <TouchableOpacity style={styles.newChatBtn} onPress={() => setShowNewChat(!showNewChat)}>
          <Text style={styles.newChatBtnText}>{showNewChat ? 'Close' : '+ New'}</Text>
        </TouchableOpacity>
      </View>

      {showNewChat && (
        <View style={[styles.newChatPanel, { backgroundColor: surface.surfaceAlt, borderColor: surface.border }]}>
          {relationships.length === 0 ? (
            <Text style={{ color: surface.textMuted, fontSize: typography.sm, padding: spacing.md }}>
              No contacts yet — people appear here once you have an active lease, tenancy, or assignment.
            </Text>
          ) : (
            relationships.map((r) => (
              <TouchableOpacity key={r.id} style={styles.relationshipRow} onPress={() => startNewChat(r.id)}>
                <View style={[styles.avatar, { backgroundColor: theme.primaryLight }]}>
                  <Text style={[styles.avatarText, { color: theme.primaryDark }]}>{r.name[0]?.toUpperCase()}</Text>
                </View>
                <Text style={[styles.relationshipName, { color: surface.text }]}>{r.name}</Text>
                <Text style={[styles.relationshipTag, { color: surface.textMuted }]}>{r.relationships[0]}</Text>
              </TouchableOpacity>
            ))
          )}
        </View>
      )}

      {loadingThreads ? (
        <ActivityIndicator style={{ marginTop: 30 }} color={theme.primary} />
      ) : (
        <FlatList
          data={threads}
          keyExtractor={(t) => t.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadThreads() }} tintColor={theme.primary} />}
          renderItem={({ item: t }) => (
            <TouchableOpacity style={[styles.threadRow, { borderColor: surface.border }]} onPress={() => openThread(t)}>
              <View style={[styles.avatar, { backgroundColor: theme.primaryLight }]}>
                <Text style={[styles.avatarText, { color: theme.primaryDark }]}>{threadLabel(t)[0]?.toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.threadName, { color: surface.text }]} numberOfLines={1}>{threadLabel(t)}</Text>
                <Text style={[styles.threadPreview, { color: surface.textMuted }]} numberOfLines={1}>{previewFor(t)}</Text>
              </View>
              {t.unread_count > 0 && (
                <View style={[styles.unreadBadge, { backgroundColor: theme.primary }]}>
                  <Text style={styles.unreadText}>{t.unread_count}</Text>
                </View>
              )}
            </TouchableOpacity>
          )}
          ListEmptyComponent={<EmptyState emoji="💬" message="No conversations yet." />}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  listHeader: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: spacing.xl, paddingVertical: spacing.lg,
  },
  listHeaderTitle: { color: colors.white, fontSize: typography.lg, fontWeight: '700' },
  newChatBtn: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.full },
  newChatBtnText: { color: colors.white, fontSize: typography.xs, fontWeight: '700' },
  newChatPanel: { borderBottomWidth: 1, maxHeight: 220 },
  relationshipRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm },
  relationshipName: { flex: 1, fontSize: typography.sm, fontWeight: '600' },
  relationshipTag: { fontSize: typography.xs, textTransform: 'capitalize' },
  threadRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: spacing.lg, paddingVertical: spacing.md, borderBottomWidth: 1 },
  avatar: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: typography.base, fontWeight: '700' },
  threadName: { fontSize: typography.base, fontWeight: '600' },
  threadPreview: { fontSize: typography.sm, marginTop: 2 },
  unreadBadge: { minWidth: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  unreadText: { color: colors.white, fontSize: 11, fontWeight: '700' },

  threadHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: spacing.lg, paddingVertical: spacing.lg },
  backBtn: { paddingVertical: 4, paddingRight: 4 },
  backText: { color: colors.white, fontSize: typography.base, fontWeight: '600' },
  threadHeaderTitle: { color: colors.white, fontSize: typography.base, fontWeight: '700', flex: 1 },

  messageList: { padding: spacing.lg, gap: 4 },
  bubbleRow: { marginBottom: spacing.sm, maxWidth: '80%' },
  bubbleRowMine: { alignSelf: 'flex-end', alignItems: 'flex-end' },
  bubbleRowTheirs: { alignSelf: 'flex-start', alignItems: 'flex-start' },
  bubble: { borderRadius: radius.lg, paddingHorizontal: 14, paddingVertical: 9 },
  bubbleText: { fontSize: typography.sm },
  bubbleSub: { fontSize: typography.xs, marginTop: 1, textTransform: 'capitalize' },
  bubbleTime: { fontSize: 10, marginTop: 4 },
  bold: { fontWeight: '700', textTransform: 'capitalize' },
  italic: { fontStyle: 'italic', textTransform: 'capitalize' },

  reactionRow: { flexDirection: 'row', gap: 4, marginTop: 4 },
  reactionPill: { borderWidth: 1, borderRadius: radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  reactionText: { fontSize: 11 },
  quickReactRow: { flexDirection: 'row', gap: 6, borderRadius: radius.full, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 6, marginTop: 6 },
  quickReactBtn: { paddingHorizontal: 2 },

  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderTopWidth: 1 },
  input: { flex: 1, borderRadius: radius.lg, paddingHorizontal: 14, paddingVertical: 10, fontSize: typography.sm, maxHeight: 100 },
  sendBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: radius.lg },
  sendText: { color: colors.white, fontSize: typography.sm, fontWeight: '700' },

  iconBtn: { padding: 8 },
  iconBtnText: { fontSize: 20 },

  recordingBar: {
    flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: spacing.md, paddingVertical: 8,
    backgroundColor: '#fef2f2',
  },
  recordingDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.red600 },
  recordingText: { fontSize: typography.sm, color: colors.red600, flex: 1 },
  recordingCancel: { fontSize: typography.xs, color: colors.red600, textDecorationLine: 'underline' },

  uploadingBar: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: spacing.md, paddingVertical: 8 },

  imageGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  attachmentImage: { width: 140, height: 140, borderRadius: radius.md },

  docRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  voiceRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  docIcon: { fontSize: 18 },
  docLink: { fontSize: typography.sm, textDecorationLine: 'underline', flexShrink: 1 },

  attachOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  attachMenu: { borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl, paddingVertical: spacing.md, paddingBottom: spacing.xl },
  attachOption: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: spacing.xl, paddingVertical: spacing.md },
  attachOptionIcon: { fontSize: 22, width: 28, textAlign: 'center' },
  attachOptionText: { fontSize: typography.base, fontWeight: '600' },

  lightbox: { flex: 1, backgroundColor: 'rgba(0,0,0,0.9)', alignItems: 'center', justifyContent: 'center' },
  lightboxImage: { width: '95%', height: '80%' },
})
