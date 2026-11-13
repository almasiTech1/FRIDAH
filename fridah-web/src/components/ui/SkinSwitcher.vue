<template>
  <div ref="root" class="fx-pop-wrap">
    <button class="fx-icon-btn" title="Change look" aria-label="Change look" :aria-expanded="open" @click="open = !open"><Palette /></button>
    <div v-if="open" class="fx-pop" style="width:380px">
      <h4>Dashboard look</h4>
      <button v-for="s in SKINS" :key="s.id" class="fx-pop-item fx-skin-row" :class="{ on: skin.id === s.id }" @click="choose(s.id, s.name)">
        <span class="fx-swatch"><i v-for="c in s.swatch" :key="c" :style="`background:${c}`" /></span>
        <span class="min-w-0"><b class="block font-semibold">{{ s.name }}</b><small>{{ s.blurb }}</small></span>
        <span v-if="skin.id === s.id" class="fx-check">✓</span>
      </button>
      <h4>Wallpaper</h4>
      <div class="flex gap-2 p-2">
        <label class="fx-btn" style="height:38px;flex:1;justify-content:center;cursor:pointer"><ImagePlus /> Upload image
          <input type="file" accept="image/*" class="hidden" @change="onFile" />
        </label>
        <button v-if="skin.wallpaper" class="fx-btn" style="height:38px" @click="skin.setWallpaper(null)">Remove</button>
        <button v-if="skin.chosen" class="fx-btn" style="height:38px" title="Back to this portal's default look" @click="skin.resetToPortalDefault()"><RotateCcw /></button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { Palette, ImagePlus, RotateCcw } from 'lucide-vue-next'
import { SKINS, useSkinStore, type SkinId } from '@/stores/skin'
import { useToastStore } from '@/stores/toasts'
const skin = useSkinStore(); const toast = useToastStore()
const open = ref(false); const root = ref<HTMLElement>()
onClickOutside(root, () => (open.value = false))
function choose(id: SkinId, name: string) { skin.set(id); toast.push(`${name} applied`, { body: 'Your choice is remembered on this device.', tone: 'info' }) }
/** Downscale so the wallpaper fits in localStorage and stays crisp but light. */
function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (!f.type.startsWith('image/')) { toast.push('Pick an image file', { tone: 'warn' }); return }
  const img = new Image(); const url = URL.createObjectURL(f)
  img.onload = () => {
    const scale = Math.min(1, 1600 / img.width); const c = document.createElement('canvas')
    c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale)
    c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height)
    skin.setWallpaper(c.toDataURL('image/jpeg', 0.78)); URL.revokeObjectURL(url)
    toast.push('Wallpaper set', { body: 'Frosted glass now floats over your image.' })
  }
  img.onerror = () => { URL.revokeObjectURL(url); toast.push('Could not read that image', { tone: 'error' }) }
  img.src = url; (e.target as HTMLInputElement).value = ''
}
</script>
