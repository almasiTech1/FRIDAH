import React, { useState, useRef, useEffect } from 'react'
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Animated, Easing,
} from 'react-native'
import { paymentsApi } from '@/api/services'
import { formatKES } from '@/utils/formatters'
import { colors, radius, typography, spacing } from '@/theme'

interface Props {
  visible: boolean
  amount: number
  invoiceId?: string
  bookingId?: string
  description?: string
  accentColor?: string
  onClose: () => void
  onSuccess: () => void
}

type State = 'idle' | 'processing' | 'success' | 'failed'

export const MpesaPayModal: React.FC<Props> = ({
  visible, amount, invoiceId, bookingId,
  description = 'FRIDAH Payment',
  accentColor = '#10b981',
  onClose, onSuccess,
}) => {
  const [phone, setPhone] = useState('+254')
  const [state, setState] = useState<State>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [paymentId, setPaymentId] = useState('')
  const spinAnim = useRef(new Animated.Value(0)).current
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const scaleAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (!visible) { setState('idle'); setPhone('+254'); setErrorMsg('') }
  }, [visible])

  useEffect(() => {
    if (state === 'processing') {
      Animated.loop(
        Animated.timing(spinAnim, {
          toValue: 1, duration: 1000, easing: Easing.linear, useNativeDriver: true,
        }),
      ).start()
    } else {
      spinAnim.stopAnimation()
    }
    if (state === 'success') {
      Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true }).start()
    } else {
      scaleAnim.setValue(0)
    }
  }, [state])

  const spin = spinAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })

  const initiate = async () => {
    if (!phone || phone.length < 12) { setErrorMsg('Enter a valid phone number.'); return }
    setState('processing'); setErrorMsg('')
    try {
      const { data } = await paymentsApi.stkPush({
        phone_number: phone, amount,
        invoice_id: invoiceId, booking_id: bookingId, description,
      })
      setPaymentId(data.data.payment.id)
      startPolling(data.data.payment.id)
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Failed to initiate payment.')
      setState('failed')
    }
  }

  const startPolling = (pid: string) => {
    let attempts = 0
    pollRef.current = setInterval(async () => {
      attempts++
      if (attempts > 12) {
        clearPolling()
        setState('failed')
        setErrorMsg('Payment timed out. Please try again.')
        return
      }
      try {
        const { data } = await paymentsApi.stkStatus(pid)
        const s = data.data.status
        if (s === 'completed') { clearPolling(); setState('success') }
        else if (s === 'failed' || s === 'cancelled') {
          clearPolling(); setState('failed')
          setErrorMsg(data.data.failure_reason || 'Payment failed or was cancelled.')
        }
      } catch {}
    }, 5000)
  }

  const clearPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const handleSuccess = () => { clearPolling(); onSuccess(); onClose() }

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Pay with M-Pesa</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeX}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Amount */}
          <View style={[styles.amountBox, { backgroundColor: accentColor + '15' }]}>
            <Text style={[styles.amountLabel, { color: accentColor }]}>Amount</Text>
            <Text style={[styles.amount, { color: accentColor }]}>{formatKES(amount)}</Text>
          </View>

          {/* Idle state */}
          {(state === 'idle' || state === 'failed') && (
            <View style={styles.form}>
              <Text style={styles.inputLabel}>M-Pesa Phone Number</Text>
              <TextInput
                style={styles.input}
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
                placeholder="+254712345678"
                placeholderTextColor={colors.gray400}
              />
              {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}
              <View style={styles.btnRow}>
                <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
                  <Text style={styles.cancelText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.payBtn, { backgroundColor: accentColor }]}
                  onPress={initiate}
                >
                  <Text style={styles.payText}>Send STK Push</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* Processing state */}
          {state === 'processing' && (
            <View style={styles.stateCenter}>
              <Animated.View style={{ transform: [{ rotate: spin }] }}>
                <View style={[styles.spinCircle, { borderTopColor: accentColor }]} />
              </Animated.View>
              <Text style={styles.stateTitle}>Waiting for payment…</Text>
              <Text style={styles.stateSub}>
                Check your phone for the M-Pesa PIN prompt and enter your PIN to confirm.
              </Text>
              <TouchableOpacity onPress={() => { clearPolling(); setState('idle') }}>
                <Text style={[styles.cancelLink, { color: accentColor }]}>Cancel</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Success state */}
          {state === 'success' && (
            <View style={styles.stateCenter}>
              <Animated.View style={[styles.successCircle, { transform: [{ scale: scaleAnim }] }]}>
                <Text style={styles.successTick}>✓</Text>
              </Animated.View>
              <Text style={styles.stateTitle}>Payment Successful!</Text>
              <Text style={styles.stateSub}>{formatKES(amount)} received.</Text>
              <TouchableOpacity
                style={[styles.payBtn, { backgroundColor: accentColor, alignSelf: 'center', marginTop: 16 }]}
                onPress={handleSuccess}
              >
                <Text style={styles.payText}>Done</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: spacing.xl, paddingBottom: 36,
  },
  header: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', marginBottom: spacing.lg,
  },
  title: { fontSize: typography.xl, fontWeight: '700', color: colors.gray900 },
  closeBtn: { padding: 4 },
  closeX: { fontSize: 18, color: colors.gray500 },
  amountBox: {
    padding: spacing.md, borderRadius: radius.md, marginBottom: spacing.xl,
  },
  amountLabel: { fontSize: typography.sm, fontWeight: '500', marginBottom: 2 },
  amount: { fontSize: typography.xxxl, fontWeight: '800' },
  form: {},
  inputLabel: { fontSize: typography.sm, fontWeight: '500', color: colors.gray700, marginBottom: 6 },
  input: {
    borderWidth: 1.5, borderColor: colors.gray200,
    borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 12,
    fontSize: typography.base, color: colors.gray900, marginBottom: 8,
  },
  errorText: { fontSize: typography.sm, color: colors.red500, marginBottom: 8 },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 8 },
  cancelBtn: {
    flex: 1, paddingVertical: 13, borderRadius: radius.lg,
    borderWidth: 1.5, borderColor: colors.gray200, alignItems: 'center',
  },
  cancelText: { fontSize: typography.base, fontWeight: '600', color: colors.gray600 },
  payBtn: {
    flex: 1, paddingVertical: 13, borderRadius: radius.lg, alignItems: 'center',
  },
  payText: { fontSize: typography.base, fontWeight: '600', color: colors.white },
  stateCenter: { alignItems: 'center', paddingVertical: 24, gap: 12 },
  spinCircle: {
    width: 48, height: 48, borderRadius: 24,
    borderWidth: 4, borderColor: colors.gray100,
  },
  stateTitle: { fontSize: typography.lg, fontWeight: '700', color: colors.gray900 },
  stateSub: {
    fontSize: typography.sm, color: colors.gray500,
    textAlign: 'center', paddingHorizontal: 20,
  },
  cancelLink: { fontSize: typography.sm, fontWeight: '500', marginTop: 8 },
  successCircle: {
    width: 64, height: 64, borderRadius: 32,
    backgroundColor: '#dcfce7', alignItems: 'center', justifyContent: 'center',
  },
  successTick: { fontSize: 32, color: '#16a34a' },
})
