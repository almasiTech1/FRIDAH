import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { defineComponent, ref } from 'vue'
import { useRowSearch } from '@/composables/useRowSearch'
import TableToolbar from '@/components/ui/TableToolbar.vue'

const Demo = defineComponent({
  components: { TableToolbar },
  setup() {
    const data = ref([{ id: 1, tenant: 'Wanjiru Kamau', status: 'paid' }, { id: 2, tenant: 'Brian Otieno', status: 'overdue' }, { id: 3, tenant: 'Amina Hassan', status: 'paid' }])
    return { ...useRowSearch(() => data.value, 'demo'), total: data.value.length }
  },
  template: `<div><TableToolbar v-model="q" :count="rows.length" :total="total" @export="exportCsv" /><p v-for="r in rows" :key="r.id" class="row">{{ r.tenant }}</p></div>`,
})

describe('list-page search', () => {
  it('filters rows across every field and reports the count', async () => {
    const w = mount(Demo, { global: { plugins: [createPinia()] } })
    expect(w.findAll('.row')).toHaveLength(3)
    await w.find('input').setValue('overdue')
    expect(w.findAll('.row')).toHaveLength(1)
    expect(w.text()).toContain('1 of 3 row')
    await w.find('input').setValue('AMINA')
    expect(w.find('.row').text()).toBe('Amina Hassan')
  })
  it('disables export when nothing matches', async () => {
    const w = mount(Demo, { global: { plugins: [createPinia()] } })
    await w.find('input').setValue('zzz')
    expect(w.find('button').attributes('disabled')).toBeDefined()
  })
})
