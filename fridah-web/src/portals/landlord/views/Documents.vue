<template>
  <div class="space-y-5">
    <div class="page-header"><h1 class="page-title">{{ $t('nav.documents') }}</h1></div>

    <div class="card card-body">
      <label class="label">Property</label>
      <select v-model="selectedPropertyId" class="input" @change="load">
        <option value="">Choose a property…</option>
        <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
    </div>

    <template v-if="selectedPropertyId">
      <div class="card card-body space-y-3">
        <h2 class="section-title">Upload document</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Document type</label>
            <select v-model="uploadForm.document_type" class="input">
              <option value="title_deed">Title Deed</option>
              <option value="occupation_certificate">Occupation Certificate</option>
              <option value="compliance_certificate">Compliance Certificate</option>
              <option value="fire_safety_certificate">Fire Safety Certificate</option>
              <option value="land_rates_receipt">Land Rates Receipt</option>
              <option value="insurance_policy">Insurance Policy</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div><label class="label">Title</label><input v-model="uploadForm.title" class="input" placeholder="e.g. Title Deed - Kilimani Apartments"/></div>
          <div><label class="label">Expiry date (optional)</label><input v-model="uploadForm.expiry_date" type="date" class="input"/></div>
          <div><label class="label">File</label><input type="file" class="input" @change="onFileChange"/></div>
        </div>
        <button class="btn-primary bg-landlord-600 hover:bg-landlord-700" :disabled="uploading || !uploadForm.file" @click="upload">
          <span v-if="uploading" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"/>
          <span v-else>Upload</span>
        </button>
      </div>

      <div class="card overflow-x-auto">
        <div v-if="loading" class="p-8 text-center text-gray-400 dark:text-gray-500">{{ $t('common.loading') }}</div>
        <table v-else-if="documents.length" class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-800/50 border-b dark:border-gray-800"><tr>
            <th class="table-th">Type</th><th class="table-th">Title</th><th class="table-th">Version</th>
            <th class="table-th">Expiry</th><th class="table-th">Uploaded</th><th class="table-th"></th>
          </tr></thead>
          <tbody>
            <tr v-for="d in documents" :key="d.id" class="table-tr">
              <td class="table-td">{{ d.document_type_display }}</td>
              <td class="table-td font-medium">{{ d.title }}</td>
              <td class="table-td">v{{ d.version }}</td>
              <td class="table-td">{{ d.expiry_date ? formatDate(d.expiry_date) : '—' }}</td>
              <td class="table-td text-xs">{{ formatDate(d.created_at) }} by {{ d.uploaded_by_name }}</td>
              <td class="table-td"><a :href="d.file" target="_blank" class="text-landlord-600 dark:text-landlord-400 font-medium text-xs hover:underline">Download</a></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="p-10 text-center text-gray-400 dark:text-gray-500">No documents uploaded yet for this property.</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { propertiesApi, documentsApi } from '@/api/services'
import { formatDate } from '@/utils/formatters'

const properties = ref<{ id: string; name: string }[]>([])
const selectedPropertyId = ref('')
const documents = ref<any[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadForm = ref<{ document_type: string; title: string; expiry_date: string; file: File | null }>({
  document_type: 'title_deed', title: '', expiry_date: '', file: null,
})

function onFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  uploadForm.value.file = files?.[0] || null
}

async function loadProperties() {
  const { data } = await propertiesApi.list()
  properties.value = data.data?.results || data.data || []
}

async function load() {
  if (!selectedPropertyId.value) return
  loading.value = true
  try {
    const { data } = await documentsApi.list(selectedPropertyId.value)
    documents.value = data.data?.results || data.data || []
  } finally { loading.value = false }
}

async function upload() {
  if (!uploadForm.value.file) return
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('document_type', uploadForm.value.document_type)
    formData.append('title', uploadForm.value.title || uploadForm.value.file.name)
    if (uploadForm.value.expiry_date) formData.append('expiry_date', uploadForm.value.expiry_date)
    formData.append('file', uploadForm.value.file)
    await documentsApi.upload(selectedPropertyId.value, formData)
    uploadForm.value = { document_type: 'title_deed', title: '', expiry_date: '', file: null }
    await load()
  } finally { uploading.value = false }
}

onMounted(loadProperties)
</script>
