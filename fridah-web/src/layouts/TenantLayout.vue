<template>
  <PortalLayout :gradient="['#10b981','#059669']" portal-label="Tenant Portal"
    notif-route="/tenant/notifications" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { Home, FileText, CreditCard, Wrench, Building2, Bell, User, MessageSquare, ClipboardList , Undo2 } from 'lucide-vue-next'
const nav = [
  { to: '/tenant/dashboard',     label: 'Dashboard',     icon: Home },
  { to: '/tenant/lease',         label: 'My Lease',      icon: FileText },
  { to: '/tenant/invoices',      label: 'Invoices',      icon: FileText },
  { to: '/tenant/payments',      label: 'Payments',      icon: CreditCard },
  { to: '/tenant/refunds',       label: 'My Refunds',    icon: Undo2 },
  { to: '/tenant/maintenance',   label: 'Maintenance',   icon: Wrench },
  { to: '/tenant/messages',      label: 'Messages',      icon: MessageSquare },
  { to: '/tenant/properties',    label: 'Browse Homes',  icon: Building2 },
  { to: '/tenant/applications',  label: 'My Applications', icon: ClipboardList },
  { to: '/tenant/notifications', label: 'Notifications', icon: Bell },
  { to: '/tenant/profile',       label: 'Profile & KYC', icon: User },
]
</script>
