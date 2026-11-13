<template>
  <PortalLayout :gradient="['#8b5cf6','#6d28d9']" portal-label="Admin Portal" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { LayoutDashboard, Users, ShieldCheck, Building2, Hotel, CreditCard, BarChart2, ReceiptText, ShieldAlert, Briefcase , Undo2, Scale, User } from 'lucide-vue-next'
const nav = [
  { to: '/admin/dashboard',  label: 'Dashboard',      icon: LayoutDashboard },
  { to: '/admin/users',      label: 'Users',          icon: Users },
  { to: '/admin/kyc',        label: 'KYC Review',     icon: ShieldCheck },
  { to: '/admin/properties', label: 'Properties',     icon: Building2 },
  { to: '/admin/agencies',   label: 'Agencies',       icon: Briefcase },
  { to: '/admin/refunds',    label: 'Refunds',        icon: Undo2 },
  { to: '/admin/profile',    label: 'My Account',     icon: User },
  { to: '/admin/reconciliation', label: 'Reconciliation', icon: Scale },
  { to: '/admin/review-queue', label: 'Review Queue', icon: ShieldCheck },
  { to: '/admin/portfolio',  label: 'Portfolio',      icon: BarChart2 },
  { to: '/admin/tax-settings', label: 'Tax Settings', icon: ReceiptText },
  { to: '/admin/listings',   label: 'Hotel Listings', icon: Hotel },
  { to: '/admin/payments',   label: 'Payments',       icon: CreditCard },
  { to: '/admin/paybill',    label: 'Paybill Recon.', icon: ReceiptText },
  { to: '/admin/blacklist',  label: 'Blacklist',      icon: ShieldAlert },
  { to: '/admin/analytics',  label: 'Analytics',      icon: BarChart2 },
]
</script>
