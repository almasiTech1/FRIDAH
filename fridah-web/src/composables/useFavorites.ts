import { computed, ref } from 'vue'

/** Saved properties / listings, kept on this device. */
export function useFavorites(kind: 'property' | 'listing') {
  const key = `fridah-saved-${kind}`
  const read = (): string[] => { try { return JSON.parse(localStorage.getItem(key) || '[]') } catch { return [] } }
  const ids = ref<string[]>(read())
  const has = (id: string) => ids.value.includes(id)
  function toggle(id: string) {
    ids.value = has(id) ? ids.value.filter((x) => x !== id) : [...ids.value, id]
    try { localStorage.setItem(key, JSON.stringify(ids.value)) } catch { /* private mode: keep for this session */ }
    return has(id)
  }
  return { ids, count: computed(() => ids.value.length), has, toggle }
}
