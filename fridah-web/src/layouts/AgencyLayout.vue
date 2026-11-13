<template>
  <PortalLayout :gradient="['#0ea5e9','#0369a1']" portal-label="Agency Portal" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { Home, Building2, Users, FileText, Wallet, Receipt, MessageSquare, ClipboardList, User } from 'lucide-vue-next'
const nav = [
  { to: '/agency/dashboard',   label: 'Dashboard',   icon: Home },
  { to: '/agency/properties',  label: 'Properties',  icon: Building2 },
  { to: '/agency/staff',       label: 'Staff',       icon: Users },
  { to: '/agency/statements',  label: 'Statements',  icon: FileText },
  { to: '/agency/payouts',     label: 'Payouts',     icon: Wallet },
  { to: '/agency/expenses',    label: 'Expenses',    icon: Receipt },
  { to: '/agency/chat',        label: 'Chat',        icon: MessageSquare },
  { to: '/agency/audit-log',   label: 'Audit Log',   icon: ClipboardList },
  { to: '/agency/profile',     label: 'Profile',     icon: User },
]
</script>
