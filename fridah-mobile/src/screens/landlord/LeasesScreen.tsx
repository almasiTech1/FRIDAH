import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, Alert, TextInput } from 'react-native'
import { rentalsApi, renewalsApi, riskScoreApi, blacklistApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Lease } from '@/types'

interface Renewal {
  id: string; tenant_name: string; unit_number: string; property_name: string
  proposed_rent_amount: number; proposed_start_date: string; proposed_end_date: string; status: string
}

export const LandlordLeasesScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [tab, setTab] = useState<'leases' | 'renewals'>('leases')
  const [leases, setLeases] = useState<Lease[]>([])
  const [renewals, setRenewals] = useState<Renewal[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [expandedTenant, setExpandedTenant] = useState<string | null>(null)
  const [screeningData, setScreeningData] = useState<{ risk: any; flags: any[] } | null>(null)
  const [editingRenewalId, setEditingRenewalId] = useState<string | null>(null)
  const [editRent, setEditRent] = useState('')

  const load = async () => {
    try {
      const [{ data: leaseData }, renewalRes] = await Promise.all([rentalsApi.leases(), renewalsApi.list()])
      setLeases(leaseData.data?.results || [])
      setRenewals((renewalRes.data as any).data?.results || (renewalRes.data as any).data || [])
    } catch { setLeases([]); setRenewals([]) } finally { setLoading(false); setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  const activate = async (id: string) => { try { await rentalsApi.activateLease(id); load() } catch {} }
  const terminate = (id: string) => Alert.alert('Terminate Lease', 'Are you sure?', [
    { text:'Cancel', style:'cancel' },
    { text:'Terminate', style:'destructive', onPress: async () => { try { await rentalsApi.terminateLease(id,'Terminated by landlord'); load() } catch {} } }
  ])

  const toggleScreening = async (leaseItem: Lease) => {
    if (expandedTenant === leaseItem.tenant) { setExpandedTenant(null); return }
    setExpandedTenant(leaseItem.tenant)
    setScreeningData(null)
    try {
      const [riskRes, flagsRes] = await Promise.all([
        riskScoreApi.get(leaseItem.tenant),
        blacklistApi.check(leaseItem.tenant),
      ])
      setScreeningData({ risk: (riskRes.data as any).data, flags: (flagsRes.data as any).data?.flags || [] })
    } catch { setScreeningData({ risk: null, flags: [] }) }
  }

  const saveRenewalRent = async (id: string) => {
    await renewalsApi.updateOffer(id, { proposed_rent_amount: Number(editRent) })
    setEditingRenewalId(null)
    load()
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.segmentRow}>
        <TouchableOpacity style={[styles.segment, tab === 'leases' && { backgroundColor: theme.primary }]} onPress={() => setTab('leases')}>
          <Text style={[styles.segmentText, tab === 'leases' && { color: colors.white }]}>Leases</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.segment, tab === 'renewals' && { backgroundColor: theme.primary }]} onPress={() => setTab('renewals')}>
          <Text style={[styles.segmentText, tab === 'renewals' && { color: colors.white }]}>Renewals {renewals.filter(r => r.status === 'pending').length > 0 ? `(${renewals.filter(r => r.status === 'pending').length})` : ''}</Text>
        </TouchableOpacity>
      </View>

      {tab === 'leases' ? (
        <FlatList data={leases} keyExtractor={i=>i.id} contentContainerStyle={{padding:spacing.lg,gap:12}}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => {setRefreshing(true);load()}} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="📋" message="No leases yet" />}
          renderItem={({item}) => (
            <Card style={{padding:spacing.lg}}>
              <View style={{flexDirection:'row',justifyContent:'space-between',marginBottom:10}}>
                <TouchableOpacity onPress={() => toggleScreening(item)}>
                  <Text style={{fontSize:typography.base,fontWeight:'700',color:colors.gray900}}>{item.tenant_name} 🔍</Text>
                  <Text style={{fontSize:typography.xs,color:colors.gray500}}>{item.property_name} · Unit {item.unit_number}</Text>
                </TouchableOpacity>
                <StatusBadge status={item.status} />
              </View>
              <View style={{flexDirection:'row',gap:16,marginBottom:12}}>
                <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Rent</Text><Text style={{fontWeight:'700',color:colors.gray900}}>{formatKES(item.rent_amount)}/mo</Text></View>
                <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Start</Text><Text style={{fontWeight:'700',color:colors.gray900}}>{formatDate(item.start_date)}</Text></View>
                <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Due Day</Text><Text style={{fontWeight:'700',color:colors.gray900}}>Day {item.rent_due_day}</Text></View>
              </View>

              {expandedTenant === item.tenant && (
                <View style={styles.screeningPanel}>
                  {!screeningData ? <Text style={styles.screeningMuted}>Loading…</Text> : (
                    <>
                      <View style={{flexDirection:'row',alignItems:'center',gap:8,marginBottom:8}}>
                        <Text style={styles.riskScoreBig}>{screeningData.risk?.score ?? '—'}<Text style={{fontSize:12,color:colors.gray400}}>/10</Text></Text>
                        <Text style={styles.screeningLabel}>Risk score · {screeningData.risk?.on_time_payment_rate ?? 0}% on-time</Text>
                      </View>
                      {screeningData.flags.length > 0 ? (
                        screeningData.flags.map((f: any) => (
                          <View key={f.id} style={styles.flagRow}>
                            <Text style={styles.flagReason}>⚠ {f.reason.replace('_',' ')}</Text>
                            <Text style={styles.screeningMuted}>{f.details}</Text>
                          </View>
                        ))
                      ) : <Text style={styles.screeningMuted}>No blacklist flags.</Text>}
                    </>
                  )}
                </View>
              )}

              <View style={{flexDirection:'row',gap:8, marginTop: 12}}>
                {item.status==='pending' && <TouchableOpacity style={{flex:1,backgroundColor:theme.primary,borderRadius:radius.lg,paddingVertical:10,alignItems:'center'}} onPress={() => activate(item.id)}><Text style={{color:colors.white,fontWeight:'700',fontSize:typography.sm}}>Activate</Text></TouchableOpacity>}
                {item.status==='active' && <TouchableOpacity style={{flex:1,backgroundColor:'#fee2e2',borderRadius:radius.lg,paddingVertical:10,alignItems:'center'}} onPress={() => terminate(item.id)}><Text style={{color:'#dc2626',fontWeight:'700',fontSize:typography.sm}}>Terminate</Text></TouchableOpacity>}
              </View>
            </Card>
          )}
        />
      ) : (
        <FlatList data={renewals} keyExtractor={i=>i.id} contentContainerStyle={{padding:spacing.lg,gap:12}}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => {setRefreshing(true);load()}} tintColor={theme.primary} />}
          ListEmptyComponent={<EmptyState emoji="🔄" message="No renewal offers - these are created automatically 60 days before a lease ends." />}
          renderItem={({item}) => (
            <Card style={{padding:spacing.lg}}>
              <View style={{flexDirection:'row',justifyContent:'space-between',marginBottom:10}}>
                <View>
                  <Text style={{fontSize:typography.base,fontWeight:'700',color:colors.gray900}}>{item.tenant_name}</Text>
                  <Text style={{fontSize:typography.xs,color:colors.gray500}}>{item.property_name} · Unit {item.unit_number}</Text>
                </View>
                <StatusBadge status={item.status} />
              </View>
              <View style={{flexDirection:'row',gap:16,marginBottom:12}}>
                <View>
                  <Text style={{fontSize:typography.xs,color:colors.gray400}}>Proposed rent</Text>
                  {editingRenewalId === item.id ? (
                    <TextInput style={styles.rentInput} value={editRent} onChangeText={setEditRent} keyboardType="numeric" />
                  ) : (
                    <Text style={{fontWeight:'700',color:colors.gray900}}>{formatKES(item.proposed_rent_amount)}</Text>
                  )}
                </View>
                <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Term</Text><Text style={{fontWeight:'700',color:colors.gray900,fontSize:typography.xs}}>{formatDate(item.proposed_start_date)} - {formatDate(item.proposed_end_date)}</Text></View>
              </View>
              {item.status === 'pending' && (
                editingRenewalId === item.id ? (
                  <View style={{flexDirection:'row',gap:8}}>
                    <Button label="Save" color={theme.primary} onPress={() => saveRenewalRent(item.id)} style={{flex:1}} />
                    <Button label="Cancel" variant="outline" onPress={() => setEditingRenewalId(null)} style={{flex:1}} />
                  </View>
                ) : (
                  <Button label="Edit offer" variant="outline" onPress={() => { setEditingRenewalId(item.id); setEditRent(String(item.proposed_rent_amount)) }} />
                )
              )}
            </Card>
          )}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  segmentRow: { flexDirection: 'row', gap: 8, padding: spacing.lg, paddingBottom: 0 },
  segment: { flex: 1, paddingVertical: 10, borderRadius: radius.lg, backgroundColor: colors.white, alignItems: 'center', borderWidth: 1, borderColor: colors.gray100 },
  segmentText: { fontSize: typography.sm, fontWeight: '700', color: colors.gray600 },
  screeningPanel: { backgroundColor: colors.gray50, borderRadius: radius.md, padding: spacing.md, marginBottom: 4 },
  riskScoreBig: { fontSize: 22, fontWeight: '900', color: colors.gray900 },
  screeningLabel: { fontSize: typography.xs, color: colors.gray500 },
  screeningMuted: { fontSize: typography.xs, color: colors.gray400 },
  flagRow: { marginTop: 4 },
  flagReason: { fontSize: typography.xs, fontWeight: '700', color: colors.red600 },
  rentInput: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.sm, padding: 6, fontSize: typography.sm, width: 100 },
})
