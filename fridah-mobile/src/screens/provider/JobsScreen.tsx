import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Modal, TextInput, ScrollView, Alert } from 'react-native'
import { servicesApi } from '@/api/services'
import { Card, EmptyState, Badge } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate, truncate } from '@/utils/formatters'
import type { ServiceJob } from '@/types'

export const ProviderJobsScreen: React.FC = () => {
  const theme = getTheme('service_provider')
  const [jobs, setJobs] = useState<ServiceJob[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [quoteJob, setQuoteJob] = useState<ServiceJob | null>(null)
  const [quoteForm, setQuoteForm] = useState({ amount: '', estimated_days: '1', message: '' })
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    try {
      const { data } = await servicesApi.jobs({ status: 'open' })
      setJobs(data.data?.results || [])
    } catch { setJobs([]) }
    finally { setLoading(false); setRefreshing(false) }
  }

  useEffect(() => { load() }, [])

  const submitQuote = async () => {
    if (!quoteJob || !quoteForm.amount) { Alert.alert('Error', 'Enter your price.'); return }
    setSubmitting(true)
    try {
      await servicesApi.submitQuote({ job: quoteJob.id, amount: parseFloat(quoteForm.amount) as any, estimated_days: parseInt(quoteForm.estimated_days) as any, message: quoteForm.message } as any)
      setQuoteJob(null)
      setQuoteForm({ amount: '', estimated_days: '1', message: '' })
      load()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to submit quote.')
    } finally { setSubmitting(false) }
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <FlatList
        data={jobs}
        keyExtractor={i => i.id}
        contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="💼" message="No open jobs right now. Check back soon." />}
        renderItem={({ item }) => (
          <Card style={{ padding: spacing.lg }}>
            <View style={styles.cardTop}>
              <View style={{ flex: 1 }}>
                <Text style={styles.jobTitle}>{item.title}</Text>
                <Text style={styles.jobMeta}>📍 {item.town}, {item.county}</Text>
              </View>
              <Badge label={item.category_name} color={theme.primary} bg={theme.primaryLight} />
            </View>
            <Text style={styles.jobDesc}>{truncate(item.description, 100)}</Text>
            <View style={styles.jobFooter}>
              <View>
                {item.budget_estimate && <Text style={styles.budget}>Budget: {formatKES(item.budget_estimate)}</Text>}
                <Text style={styles.postedBy}>by {item.posted_by_name} · {formatDate(item.created_at)}</Text>
              </View>
              <TouchableOpacity style={[styles.quoteBtn, { backgroundColor: theme.primary }]}
                onPress={() => { setQuoteJob(item); setQuoteForm({ amount: String(item.budget_estimate || ''), estimated_days: '1', message: '' }) }}>
                <Text style={styles.quoteBtnText}>Submit Quote</Text>
              </TouchableOpacity>
            </View>
          </Card>
        )}
      />

      <Modal visible={!!quoteJob} animationType="slide" transparent onRequestClose={() => setQuoteJob(null)}>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>Submit Quote</Text>
              <TouchableOpacity onPress={() => setQuoteJob(null)}><Text style={styles.closeBtn}>✕</Text></TouchableOpacity>
            </View>
            <Text style={styles.jobTitleModal}>{quoteJob?.title}</Text>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.fieldLabel}>Your Price (KES)</Text>
              <TextInput style={styles.input} value={quoteForm.amount} onChangeText={v => setQuoteForm(f => ({ ...f, amount: v }))} keyboardType="numeric" placeholder="e.g. 5000" placeholderTextColor={colors.gray400} />
              <Text style={styles.fieldLabel}>Estimated Days</Text>
              <TextInput style={styles.input} value={quoteForm.estimated_days} onChangeText={v => setQuoteForm(f => ({ ...f, estimated_days: v }))} keyboardType="numeric" placeholder="1" placeholderTextColor={colors.gray400} />
              <Text style={styles.fieldLabel}>Message to Client</Text>
              <TextInput style={[styles.input, { height: 80 }]} value={quoteForm.message} onChangeText={v => setQuoteForm(f => ({ ...f, message: v }))} multiline placeholder="Introduce yourself, describe your approach…" placeholderTextColor={colors.gray400} textAlignVertical="top" />
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
                <Button label="Cancel" onPress={() => setQuoteJob(null)} variant="outline" style={{ flex: 1 }} />
                <Button label="Submit Quote" onPress={submitQuote} loading={submitting} color={theme.primary} style={{ flex: 1 }} />
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  jobTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900 },
  jobMeta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  jobDesc: { fontSize: typography.sm, color: colors.gray600, lineHeight: 20, marginBottom: 12 },
  jobFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  budget: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  postedBy: { fontSize: typography.xs, color: colors.gray400, marginTop: 2 },
  quoteBtn: { borderRadius: radius.lg, paddingVertical: 10, paddingHorizontal: 16 },
  quoteBtnText: { color: colors.white, fontWeight: '700', fontSize: typography.sm },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: spacing.xl, paddingBottom: 36, maxHeight: '85%' },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  sheetTitle: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900 },
  closeBtn: { fontSize: 18, color: colors.gray400, padding: 4 },
  jobTitleModal: { fontSize: typography.sm, color: colors.gray500, marginBottom: 16 },
  fieldLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900, marginBottom: 14 },
})
