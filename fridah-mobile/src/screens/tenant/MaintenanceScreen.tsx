import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  TextInput, ScrollView, RefreshControl, Modal, Alert, Image,
} from 'react-native'
import { launchImageLibrary, launchCamera } from 'react-native-image-picker'
import { rentalsApi, aiApi } from '@/api/services'
import { Card, StatusBadge, EmptyState, Skeleton } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate } from '@/utils/formatters'
import type { MaintenanceRequest } from '@/types'

const CATEGORIES = ['Plumbing','Electrical','Carpentry','Painting','Pest Control','Cleaning','Security','Other']

// The AI triage endpoint uses its own technical taxonomy (see apps/ai/maintenance_triage.py
// on the backend), which doesn't match this form's human-friendly category chips one-to-one -
// this maps its suggestion onto the closest existing chip rather than introducing a second,
// inconsistent category vocabulary.
const AI_CATEGORY_TO_CHIP: Record<string, string> = {
  plumbing: 'Plumbing', electrical: 'Electrical', structural: 'Carpentry',
  pest_control: 'Pest Control', locks_security: 'Security',
  appliance: 'Other', hvac: 'Other', other: 'Other',
}

export const TenantMaintenanceScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const [requests, setRequests] = useState<MaintenanceRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', category: 'Plumbing', priority: 'medium' })
  const [photo, setPhoto] = useState<{ uri: string; name: string; type: string } | null>(null)
  const [triaging, setTriaging] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState<{ confidence: string; safety_concern: boolean } | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await rentalsApi.maintenanceList()
      setRequests(data.data?.results || [])
    } catch { setRequests([]) }
    finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const submit = async () => {
    if (!form.title || !form.description) { Alert.alert('Error', 'Fill in all fields.'); return }
    setSubmitting(true)
    try {
      const { data } = await rentalsApi.createMaintenance(form as any)
      const created = (data as any).data || data
      if (photo && created?.id) {
        try { await rentalsApi.attachMaintenanceImage(created.id, photo) }
        catch { /* request itself succeeded - a failed photo attach shouldn't block the flow */ }
      }
      setShowForm(false)
      setForm({ title: '', description: '', category: 'Plumbing', priority: 'medium' })
      setPhoto(null)
      setAiSuggestion(null)
      load()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to submit.')
    } finally { setSubmitting(false) }
  }

  const runTriage = async (p: { uri: string; name: string; type: string }) => {
    setTriaging(true)
    try {
      const { data } = await aiApi.maintenanceTriage(p, form.description)
      const result = (data as any).data || data
      setForm(f => ({
        ...f,
        category: AI_CATEGORY_TO_CHIP[result.category] || f.category,
        priority: ['low', 'medium', 'high', 'urgent'].includes(result.priority) ? result.priority : f.priority,
        description: f.description || result.description || f.description,
      }))
      setAiSuggestion({ confidence: result.confidence, safety_concern: result.safety_concern })
    } catch {
      // AI is an assist step only - if it's unavailable or fails, the tenant just
      // fills the form manually. The photo is still attached either way.
    } finally {
      setTriaging(false)
    }
  }

  const pickPhoto = () => {
    Alert.alert('Add a Photo', 'A photo helps us (and AI) understand the issue faster', [
      { text: 'Take Photo', onPress: () => launchPhoto(true) },
      { text: 'Choose from Gallery', onPress: () => launchPhoto(false) },
      { text: 'Cancel', style: 'cancel' },
    ])
  }

  const launchPhoto = (fromCamera: boolean) => {
    const launcher = fromCamera ? launchCamera : launchImageLibrary
    launcher({ mediaType: 'photo', quality: 0.8 }, (response) => {
      const asset = response.assets?.[0]
      if (!asset?.uri) return
      const p = { uri: asset.uri, name: asset.fileName || `issue-${Date.now()}.jpg`, type: asset.type || 'image/jpeg' }
      setPhoto(p)
      runTriage(p)
    })
  }

  const priorityDot = (p: string) => ({ low: '#9ca3af', medium: '#3b82f6', high: '#f59e0b', urgent: '#ef4444' }[p] || '#9ca3af')

  const closeForm = () => {
    setShowForm(false)
    setPhoto(null)
    setAiSuggestion(null)
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Button label="+ New Request" onPress={() => setShowForm(true)} color={theme.primary} size="sm" />
      </View>

      {loading ? (
        <ScrollView contentContainerStyle={styles.list}>
          {[0,1,2].map(i => <Skeleton key={i} height={100} style={{ marginBottom: 12 }} />)}
        </ScrollView>
      ) : (
        <FlatList
          data={requests}
          keyExtractor={i => i.id}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="🔧" message="No maintenance requests yet" />}
          renderItem={({ item }) => (
            <Card style={styles.card}>
              <View style={styles.cardTop}>
                <View style={[styles.dot, { backgroundColor: priorityDot(item.priority) }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.reqTitle}>{item.title}</Text>
                  <Text style={styles.reqMeta}>{item.category} · {formatDate(item.created_at)}</Text>
                </View>
                <StatusBadge status={item.status} />
              </View>
              <Text style={styles.desc}>{item.description}</Text>
              {item.provider_name && (
                <Text style={styles.provider}>👷 Assigned: {item.provider_name}</Text>
              )}
              {item.resolution_notes && (
                <View style={styles.resolutionBox}>
                  <Text style={styles.resolutionText}>✓ {item.resolution_notes}</Text>
                </View>
              )}
            </Card>
          )}
        />
      )}

      {/* New Request Modal */}
      <Modal visible={showForm} animationType="slide" transparent onRequestClose={closeForm}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>New Maintenance Request</Text>
              <TouchableOpacity onPress={() => setShowForm(false)}>
                <Text style={styles.modalClose}>✕</Text>
              </TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.fieldLabel}>Photo (optional)</Text>
              {photo ? (
                <View style={styles.photoPreviewWrap}>
                  <Image source={{ uri: photo.uri }} style={styles.photoPreview} />
                  <TouchableOpacity style={styles.photoRemove} onPress={() => { setPhoto(null); setAiSuggestion(null) }}>
                    <Text style={{ color: colors.white, fontWeight: '700' }}>✕</Text>
                  </TouchableOpacity>
                  {triaging && (
                    <View style={styles.photoOverlay}>
                      <Text style={styles.photoOverlayText}>🤖 Analyzing photo…</Text>
                    </View>
                  )}
                </View>
              ) : (
                <TouchableOpacity style={styles.photoBtn} onPress={pickPhoto}>
                  <Text style={styles.photoBtnText}>📷 Add a photo — AI can help fill in the details</Text>
                </TouchableOpacity>
              )}
              {aiSuggestion && (
                <View style={[styles.aiBanner, aiSuggestion.safety_concern && styles.aiBannerWarning]}>
                  <Text style={[styles.aiBannerText, aiSuggestion.safety_concern && styles.aiBannerTextWarning]}>
                    {aiSuggestion.safety_concern ? '⚠️ This may be a safety concern - flagged as higher priority.' : '✓ AI suggested a category and priority below - feel free to adjust.'}
                    {aiSuggestion.confidence === 'low' ? ' (Low confidence - please double-check.)' : ''}
                  </Text>
                </View>
              )}

              <Text style={styles.fieldLabel}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  {CATEGORIES.map(c => (
                    <TouchableOpacity key={c} style={[styles.chip, form.category === c && { backgroundColor: theme.primary, borderColor: theme.primary }]} onPress={() => setForm(f => ({ ...f, category: c }))}>
                      <Text style={[styles.chipText, form.category === c && { color: colors.white }]}>{c}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>
              <Text style={styles.fieldLabel}>Priority</Text>
              <View style={styles.priorityRow}>
                {['low','medium','high','urgent'].map(p => (
                  <TouchableOpacity key={p} style={[styles.priorityBtn, form.priority === p && { backgroundColor: priorityDot(p) }]} onPress={() => setForm(f => ({ ...f, priority: p }))}>
                    <Text style={[styles.priorityText, form.priority === p && { color: colors.white }]} >{p}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={styles.fieldLabel}>Title</Text>
              <TextInput style={styles.input} placeholder="Brief description of the issue" value={form.title} onChangeText={v => setForm(f => ({ ...f, title: v }))} placeholderTextColor={colors.gray400} />
              <Text style={styles.fieldLabel}>Details</Text>
              <TextInput style={[styles.input, styles.textarea]} placeholder="Describe the problem in detail..." value={form.description} onChangeText={v => setForm(f => ({ ...f, description: v }))} multiline numberOfLines={4} placeholderTextColor={colors.gray400} textAlignVertical="top" />
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
                <Button label="Cancel" onPress={closeForm} variant="outline" style={{ flex: 1 }} />
                <Button label="Submit" onPress={submit} loading={submitting} color={theme.primary} style={{ flex: 1 }} />
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray50 },
  header: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.lg, paddingBottom: 0 },
  list: { padding: spacing.lg, gap: 12 },
  card: { padding: spacing.lg },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  dot: { width: 10, height: 10, borderRadius: 5, marginTop: 4, flexShrink: 0 },
  reqTitle: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  reqMeta: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  desc: { fontSize: typography.sm, color: colors.gray600, lineHeight: 20 },
  provider: { fontSize: typography.xs, color: colors.gray500, marginTop: 8 },
  resolutionBox: { backgroundColor: '#dcfce7', borderRadius: radius.md, padding: 10, marginTop: 8 },
  resolutionText: { fontSize: typography.xs, color: '#16a34a', fontWeight: '500' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: spacing.xl, paddingBottom: 36, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  modalTitle: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900 },
  modalClose: { fontSize: 18, color: colors.gray400, padding: 4 },
  fieldLabel: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700, marginBottom: 8 },
  photoBtn: { borderWidth: 1.5, borderColor: colors.gray200, borderStyle: 'dashed', borderRadius: radius.lg, padding: 16, alignItems: 'center', marginBottom: 16, backgroundColor: colors.gray50 },
  photoBtnText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray500, textAlign: 'center' },
  photoPreviewWrap: { marginBottom: 16, borderRadius: radius.lg, overflow: 'hidden' },
  photoPreview: { width: '100%', height: 160, backgroundColor: colors.gray100 },
  photoRemove: { position: 'absolute', top: 8, right: 8, width: 26, height: 26, borderRadius: 13, backgroundColor: 'rgba(0,0,0,0.6)', alignItems: 'center', justifyContent: 'center' },
  photoOverlay: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(0,0,0,0.6)', padding: 8 },
  photoOverlayText: { color: colors.white, fontSize: typography.xs, fontWeight: '600', textAlign: 'center' },
  aiBanner: { backgroundColor: '#eff6ff', borderRadius: radius.md, padding: 10, marginBottom: 16 },
  aiBannerWarning: { backgroundColor: '#fef2f2' },
  aiBannerText: { fontSize: typography.xs, color: '#1d4ed8', fontWeight: '600' },
  aiBannerTextWarning: { color: '#dc2626' },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900, backgroundColor: colors.white, marginBottom: 16 },
  textarea: { height: 96 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.full, borderWidth: 1.5, borderColor: colors.gray200, backgroundColor: colors.white },
  chipText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600 },
  priorityRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  priorityBtn: { flex: 1, paddingVertical: 8, borderRadius: radius.md, borderWidth: 1.5, borderColor: colors.gray200, alignItems: 'center' },
  priorityText: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, textTransform: 'capitalize' },
})
