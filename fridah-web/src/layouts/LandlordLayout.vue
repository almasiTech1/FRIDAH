<template>
  <PortalLayout :gradient="['#6366f1','#4338ca']" portal-label="Landlord Portal" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { Home, Building2, DoorOpen, FileText, Wrench, BarChart2, Wallet, User, RefreshCw, ShieldAlert, FolderLock, Sparkles, MessageSquare, ClipboardList, Receipt, Briefcase , Undo2 } from 'lucide-vue-next'
const nav = [
  { to: '/landlord/dashboard',   label: 'Dashboard',   icon: Home },
  { to: '/landlord/properties',  label: 'Properties',  icon: Building2 },
  { to: '/landlord/managed',     label: 'Managed & Revenue', icon: Briefcase },
  { to: '/landlord/units',       label: 'Units',       icon: DoorOpen },
  { to: '/landlord/leases',      label: 'Leases',      icon: FileText },
  { to: '/landlord/applications', label: 'Applications', icon: ClipboardList },
  { to: '/landlord/renewals',    label: 'Renewals',    icon: RefreshCw },
  { to: '/landlord/invoices',    label: 'Invoices',    icon: FileText },
  { to: '/landlord/statements',  label: 'Statements',  icon: Receipt },
  { to: '/landlord/approvals',   label: 'Approvals',   icon: ClipboardList },
  { to: '/landlord/refunds',     label: 'Refunds',     icon: Undo2 },
  { to: '/landlord/tax',         label: 'Tax',         icon: FileText },
  { to: '/landlord/amenities',   label: 'Amenities',   icon: Sparkles },
  { to: '/landlord/maintenance', label: 'Maintenance', icon: Wrench },
  { to: '/landlord/messages',    label: 'Messages',    icon: MessageSquare },
  { to: '/landlord/screening',   label: 'Screening',   icon: ShieldAlert },
  { to: '/landlord/documents',   label: 'Documents',   icon: FolderLock },
  { to: '/landlord/rent-estimator', label: 'Rent Estimator', icon: Sparkles },
  { to: '/landlord/analytics',   label: 'Analytics',   icon: BarChart2 },
  { to: '/landlord/wallet',      label: 'Wallet',       icon: Wallet },
  { to: '/landlord/profile',     label: 'Profile',     icon: User },
]
</script>
