import type { Directive } from 'vue'

/**
 * v-reveal="'up'" | 'down' | 'left' | 'right' | 'zoom' | 'fade'
 * Adds the base hidden state immediately, then swaps to the visible/animated state
 * once the element scrolls into view. Cheap (single shared IntersectionObserver),
 * no animation library dependency.
 */
const hiddenClasses: Record<string, string[]> = {
  up:    ['opacity-0', 'translate-y-8'],
  down:  ['opacity-0', '-translate-y-8'],
  left:  ['opacity-0', 'translate-x-8'],
  right: ['opacity-0', '-translate-x-8'],
  zoom:  ['opacity-0', 'scale-95'],
  fade:  ['opacity-0'],
}

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const el = entry.target as HTMLElement
        const mode = el.dataset.revealMode || 'up'
        el.classList.remove(...(hiddenClasses[mode] || hiddenClasses.up))
        el.classList.add('opacity-100', 'translate-y-0', 'translate-x-0', 'scale-100')
        observer.unobserve(el)
      }
    }
  },
  { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
)

export const vReveal: Directive<HTMLElement, string | undefined> = {
  mounted(el, binding) {
    const mode = binding.value || 'up'
    el.dataset.revealMode = mode
    el.classList.add('transition-all', 'duration-700', 'ease-out', 'will-change-transform')
    el.classList.add(...(hiddenClasses[mode] || hiddenClasses.up))
    observer.observe(el)
  },
  unmounted(el) {
    observer.unobserve(el)
  },
}
