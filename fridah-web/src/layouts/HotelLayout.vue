<template>
  <PortalLayout :gradient="['#f59e0b','#b45309']" portal-label="Hotel / BnB" :nav-items="nav" />
</template>
<script setup lang="ts">
import PortalLayout from './PortalLayout.vue'
import { Home, Hotel, BedDouble, CalendarDays, CalendarRange, Wallet, User, MessageSquare, Receipt, Briefcase } from 'lucide-vue-next'
const nav = [
  { to: '/hotel/dashboard', label: 'Dashboard',  icon: Home },
  { to: '/hotel/listings',  label: 'Listings',   icon: Hotel },
  { to: '/hotel/managed',   label: 'Managed & Revenue', icon: Briefcase },
  { to: '/hotel/rooms',     label: 'Room Types', icon: BedDouble },
  { to: '/hotel/calendar',  label: 'Calendar',   icon: CalendarRange },
  { to: '/hotel/bookings',  label: 'Bookings',   icon: CalendarDays },
  { to: '/hotel/statements', label: 'Statements', icon: Receipt },
  { to: '/hotel/messages',  label: 'Messages',   icon: MessageSquare },
  { to: '/hotel/wallet',    label: 'Wallet',     icon: Wallet },
  { to: '/hotel/profile',   label: 'Profile',    icon: User },
]
</script>
