import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  TextInput, ActivityIndicator, Modal, Alert, Image,
} from 'react-native'
import { useRoute, useNavigation } from '@react-navigation/native'
import { propertiesApi, rentalsApi } from '@/api/services'
import { Card, Badge } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES } from '@/utils/formatters'
import type { Property, Unit } from '@/types'

export const PropertyDetailScreen: React.FC = () => {
  const theme = getTheme('tenant')
  const route = useRoute<any>()
  const nav = useNavigation<any>()
  const { propertyId } = route.params || {}

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [myApplications, setMyApplications] = useState<any[]>([])

  const [applyUnit, setApplyUnit] = useState<Unit | null>(null)
  const [moveInDate, setMoveInDate] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [costOfLivingOpen, setCostOfLivingOpen] = useState('')
  const [costOfLivingLoading, setCostOfLivingLoading] = useState(false)
  const [costOfLivingData, setCostOfLivingData] = useState<any>(null)
  const [personalTransport, setPersonalTransport] = useState('')
  const [personalOther, setPersonalOther] = useState('')

  const toggleCostOfLiving = async (unitId: string) => {
    if (costOfLivingOpen === unitId) {
      setCostOfLivingOpen('')
      return
    }
    setCostOfLivingOpen(unitId)
    setCostOfLivingData(null)
    setPersonalTransport('')
    setPersonalOther('')
    setCostOfLivingLoading(true)
    try {
      const { data } = await propertiesApi.costOfLiving(unitId)
      setCostOfLivingData((data as any).data || data)
    } catch {
      setCostOfLivingData(null)
    } finally {
      setCostOfLivingLoading(false)
    }
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await propertiesApi.get(propertyId)
      setProperty((data as any).data || data)
    } catch {
      setProperty(null)
    }
    try {
      const { data } = await rentalsApi.applications()
      setMyApplications((data as any).results || (data as any).data || [])
    } catch { setMyApplications([]) }
    setLoading(false)
  }, [propertyId])

  useEffect(() => { load() }, [load])

  const pendingFor = (unitId: string) => myApplications.find((a) => a.unit === unitId && a.status === 'pending')

  const openApply = (unit: Unit) => {
    setApplyUnit(unit)
    setMoveInDate('')
    setMessage('')
  }

  const submit = async () => {
    if (!applyUnit) return
    setSubmitting(true)
    try {
      await rentalsApi.applyToUnit(applyUnit.id, {
        message: message || undefined,
        preferred_move_in_date: moveInDate || undefined,
      })
      setApplyUnit(null)
      Alert.alert('Application submitted', 'The landlord will review your application.')
      await load()
    } catch (e: any) {
      Alert.alert('Could not submit', e?.response?.data?.error?.message || 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" color={theme.primary} /></View>
  }
  if (!property) {
    return <View style={styles.center}><Text style={{ color: colors.gray400 }}>Property not found.</Text></View>
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <ScrollView contentContainerStyle={styles.content}>
        <TouchableOpacity onPress={() => nav.goBack()} style={{ marginBottom: 12 }}>
          <Text style={{ color: colors.gray500, fontWeight: '600' }}>&larr; Back</Text>
        </TouchableOpacity>

        <View style={[styles.imgBox, { backgroundColor: theme.primaryLight }]}>
          {property.primary_image ? (
            <Image source={{ uri: property.primary_image }} style={{ width: '100%', height: '100%' }} resizeMode="cover" />
          ) : (
            <Text style={{ fontSize: 48 }}>🏠</Text>
          )}
        </View>

        <Card style={{ marginTop: 14 }}>
          <View style={styles.row}>
            <Text style={styles.name}>{property.name}</Text>
            <Badge label={property.property_type} color={theme.primary} bg={theme.primaryLight} />
          </View>
          <Text style={styles.location}>📍 {property.estate ? property.estate + ', ' : ''}{property.town}, {property.county}</Text>
          {!!property.description && <Text style={styles.description}>{property.description}</Text>}
          {!!property.amenities?.length && (
            <View style={styles.amenities}>
              {property.amenities.map((a) => (
                <View key={a} style={styles.chip}><Text style={styles.chipText}>{a}</Text></View>
              ))}
            </View>
          )}
        </Card>

        <Text style={styles.sectionTitle}>Units</Text>
        {!property.units?.length ? (
          <Card><Text style={{ color: colors.gray400, textAlign: 'center', paddingVertical: 16 }}>No units listed yet.</Text></Card>
        ) : (
          property.units.map((u) => {
            const applied = pendingFor(u.id)
            return (
              <Card key={u.id} style={styles.unitCardWrap}>
                <View style={styles.unitCardRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.unitTitle}>Unit {u.unit_number}</Text>
                    <Text style={styles.unitSub}>{u.bedrooms} bed &middot; {u.bathrooms} bath</Text>
                    <Text style={[styles.unitPrice, { color: theme.primary }]}>{formatKES(u.rent_amount)}/mo</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Badge label={u.status} color={u.status === 'vacant' ? '#15803d' : colors.gray600} bg={u.status === 'vacant' ? '#f0fdf4' : colors.gray100} />
                    {u.status === 'vacant' && (
                      <TouchableOpacity
                        style={[styles.applyBtn, { backgroundColor: applied ? colors.gray200 : theme.primary }]}
                        disabled={!!applied}
                        onPress={() => openApply(u)}
                      >
                        <Text style={[styles.applyBtnText, applied && { color: colors.gray500 }]}>{applied ? 'Applied ✓' : 'Apply to Rent'}</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>

                <TouchableOpacity onPress={() => toggleCostOfLiving(u.id)}>
                  <Text style={[styles.colToggle, { color: theme.primary }]}>
                    {costOfLivingOpen === u.id ? 'Hide cost of living breakdown' : '💰 See total cost of living'}
                  </Text>
                </TouchableOpacity>

                {costOfLivingOpen === u.id && (
                  <View style={styles.colBox}>
                    {costOfLivingLoading ? (
                      <Text style={styles.colLoading}>Loading…</Text>
                    ) : costOfLivingData ? (
                      <View>
                        <View style={styles.colRow}>
                          <Text style={styles.colLabel}>Rent</Text>
                          <Text style={styles.colValue}>{formatKES(costOfLivingData.rent)}</Text>
                        </View>
                        {costOfLivingData.utilities.map((line: any) => (
                          <View key={line.utility_type} style={styles.colRow}>
                            <Text style={styles.colLabel}>{line.utility_type}</Text>
                            <Text style={styles.colValue}>{line.monthly_estimate ? formatKES(line.monthly_estimate) : 'No data yet'}</Text>
                          </View>
                        ))}
                        <View style={[styles.colRow, styles.colTotalRow]}>
                          <Text style={styles.colTotalLabel}>Platform total</Text>
                          <Text style={[styles.colTotalValue, { color: theme.primary }]}>{formatKES(costOfLivingData.platform_total)}</Text>
                        </View>
                        <Text style={styles.colNote}>{costOfLivingData.note}</Text>

                        <View style={styles.colPersonalSection}>
                          <Text style={styles.colPersonalLabel}>Add your own estimates</Text>
                          <View style={{ flexDirection: 'row', gap: 8 }}>
                            <TextInput
                              style={styles.colInput} placeholder="Transport" keyboardType="number-pad"
                              placeholderTextColor={colors.gray400} value={personalTransport} onChangeText={setPersonalTransport}
                            />
                            <TextInput
                              style={styles.colInput} placeholder="Other" keyboardType="number-pad"
                              placeholderTextColor={colors.gray400} value={personalOther} onChangeText={setPersonalOther}
                            />
                          </View>
                          <View style={styles.colRow}>
                            <Text style={styles.colTotalLabel}>Your estimated total</Text>
                            <Text style={styles.colTotalValue}>
                              {formatKES(Number(costOfLivingData.platform_total) + (Number(personalTransport) || 0) + (Number(personalOther) || 0))}
                            </Text>
                          </View>
                        </View>
                      </View>
                    ) : null}
                  </View>
                )}
              </Card>
            )
          })
        )}
      </ScrollView>

      <Modal visible={!!applyUnit} animationType="slide" transparent onRequestClose={() => setApplyUnit(null)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Apply for Unit {applyUnit?.unit_number}</Text>
              <TouchableOpacity onPress={() => setApplyUnit(null)}><Text style={styles.modalClose}>✕</Text></TouchableOpacity>
            </View>
            <Text style={styles.fieldLabel}>Preferred move-in date</Text>
            <TextInput
              style={styles.input} placeholder="YYYY-MM-DD" placeholderTextColor={colors.gray400}
              value={moveInDate} onChangeText={setMoveInDate}
            />
            <Text style={styles.fieldLabel}>Message to landlord (optional)</Text>
            <TextInput
              style={[styles.input, styles.textarea]} placeholder="Tell the landlord a bit about yourself..."
              placeholderTextColor={colors.gray400} value={message} onChangeText={setMessage}
              multiline numberOfLines={4} textAlignVertical="top"
            />
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
              <Button label="Cancel" onPress={() => setApplyUnit(null)} variant="outline" style={{ flex: 1 }} />
              <Button label="Submit Application" onPress={submit} loading={submitting} color={theme.primary} style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.gray50 },
  content: { padding: spacing.lg, paddingBottom: 40 },
  imgBox: { height: 200, borderRadius: radius.xl, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  name: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900, flex: 1, marginRight: 8 },
  location: { fontSize: typography.sm, color: colors.gray500, marginTop: 4 },
  description: { fontSize: typography.sm, color: colors.gray600, marginTop: 10, lineHeight: 20 },
  amenities: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  chip: { backgroundColor: colors.gray100, borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 5 },
  chipText: { fontSize: typography.xs, color: colors.gray600, fontWeight: '500' },
  sectionTitle: { fontSize: typography.base, fontWeight: '700', color: colors.gray900, marginTop: 20, marginBottom: 10 },
  unitCardWrap: { marginBottom: 10 },
  unitCardRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  colToggle: { fontSize: typography.xs, fontWeight: '700', marginTop: 10 },
  colBox: { marginTop: 8, padding: 10, borderRadius: radius.md, backgroundColor: colors.gray50 },
  colLoading: { fontSize: typography.xs, color: colors.gray400 },
  colRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  colLabel: { fontSize: typography.xs, color: colors.gray500, textTransform: 'capitalize' },
  colValue: { fontSize: typography.xs, fontWeight: '600', color: colors.gray900 },
  colTotalRow: { marginTop: 4, paddingTop: 6, borderTopWidth: 1, borderTopColor: colors.gray200 },
  colTotalLabel: { fontSize: typography.xs, fontWeight: '700', color: colors.gray700 },
  colTotalValue: { fontSize: typography.xs, fontWeight: '800', color: colors.gray900 },
  colNote: { fontSize: 10, color: colors.gray400, marginTop: 6, lineHeight: 14 },
  colPersonalSection: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.gray200 },
  colPersonalLabel: { fontSize: 11, fontWeight: '700', color: colors.gray600, marginBottom: 6 },
  colInput: { flex: 1, borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 7, fontSize: typography.xs, color: colors.gray900, backgroundColor: colors.white },
  unitTitle: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  unitSub: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  unitPrice: { fontSize: typography.sm, fontWeight: '700', marginTop: 4 },
  applyBtn: { marginTop: 8, paddingHorizontal: 12, paddingVertical: 7, borderRadius: radius.full },
  applyBtnText: { fontSize: typography.xs, fontWeight: '700', color: colors.white },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: colors.white, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: spacing.xl, paddingBottom: 36, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  modalTitle: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900 },
  modalClose: { fontSize: 18, color: colors.gray400, padding: 4 },
  fieldLabel: { fontSize: typography.sm, fontWeight: '600', color: colors.gray700, marginBottom: 8 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12, fontSize: typography.sm, color: colors.gray900, backgroundColor: colors.white, marginBottom: 16 },
  textarea: { height: 96 },
})
