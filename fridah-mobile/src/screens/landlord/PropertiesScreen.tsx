import React, { useState, useEffect, useRef } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert, TextInput, Modal, ScrollView, Linking, ActivityIndicator } from 'react-native'
import { propertiesApi, documentsApi, agencyApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatDate } from '@/utils/formatters'
import type { Property, OwnedProperty, AgencyDirectoryEntry } from '@/types'

export const LandlordPropertiesScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [properties, setProperties] = useState<Property[]>([])
  const [ownedProperties, setOwnedProperties] = useState<OwnedProperty[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ name:'', property_type:'apartment', county:'', town:'', estate:'', total_units:'1', description:'' })
  const set = (k:string, v:string) => setForm(f => ({...f,[k]:v}))
  const [expandedDocsFor, setExpandedDocsFor] = useState<string | null>(null)
  const [documents, setDocuments] = useState<any[]>([])
  const [docsLoading, setDocsLoading] = useState(false)

  // Assign-to-agency
  const [assignTarget, setAssignTarget] = useState<Property | null>(null)
  const [agencySearchQuery, setAgencySearchQuery] = useState('')
  const [agencySearchResults, setAgencySearchResults] = useState<AgencyDirectoryEntry[]>([])
  const [searchingAgencies, setSearchingAgencies] = useState(false)
  const [selectedAgency, setSelectedAgency] = useState<AgencyDirectoryEntry | null>(null)
  const [feePercent, setFeePercent] = useState('5')
  const [payoutRule, setPayoutRule] = useState<'owner_direct' | 'agency_collects'>('owner_direct')
  const [assigning, setAssigning] = useState(false)
  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  const managementFor = (propertyId: string) => ownedProperties.find(op => op.id === propertyId)

  const loadOwnedProperties = async () => {
    try {
      const { data } = await agencyApi.ownerProperties()
      setOwnedProperties((data as any).data || [])
    } catch { setOwnedProperties([]) }
  }

  const load = async () => {
    try { const { data } = await propertiesApi.list(); setProperties(data.data?.results || []) }
    catch { setProperties([]) } finally { setLoading(false); setRefreshing(false) }
    loadOwnedProperties()
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!form.name||!form.county||!form.town) { Alert.alert('Error','Fill required fields'); return }
    setSaving(true)
    try { await propertiesApi.create({...form, total_units: parseInt(form.total_units)}); setShowForm(false); load() }
    catch (e:any) { Alert.alert('Error', e?.response?.data?.error?.message||'Failed') }
    finally { setSaving(false) }
  }

  const toggleDocuments = async (propertyId: string) => {
    if (expandedDocsFor === propertyId) { setExpandedDocsFor(null); return }
    setExpandedDocsFor(propertyId)
    setDocsLoading(true)
    try {
      const { data } = await documentsApi.list(propertyId)
      setDocuments((data as any).data?.results || (data as any).data || [])
    } catch { setDocuments([]) } finally { setDocsLoading(false) }
  }

  const openAssign = (property: Property) => {
    setAssignTarget(property)
    setAgencySearchQuery(''); setAgencySearchResults([]); setSelectedAgency(null)
    setFeePercent('5'); setPayoutRule('owner_direct')
  }

  const onAgencySearchChange = (text: string) => {
    setAgencySearchQuery(text)
    setSelectedAgency(null)
    if (searchDebounce.current) clearTimeout(searchDebounce.current)
    if (!text.trim()) { setAgencySearchResults([]); return }
    searchDebounce.current = setTimeout(async () => {
      setSearchingAgencies(true)
      try {
        const { data } = await agencyApi.searchDirectory(text.trim())
        setAgencySearchResults((data as any).data || [])
      } catch { setAgencySearchResults([]) }
      finally { setSearchingAgencies(false) }
    }, 350)
  }

  const confirmAssign = async () => {
    if (!assignTarget || !selectedAgency) { Alert.alert('Error', 'Pick an agency first.'); return }
    setAssigning(true)
    try {
      await agencyApi.assignProperty({
        property_id: assignTarget.id, agency_id: selectedAgency.id,
        start_date: new Date().toISOString().slice(0, 10),
        management_fee_percent: parseFloat(feePercent) || 5, payout_rule: payoutRule,
      })
      setAssignTarget(null)
      loadOwnedProperties()
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.error?.message || 'Failed to assign property. Check the agency and try again.')
    } finally {
      setAssigning(false)
    }
  }

  return (
    <View style={{flex:1,backgroundColor:colors.gray50}}>
      <View style={{flexDirection:'row',justifyContent:'flex-end',padding:spacing.lg,paddingBottom:4}}>
        <Button label="+ Add Property" onPress={() => setShowForm(true)} color={theme.primary} size="sm" />
      </View>
      <FlatList data={properties} keyExtractor={i=>i.id} contentContainerStyle={{padding:spacing.lg,gap:12}}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => {setRefreshing(true);load()}} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🏠" message="No properties yet. Add your first one!" />}
        renderItem={({item}) => (
          <Card style={{padding:spacing.lg}}>
            <View style={{flexDirection:'row',justifyContent:'space-between',alignItems:'flex-start',marginBottom:8}}>
              <View style={{flex:1}}>
                <Text style={{fontSize:typography.base,fontWeight:'700',color:colors.gray900}}>{item.name}</Text>
                <Text style={{fontSize:typography.xs,color:colors.gray500,marginTop:2}}>📍 {item.estate ? item.estate+', ':''}{item.town}, {item.county}</Text>
              </View>
              <StatusBadge status={item.status} />
            </View>
            <View style={{flexDirection:'row',gap:16}}>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Units</Text><Text style={{fontWeight:'700',color:colors.gray900}}>{item.total_units}</Text></View>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Vacant</Text><Text style={{fontWeight:'700',color:'#16a34a'}}>{item.vacant_units_count}</Text></View>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Type</Text><Text style={{fontWeight:'700',color:colors.gray900,textTransform:'capitalize'}}>{item.property_type}</Text></View>
            </View>
            <TouchableOpacity style={styles.docsToggle} onPress={() => toggleDocuments(item.id)}>
              <Text style={styles.docsToggleText}>📁 {expandedDocsFor === item.id ? 'Hide documents' : 'View documents'}</Text>
            </TouchableOpacity>
            {expandedDocsFor === item.id && (
              <View style={styles.docsPanel}>
                {docsLoading ? <Text style={styles.docsMuted}>Loading…</Text> : documents.length === 0 ? (
                  <Text style={styles.docsMuted}>No documents uploaded yet. Upload from the FRIDAH web app.</Text>
                ) : documents.map(d => (
                  <TouchableOpacity key={d.id} style={styles.docRow} onPress={() => Linking.openURL(d.file)}>
                    <Text style={styles.docTitle}>{d.title} (v{d.version})</Text>
                    <Text style={styles.docMeta}>{d.document_type_display} {d.expiry_date ? `· expires ${formatDate(d.expiry_date)}` : ''}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            <View style={styles.managementRow}>
              {managementFor(item.id)?.managing_agency ? (
                <View style={styles.agencyBadge}>
                  <Text style={styles.agencyBadgeText}>🏢 {managementFor(item.id)?.managing_agency?.name}</Text>
                </View>
              ) : (
                <>
                  <Text style={styles.selfManagedText}>Self-managed</Text>
                  <TouchableOpacity onPress={() => openAssign(item)}>
                    <Text style={[styles.assignLink, { color: theme.primary }]}>Assign to agency</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
          </Card>
        )}
      />
      <Modal visible={showForm} animationType="slide" transparent onRequestClose={() => setShowForm(false)}>
        <View style={{flex:1,backgroundColor:'rgba(0,0,0,0.5)',justifyContent:'flex-end'}}>
          <View style={{backgroundColor:colors.white,borderTopLeftRadius:24,borderTopRightRadius:24,padding:spacing.xl,paddingBottom:36}}>
            <View style={{flexDirection:'row',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
              <Text style={{fontSize:typography.lg,fontWeight:'700',color:colors.gray900}}>Add Property</Text>
              <TouchableOpacity onPress={() => setShowForm(false)}><Text style={{fontSize:18,color:colors.gray400}}>✕</Text></TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              {[['Name','name','e.g. Westlands Heights'],['County','county','e.g. Nairobi'],['Town','town','e.g. Westlands'],['Estate','estate','e.g. Lavington']].map(([label,key,ph]) => (
                <View key={key} style={{marginBottom:14}}>
                  <Text style={{fontSize:typography.xs,fontWeight:'600',color:colors.gray600,marginBottom:6}}>{label}</Text>
                  <TextInput style={{borderWidth:1.5,borderColor:colors.gray200,borderRadius:radius.md,paddingHorizontal:14,paddingVertical:11,fontSize:typography.sm,color:colors.gray900}} value={(form as any)[key]} onChangeText={v=>set(key,v)} placeholder={ph} placeholderTextColor={colors.gray400} />
                </View>
              ))}
              <Text style={{fontSize:typography.xs,fontWeight:'600',color:colors.gray600,marginBottom:6}}>Total Units</Text>
              <TextInput style={{borderWidth:1.5,borderColor:colors.gray200,borderRadius:radius.md,paddingHorizontal:14,paddingVertical:11,fontSize:typography.sm,color:colors.gray900,marginBottom:16}} value={form.total_units} onChangeText={v=>set('total_units',v)} keyboardType="numeric" placeholderTextColor={colors.gray400}/>
              <View style={{flexDirection:'row',gap:10,marginTop:4}}>
                <Button label="Cancel" onPress={() => setShowForm(false)} variant="outline" style={{flex:1}} />
                <Button label="Submit" onPress={save} loading={saving} color={theme.primary} style={{flex:1}} />
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      <Modal visible={!!assignTarget} animationType="slide" transparent onRequestClose={() => setAssignTarget(null)}>
        <View style={{flex:1,backgroundColor:'rgba(0,0,0,0.5)',justifyContent:'flex-end'}}>
          <View style={{backgroundColor:colors.white,borderTopLeftRadius:24,borderTopRightRadius:24,padding:spacing.xl,paddingBottom:36,maxHeight:'85%'}}>
            <View style={{flexDirection:'row',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
              <Text style={{fontSize:typography.lg,fontWeight:'700',color:colors.gray900,flex:1}} numberOfLines={1}>
                Assign "{assignTarget?.name}" to an Agency
              </Text>
              <TouchableOpacity onPress={() => setAssignTarget(null)}><Text style={{fontSize:18,color:colors.gray400}}>✕</Text></TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
              <Text style={styles.formLabel}>Search Agencies</Text>
              <TextInput
                style={styles.searchInput}
                placeholder="Search by name, town, or county…"
                placeholderTextColor={colors.gray400}
                value={agencySearchQuery}
                onChangeText={onAgencySearchChange}
              />
              {searchingAgencies && <ActivityIndicator style={{ marginTop: 8 }} color={theme.primary} />}
              {!searchingAgencies && agencySearchResults.map((a) => (
                <TouchableOpacity key={a.id} style={styles.agencyResultRow} onPress={() => { setSelectedAgency(a); setAgencySearchResults([]); setAgencySearchQuery('') }}>
                  <View style={[styles.agencyAvatar, { backgroundColor: theme.primaryLight }]}>
                    <Text style={[styles.agencyAvatarText, { color: theme.primaryDark }]}>{a.name[0]?.toUpperCase()}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.agencyResultName}>{a.name}</Text>
                    <Text style={styles.agencyResultMeta}>{a.town}, {a.county} · {a.managed_properties_count} properties managed</Text>
                  </View>
                </TouchableOpacity>
              ))}

              {selectedAgency && (
                <View style={[styles.selectedAgencyRow, { backgroundColor: theme.primaryBg }]}>
                  <View style={[styles.agencyAvatar, { backgroundColor: theme.primaryLight }]}>
                    <Text style={[styles.agencyAvatarText, { color: theme.primaryDark }]}>{selectedAgency.name[0]?.toUpperCase()}</Text>
                  </View>
                  <Text style={styles.agencyResultName}>{selectedAgency.name}</Text>
                  <TouchableOpacity onPress={() => setSelectedAgency(null)}><Text style={styles.changeLink}>Change</Text></TouchableOpacity>
                </View>
              )}

              <Text style={[styles.formLabel, { marginTop: 16 }]}>Management Fee %</Text>
              <TextInput style={styles.searchInput} value={feePercent} onChangeText={setFeePercent} keyboardType="numeric" />

              <Text style={[styles.formLabel, { marginTop: 12 }]}>Payout Rule</Text>
              {(['owner_direct', 'agency_collects'] as const).map((rule) => (
                <TouchableOpacity key={rule} style={[styles.payoutOption, payoutRule === rule && { borderColor: theme.primary, backgroundColor: theme.primaryBg }]} onPress={() => setPayoutRule(rule)}>
                  <Text style={[styles.payoutOptionText, payoutRule === rule && { color: theme.primaryDark, fontWeight: '700' }]}>
                    {rule === 'owner_direct' ? 'I receive rent directly' : 'Agency collects, then remits to me'}
                  </Text>
                </TouchableOpacity>
              ))}

              <View style={{flexDirection:'row',gap:10,marginTop:16}}>
                <Button label="Cancel" onPress={() => setAssignTarget(null)} variant="outline" style={{flex:1}} />
                <Button label="Assign" onPress={confirmAssign} loading={assigning} disabled={!selectedAgency} color={theme.primary} style={{flex:1}} />
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  docsToggle: { marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: colors.gray100 },
  docsToggleText: { fontSize: typography.xs, fontWeight: '700', color: colors.gray600 },
  docsPanel: { marginTop: 8, backgroundColor: colors.gray50, borderRadius: radius.md, padding: spacing.md, gap: 8 },
  docsMuted: { fontSize: typography.xs, color: colors.gray400 },
  docRow: { paddingVertical: 4 },
  docTitle: { fontSize: typography.sm, fontWeight: '600', color: colors.gray900 },
  docMeta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },

  managementRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: colors.gray100 },
  agencyBadge: { backgroundColor: '#e0f2fe', borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  agencyBadgeText: { fontSize: typography.xs, fontWeight: '600', color: '#0369a1' },
  selfManagedText: { fontSize: typography.xs, color: colors.gray400, fontWeight: '600' },
  assignLink: { fontSize: typography.xs, fontWeight: '700' },

  formLabel: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  searchInput: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 11, fontSize: typography.sm, color: colors.gray900 },
  agencyResultRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8 },
  agencyAvatar: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  agencyAvatarText: { fontSize: typography.xs, fontWeight: '700' },
  agencyResultName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray800 },
  agencyResultMeta: { fontSize: 11, color: colors.gray400, marginTop: 1 },
  selectedAgencyRow: { flexDirection: 'row', alignItems: 'center', gap: 10, borderRadius: radius.md, padding: 10, marginTop: 8 },
  changeLink: { fontSize: 11, color: colors.gray400, textDecorationLine: 'underline', marginLeft: 'auto' },
  payoutOption: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, padding: 10, marginBottom: 8 },
  payoutOptionText: { fontSize: typography.sm, color: colors.gray600 },
})
