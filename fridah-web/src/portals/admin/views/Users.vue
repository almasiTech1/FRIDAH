<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="page-title">User Management</h1>
      <div class="flex gap-2">
        <input v-model="search" class="input text-sm w-48" placeholder="Search name, email…"/>
        <select v-model="roleFilter" class="input text-sm w-40">
          <option value="">All roles</option>
          <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
    </div>
    <div class="card overflow-x-auto">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading…</div>
      <table v-else-if="users.length" class="w-full">
        <thead class="bg-gray-50 border-b"><tr>
          <th class="table-th">User</th><th class="table-th">Phone</th><th class="table-th">Role</th>
          <th class="table-th">KYC</th><th class="table-th">Joined</th><th class="table-th">Status</th>
        </tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="table-tr">
            <td class="table-td">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-full bg-adminc-100 text-adminc-700 flex items-center justify-center text-xs font-medium">
                  {{ (u.first_name?.[0]||'') + (u.last_name?.[0]||'') || u.username[0].toUpperCase() }}
                </div>
                <div>
                  <p class="font-medium text-sm">{{ u.first_name }} {{ u.last_name }}</p>
                  <p class="text-xs text-gray-400">{{ u.email }}</p>
                </div>
              </div>
            </td>
            <td class="table-td text-xs font-mono">{{ u.phone_number }}</td>
            <td class="table-td"><span class="badge badge-blue capitalize">{{ u.role.replace('_',' ') }}</span></td>
            <td class="table-td"><span :class="kycBadge(u.kyc_status)" class="badge">{{ u.kyc_status }}</span></td>
            <td class="table-td text-xs">{{ formatDate(u.created_at) }}</td>
            <td class="table-td"><span class="badge badge-green">Active</span></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="p-10 text-center text-gray-400">No users found.</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { analyticsApi } from '@/api/services'
import { formatDate } from '@/utils/formatters'
import type { User } from '@/types'
const users = ref<User[]>([]); const loading = ref(true)
const search = ref(''); const roleFilter = ref('')
const roles = [{value:'tenant',label:'Tenant'},{value:'landlord',label:'Landlord'},{value:'admin',label:'Admin'},{value:'service_provider',label:'Service Provider'},{value:'hotel_owner',label:'Hotel Owner'}]
const kycBadge = (s: string) => ({ verified:'badge-green', pending:'badge-yellow', rejected:'badge-red', not_submitted:'badge-gray' }[s] || 'badge-gray')
async function load() {
  loading.value = true
  try { const { data } = await analyticsApi.users({ search: search.value, role: roleFilter.value || undefined }); users.value = data.data?.results || data.data || [] }
  catch { users.value = [] } finally { loading.value = false }
}
watch([search, roleFilter], load)
onMounted(load)
</script>
