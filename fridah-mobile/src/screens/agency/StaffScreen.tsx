import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl, TextInput, Alert } from 'react-native'
import { useAuthStore } from '@/stores/authStore'
import { agencyApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { agencyTheme, colors, spacing, typography, radius } from '@/theme'
import type { AgencyMembership, AgencyRole } from '@/types'

export const AgencyStaffScreen: React.FC = () => {
  const { agencies } = useAuthStore()
  const agency = agencies[0]
  const [members, setMembers] = useState<AgencyMembership[]>([])
  const [roles, setRoles] = useState<AgencyRole[]>([])
  const [selectedRole, setSelectedRole] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [credentials, setCredentials] = useState<{ name: string; login_email: string; temporary_password: string } | null>(null)

  const load = async () => {
    try {
      if (!agency) { setMembers([]); setRoles([]); return }
      const [mRes, rRes] = await Promise.all([agencyApi.members(agency.id), agencyApi.roles(agency.id)])
      setMembers((mRes.data as any).data?.results || (mRes.data as any).data || [])
      const roleList: AgencyRole[] = (rRes.data as any).data?.results || (rRes.data as any).data || []
      setRoles(roleList)
      if (roleList.length && !selectedRole) setSelectedRole(roleList[0].id)
    } catch {
      setMembers([]); setRoles([])
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }
  useEffect(() => { load() }, [agency])

  const invite = async () => {
    if (!agency || !email.trim() || !selectedRole) { Alert.alert('Error', 'Enter an email and select a role.'); return }
    setSaving(true)
    try {
      const res: any = await agencyApi.inviteMember(agency.id, email.trim(), selectedRole, {
        first_name: firstName.trim(), last_name: lastName.trim(), phone_number: phone.trim(),
      })
      const c = res?.data?.data?.credentials
      if (c) setCredentials({ name: `${firstName} ${lastName}`.trim(), login_email: c.login_email, temporary_password: c.temporary_password })
      setShowForm(false); setEmail(''); setFirstName(''); setLastName(''); setPhone('')
      load()
    } catch (e: any) {
      const d = e?.response?.data
      const fields = d && typeof d === 'object' && !d.error ? Object.values(d).flat().join(' ') : ''
      Alert.alert('Error', d?.error?.message || fields || 'Failed to add the staff member.')
    } finally {
      setSaving(false)
    }
  }

  const suspend = async (id: string) => { await agencyApi.suspendMember(id); load() }
  const remove = (id: string) => {
    Alert.alert('Remove Staff', 'Remove this staff member from the agency?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => { await agencyApi.removeMember(id); load() } },
    ])
  }

  const resetLogin = (m: AgencyMembership) => {
    Alert.alert('Reset login', `Issue a new temporary password to ${m.user_name || m.user_email}? Their current password stops working.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Reset', style: 'destructive', onPress: async () => {
        try {
          const res: any = await agencyApi.resetStaffPassword(m.id)
          const c = res?.data?.data
          setCredentials({ name: m.user_name || m.user_email, login_email: c.login_email, temporary_password: c.temporary_password })
        } catch (e: any) { Alert.alert('Error', e?.response?.data?.error?.message || 'Could not reset the login.') }
      } },
    ])
  }
  return (
    <View style={{ flex: 1, backgroundColor: colors.gray50 }}>
      <View style={styles.headerRow}>
        <Button label={showForm ? 'Cancel' : '+ Add Staff'} onPress={() => setShowForm(!showForm)} color={agencyTheme.primary} size="sm" />
      </View>

      {credentials && (
        <Card style={styles.formCard}>
          <Text style={{ fontWeight: '700', color: '#92400e' }}>Login for {credentials.name} - copy it now</Text>
          <Text style={styles.formHint}>Shown only once and cannot be retrieved later. Give it to them securely; they must change it at first login.</Text>
          <Text selectable style={{ fontSize: typography.sm, color: colors.gray900 }}>Email: {credentials.login_email}</Text>
          <Text selectable style={{ fontSize: typography.sm, fontWeight: '800', color: colors.gray900 }}>Temporary password: {credentials.temporary_password}</Text>
          <Button label="I have saved it - dismiss" size="sm" variant="outline" color={colors.gray600} onPress={() => setCredentials(null)} />
        </Card>
      )}

      {showForm && (
        <Card style={styles.formCard}>
          <Text style={styles.formHint}>Nobody registers themselves: FRIDAH creates the login with a temporary password you hand over, and they change it at first login. If the email already has an account, they are invited instead.</Text>
          <TextInput style={styles.input} placeholder="First name" value={firstName} onChangeText={setFirstName} accessibilityLabel="First name" />
          <TextInput style={styles.input} placeholder="Last name" value={lastName} onChangeText={setLastName} accessibilityLabel="Last name" />
          <TextInput style={styles.input} placeholder="Phone (+2547XXXXXXXX)" value={phone} onChangeText={setPhone} keyboardType="phone-pad" accessibilityLabel="Phone" />
          <TextInput style={styles.input} placeholder="staff@example.com" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
          <View style={styles.roleRow}>
            {roles.map((r) => (
              <TouchableOpacity key={r.id} style={[styles.roleChip, selectedRole === r.id && { borderColor: agencyTheme.primary, backgroundColor: agencyTheme.primaryBg }]} onPress={() => setSelectedRole(r.id)}>
                <Text style={[styles.roleChipText, selectedRole === r.id && { color: agencyTheme.primaryDark, fontWeight: '700' }]}>{r.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Button label="Add staff member" onPress={invite} loading={saving} color={agencyTheme.primary} fullWidth />
        </Card>
      )}

      <FlatList
        data={members}
        keyExtractor={(m) => m.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={agencyTheme.primary} />}
        renderItem={({ item: m }) => (
          <Card>
            <View style={styles.rowBetween}>
              <View style={[styles.avatar, { backgroundColor: agencyTheme.primaryLight }]}>
                <Text style={[styles.avatarText, { color: agencyTheme.primaryDark }]}>{(m.user_name || m.user_email)[0]?.toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.memberName}>{m.user_name || m.user_email}</Text>
                <Text style={styles.meta}>{m.role_name} · {m.user_email}</Text>
              </View>
              <StatusBadge status={m.status} />
            </View>
            <View style={styles.actionsRow}>
              {m.status === 'active' && m.role_name !== 'Agency Admin' && (
                <TouchableOpacity onPress={() => resetLogin(m)}><Text style={styles.suspendLink}>Reset login</Text></TouchableOpacity>
              )}
              {m.status === 'active' && (
                <TouchableOpacity onPress={() => suspend(m.id)}><Text style={styles.suspendLink}>Suspend</Text></TouchableOpacity>
              )}
              {m.status !== 'removed' && (
                <TouchableOpacity onPress={() => remove(m.id)}><Text style={styles.removeLink}>Remove</Text></TouchableOpacity>
              )}
            </View>
          </Card>
        )}
        ListEmptyComponent={!loading ? <EmptyState emoji="👥" message="No staff members yet." /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.lg, paddingBottom: 4 },
  formCard: { marginHorizontal: spacing.lg, marginBottom: spacing.sm },
  formHint: { fontSize: typography.xs, color: colors.gray400, marginBottom: spacing.sm },
  input: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: typography.sm, marginBottom: spacing.sm, color: colors.gray900 },
  roleRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: spacing.md },
  roleChip: { borderWidth: 1, borderColor: colors.gray200, borderRadius: radius.full, paddingHorizontal: 12, paddingVertical: 6 },
  roleChipText: { fontSize: typography.xs, color: colors.gray600 },
  rowBetween: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: typography.sm, fontWeight: '700' },
  memberName: { fontSize: typography.sm, fontWeight: '700', color: colors.gray900 },
  meta: { fontSize: typography.xs, color: colors.gray500, marginTop: 2 },
  actionsRow: { flexDirection: 'row', gap: 16, marginTop: spacing.sm, marginLeft: 46 },
  suspendLink: { fontSize: typography.xs, color: '#d97706', fontWeight: '600' },
  removeLink: { fontSize: typography.xs, color: colors.red600, fontWeight: '600' },
})
