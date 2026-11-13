<template>
  <PortalLayout :gradient="['#f97316','#c2410c']" portal-label="Service Provider" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { Home, Briefcase, ClipboardList, MessageSquare, Wallet, User } from 'lucide-vue-next'
const nav = [
  { to: '/provider/dashboard', label: 'Dashboard',  icon: Home },
  { to: '/provider/jobs',      label: 'Open Jobs',  icon: Briefcase },
  { to: '/provider/my-jobs',   label: 'My Jobs',    icon: ClipboardList },
  { to: '/provider/quotes',    label: 'My Quotes',  icon: MessageSquare },
  { to: '/provider/messages',  label: 'Messages',   icon: MessageSquare },
  { to: '/provider/wallet',    label: 'Wallet',     icon: Wallet },
  { to: '/provider/profile',   label: 'Profile',    icon: User },
]
</script>
