import React, { useState, useEffect } from 'react'
import { View, Text, ScrollView, TextInput, Alert, StyleSheet } from 'react-native'
import { paymentsApi } from '@/api/services'
import { Card } from '@/components/common/Cards'
import { Button } from '@/components/common/Button'
import { getTheme, colors, spacing, typography, radius } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'

export const LandlordWalletScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [balance, setBalance] = useState(0)
  const [transactions, setTransactions] = useState<any[]>([])
  const [amount, setAmount] = useState('')
  const [phone, setPhone] = useState('+254')
  const [withdrawing, setWithdrawing] = useState(false)

  useEffect(() => {
    paymentsApi.wallet().then(({ data }) => { setBalance(data.data.balance); setTransactions(data.data.recent_transactions || []) }).catch(() => setBalance(320000))
  }, [])

  const withdraw = async () => {
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) { Alert.alert('Error','Enter a valid amount'); return }
    if (amt > balance) { Alert.alert('Error','Insufficient balance'); return }
    setWithdrawing(true)
    try { await paymentsApi.requestPayout(amt, phone); Alert.alert('Success','Payout initiated! Check your M-Pesa shortly.'); setAmount('') }
    catch (e:any) { Alert.alert('Error', e?.response?.data?.error?.message||'Failed') }
    finally { setWithdrawing(false) }
  }

  return (
    <ScrollView style={{flex:1,backgroundColor:colors.gray50}} contentContainerStyle={{padding:spacing.lg,gap:14}}>
      <View style={[styles.balCard, {backgroundColor:theme.primary}]}>
        <Text style={styles.balLabel}>Available Balance</Text>
        <Text style={styles.balAmount}>{formatKES(balance)}</Text>
        <Text style={styles.balSub}>After platform commission</Text>
      </View>
      <Card style={{padding:spacing.lg}}>
        <Text style={{fontSize:typography.base,fontWeight:'700',color:colors.gray900,marginBottom:14}}>Withdraw to M-Pesa</Text>
        <Text style={styles.label}>Amount (KES)</Text>
        <TextInput style={styles.input} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="Enter amount" placeholderTextColor={colors.gray400} />
        <Text style={styles.label}>M-Pesa Number</Text>
        <TextInput style={styles.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholderTextColor={colors.gray400} />
        <Button label={`Withdraw ${amount ? formatKES(parseFloat(amount)||0) : ''}`} onPress={withdraw} loading={withdrawing} color={theme.primary} fullWidth />
      </Card>
      {transactions.length > 0 && (
        <Card style={{padding:spacing.lg}}>
          <Text style={{fontSize:typography.base,fontWeight:'700',color:colors.gray900,marginBottom:14}}>Recent Transactions</Text>
          {transactions.map(tx => (
            <View key={tx.id} style={styles.txRow}>
              <View style={[styles.txDot, {backgroundColor: tx.entry_type==='credit'?'#dcfce7':'#fee2e2'}]}>
                <Text style={{fontSize:14}}>{tx.entry_type==='credit'?'+':'−'}</Text>
              </View>
              <View style={{flex:1}}>
                <Text style={{fontSize:typography.xs,color:colors.gray700,fontWeight:'500'}}>{tx.description}</Text>
                <Text style={{fontSize:typography.xs,color:colors.gray400}}>{formatDate(tx.created_at)}</Text>
              </View>
              <Text style={{fontWeight:'700',fontSize:typography.sm,color:tx.entry_type==='credit'?'#16a34a':'#dc2626'}}>{formatKES(tx.amount)}</Text>
            </View>
          ))}
        </Card>
      )}
    </ScrollView>
  )
}
const styles = StyleSheet.create({
  balCard:{borderRadius:radius.xl,padding:spacing.xl},
  balLabel:{color:'rgba(255,255,255,0.7)',fontSize:typography.sm,fontWeight:'500'},
  balAmount:{color:colors.white,fontSize:36,fontWeight:'900',marginTop:4},
  balSub:{color:'rgba(255,255,255,0.5)',fontSize:typography.xs,marginTop:4},
  label:{fontSize:typography.xs,fontWeight:'600',color:colors.gray600,marginBottom:6},
  input:{borderWidth:1.5,borderColor:colors.gray200,borderRadius:radius.md,paddingHorizontal:14,paddingVertical:11,fontSize:typography.sm,color:colors.gray900,marginBottom:14},
  txRow:{flexDirection:'row',alignItems:'center',gap:10,paddingVertical:10,borderBottomWidth:1,borderBottomColor:colors.gray50},
  txDot:{width:36,height:36,borderRadius:18,alignItems:'center',justifyContent:'center',flexShrink:0},
})
