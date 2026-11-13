import React, { useState } from 'react'
import { View, Text, TextInput, StyleSheet, Alert } from 'react-native'
import { launchImageLibrary, launchCamera } from 'react-native-image-picker'
import { pick } from '@react-native-documents/picker'
import { useAuthStore } from '@/stores/authStore'
import { analyticsApi } from '@/api/services'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Cards'
import { colors, spacing, typography, radius } from '@/theme'

const KYC_INFO = {
  verified: { icon: '✅', title: 'KYC Verified', sub: 'Your identity has been verified.', bg: '#f0fdf4', border: '#bbf7d0', color: '#15803d' },
  pending: { icon: '🕐', title: 'Under Review', sub: 'We are reviewing your documents. This usually takes 1-2 business days.', bg: '#fffbeb', border: '#fde68a', color: '#b45309' },
  rejected: { icon: '❌', title: 'KYC Rejected', sub: '', bg: '#fef2f2', border: '#fecaca', color: '#dc2626' },
  not_submitted: { icon: '🔒', title: 'Verify Your Identity', sub: 'Upload your National ID to unlock all features.', bg: '#eff6ff', border: '#bfdbfe', color: '#1d4ed8' },
} as const

interface Props {
  accentColor: string
}

export const KYCSubmissionCard: React.FC<Props> = ({ accentColor }) => {
  const { user, fetchMe } = useAuthStore()
  const status = (user?.kyc_status || 'not_submitted') as keyof typeof KYC_INFO
  const info = KYC_INFO[status]

  const [nationalId, setNationalId] = useState(user?.national_id || '')
  const [document, setDocument] = useState<{ uri: string; name: string; type: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = status === 'not_submitted' || status === 'rejected'

  const pickFromGallery = () => {
    launchImageLibrary({ mediaType: 'photo', quality: 0.8 }, (response) => {
      const asset = response.assets?.[0]
      if (asset?.uri) setDocument({ uri: asset.uri, name: asset.fileName || `id-${Date.now()}.jpg`, type: asset.type || 'image/jpeg' })
    })
  }

  const pickFromCamera = () => {
    launchCamera({ mediaType: 'photo', quality: 0.8 }, (response) => {
      const asset = response.assets?.[0]
      if (asset?.uri) setDocument({ uri: asset.uri, name: asset.fileName || `id-${Date.now()}.jpg`, type: asset.type || 'image/jpeg' })
    })
  }

  const pickFile = async () => {
    try {
      const [result] = await pick({ type: ['application/pdf', 'image/*'] })
      setDocument({ uri: result.uri, name: result.name || `id-${Date.now()}`, type: result.type || 'application/octet-stream' })
    } catch {
      // user cancelled the picker - nothing to do
    }
  }

  const chooseDocument = () => {
    Alert.alert('Upload ID Document', 'Choose how to add your National ID', [
      { text: 'Take Photo', onPress: pickFromCamera },
      { text: 'Choose from Gallery', onPress: pickFromGallery },
      { text: 'Choose PDF/File', onPress: pickFile },
      { text: 'Cancel', style: 'cancel' },
    ])
  }

  const submit = async () => {
    if (!nationalId.trim()) {
      Alert.alert('National ID required', 'Please enter your National ID number.')
      return
    }
    if (!document) {
      Alert.alert('Document required', 'Please attach a photo or PDF of your National ID.')
      return
    }
    setSubmitting(true)
    try {
      await analyticsApi.submitKyc(nationalId.trim(), document)
      await fetchMe()
      setDocument(null)
      Alert.alert('Submitted', 'Your KYC documents have been submitted for review.')
    } catch (e: any) {
      const message = e?.response?.data?.error?.details?.kyc_document?.[0]
        || e?.response?.data?.error?.message
        || 'Failed to submit KYC documents. Please try again.'
      Alert.alert('Submission failed', message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View>
      <View style={[styles.banner, { backgroundColor: info.bg, borderColor: info.border }]}>
        <Text style={styles.icon}>{info.icon}</Text>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: info.color }]}>{info.title}</Text>
          <Text style={[styles.sub, { color: info.color + '99' }]}>
            {status === 'rejected' && user?.kyc_rejection_reason
              ? `Reason: ${user.kyc_rejection_reason}`
              : info.sub}
          </Text>
        </View>
      </View>

      {canSubmit && (
        <Card style={styles.formCard}>
          <Text style={styles.label}>National ID Number</Text>
          <TextInput
            style={styles.input}
            value={nationalId}
            onChangeText={setNationalId}
            placeholder="e.g. 12345678"
            placeholderTextColor={colors.gray400}
            keyboardType="number-pad"
          />
          <Button
            label={document ? `✓ ${document.name}` : '📎 Attach ID Document'}
            onPress={chooseDocument}
            variant="outline"
            color={accentColor}
            fullWidth
            style={{ marginBottom: 12 }}
          />
          <Button
            label={status === 'rejected' ? 'Resubmit for Review' : 'Submit for Review'}
            onPress={submit}
            loading={submitting}
            color={accentColor}
            fullWidth
          />
        </Card>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  banner: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: spacing.md, borderRadius: radius.xl, borderWidth: 1.5 },
  icon: { fontSize: 24 },
  title: { fontSize: typography.sm, fontWeight: '700' },
  sub: { fontSize: typography.xs, marginTop: 2 },
  formCard: { padding: spacing.lg, marginTop: 12 },
  label: { fontSize: typography.xs, fontWeight: '600', color: colors.gray600, marginBottom: 6 },
  input: { borderWidth: 1.5, borderColor: colors.gray200, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 11, fontSize: typography.sm, color: colors.gray900, backgroundColor: colors.white, marginBottom: 14 },
})
