import type { Directive } from 'vue'

/** v-spot — a soft highlight that follows the pointer across a card (sets --mx / --my). */
export const vSpot: Directive<HTMLElement> = {
  mounted(el) {
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect()
      el.style.setProperty('--mx', `${e.clientX - r.left}px`)
      el.style.setProperty('--my', `${e.clientY - r.top}px`)
    }
    el.addEventListener('pointermove', move, { passive: true })
    ;(el as any).__spot = move
  },
  unmounted(el) { el.removeEventListener('pointermove', (el as any).__spot) },
}
