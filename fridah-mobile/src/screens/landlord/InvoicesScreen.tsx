import React, { useState, useEffect } from 'react'
import { View, Text, FlatList, RefreshControl } from 'react-native'
import { rentalsApi } from '@/api/services'
import { Card, StatusBadge, EmptyState } from '@/components/common/Cards'
import { getTheme, colors, spacing, typography } from '@/theme'
import { formatKES, formatDate } from '@/utils/formatters'
import type { Invoice } from '@/types'

export const LandlordInvoicesScreen: React.FC = () => {
  const theme = getTheme('landlord')
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try { const { data } = await rentalsApi.invoices(); setInvoices(data.data?.results || []) }
    catch { setInvoices([]) } finally { setRefreshing(false) }
  }
  useEffect(() => { load() }, [])

  return (
    <View style={{flex:1,backgroundColor:colors.gray50}}>
      <FlatList data={invoices} keyExtractor={i=>i.id} contentContainerStyle={{padding:spacing.lg,gap:12}}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={()=>{setRefreshing(true);load()}} tintColor={theme.primary} />}
        ListEmptyComponent={<EmptyState emoji="🧾" message="No invoices yet" />}
        renderItem={({item}) => (
          <Card style={{padding:spacing.lg}}>
            <View style={{flexDirection:'row',justifyContent:'space-between',marginBottom:8}}>
              <Text style={{fontSize:typography.xs,fontFamily:'monospace',fontWeight:'700',color:colors.gray600}}>{item.invoice_number}</Text>
              <StatusBadge status={item.status} />
            </View>
            <Text style={{fontSize:typography.sm,fontWeight:'700',color:colors.gray900,marginBottom:4}}>{item.tenant_name}</Text>
            <View style={{flexDirection:'row',justifyContent:'space-between'}}>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Amount</Text><Text style={{fontWeight:'700',color:colors.gray900}}>{formatKES(item.amount)}</Text></View>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Balance</Text><Text style={{fontWeight:'700',color:item.balance>0?'#dc2626':'#16a34a'}}>{formatKES(item.balance)}</Text></View>
              <View><Text style={{fontSize:typography.xs,color:colors.gray400}}>Due</Text><Text style={{fontWeight:'700',color:colors.gray700}}>{formatDate(item.due_date)}</Text></View>
            </View>
          </Card>
        )}
      />
    </View>
  )
}
