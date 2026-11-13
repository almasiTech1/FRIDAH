<template>
  <footer class="bg-gray-900 dark:bg-black text-gray-300">
    <div class="max-w-7xl mx-auto px-6 py-16">
      <div class="grid grid-cols-2 md:grid-cols-6 gap-10">
        <div class="col-span-2">
          <RouterLink to="/" class="flex items-center gap-2 mb-4">
            <div class="w-9 h-9 rounded-xl bg-white flex items-center justify-center">
              <span class="text-gray-900 font-bold text-sm">F</span>
            </div>
            <span class="font-bold text-lg text-white">FRIDAH</span>
          </RouterLink>
          <p class="text-sm text-gray-400 leading-relaxed mb-5 max-w-xs">
            Manage properties, hotels, rentals, and services from one smart, secure, Kenya-built platform.
          </p>
          <div class="flex gap-3">
            <a v-for="s in socials" :key="s.label" :href="s.href" target="_blank" rel="noopener" class="social-icon" :aria-label="s.label">
              <span v-html="s.svg" />
            </a>
          </div>
        </div>

        <div>
          <h4 class="footer-heading">Company</h4>
          <RouterLink to="/" class="footer-link">Home</RouterLink>
          <RouterLink to="/about" class="footer-link">About</RouterLink>
          <RouterLink to="/services" class="footer-link">Services</RouterLink>
          <RouterLink to="/pricing" class="footer-link">Pricing</RouterLink>
          <RouterLink to="/blog" class="footer-link">Blog</RouterLink>
        </div>

        <div>
          <h4 class="footer-heading">Resources</h4>
          <RouterLink to="/help" class="footer-link">Help Center</RouterLink>
          <RouterLink to="/properties" class="footer-link">Properties</RouterLink>
          <RouterLink to="/hotels" class="footer-link">Hotels</RouterLink>
          <RouterLink to="/marketplace" class="footer-link">Marketplace</RouterLink>
          <RouterLink to="/careers" class="footer-link">Careers</RouterLink>
        </div>

        <div>
          <h4 class="footer-heading">Legal</h4>
          <RouterLink to="/privacy" class="footer-link">Privacy Policy</RouterLink>
          <RouterLink to="/terms" class="footer-link">Terms of Service</RouterLink>
        </div>

        <div>
          <h4 class="footer-heading">Support</h4>
          <RouterLink to="/contact" class="footer-link">Contact Us</RouterLink>
          <a href="https://wa.me/254700000000" target="_blank" rel="noopener" class="footer-link">WhatsApp</a>
          <a href="mailto:support@fridah.co.ke" class="footer-link">support@fridah.co.ke</a>
          <a href="tel:+254700000000" class="footer-link">+254 700 000 000</a>
        </div>
      </div>

      <div class="mt-14 pt-10 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="max-w-sm">
          <h4 class="font-semibold text-white mb-2 text-sm">Stay updated</h4>
          <NewsletterSignup />
        </div>
      </div>

      <div class="mt-10 pt-8 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-500">
        <p>&copy; {{ year }} FRIDAH. All rights reserved.</p>
        <p>Built for the Kenyan market. Made with care in Nairobi.</p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import NewsletterSignup from './NewsletterSignup.vue'

const year = new Date().getFullYear()

const socials = [
  { label: 'Facebook', href: 'https://facebook.com', svg: '<svg viewBox="0 0 24 24" class="w-4 h-4 fill-current"><path d="M22 12a10 10 0 10-11.5 9.9v-7H8v-2.9h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.4h-1.2c-1.2 0-1.6.8-1.6 1.6v1.9H16l-.4 2.9h-2.1v7A10 10 0 0022 12z"/></svg>' },
  { label: 'Instagram', href: 'https://instagram.com', svg: '<svg viewBox="0 0 24 24" class="w-4 h-4 fill-current"><path d="M12 2c2.7 0 3.05.01 4.12.06 1.06.05 1.79.22 2.43.47.66.26 1.21.6 1.76 1.15.55.55.9 1.1 1.15 1.76.25.64.42 1.37.47 2.43.05 1.07.06 1.42.06 4.12s-.01 3.05-.06 4.12c-.05 1.06-.22 1.79-.47 2.43-.26.66-.6 1.21-1.15 1.76-.55.55-1.1.9-1.76 1.15-.64.25-1.37.42-2.43.47-1.07.05-1.42.06-4.12.06s-3.05-.01-4.12-.06c-1.06-.05-1.79-.22-2.43-.47-.66-.26-1.21-.6-1.76-1.15-.55-.55-.9-1.1-1.15-1.76-.25-.64-.42-1.37-.47-2.43C2.01 15.05 2 14.7 2 12s.01-3.05.06-4.12c.05-1.06.22-1.79.47-2.43.26-.66.6-1.21 1.15-1.76.55-.55 1.1-.9 1.76-1.15.64-.25 1.37-.42 2.43-.47C8.95 2.01 9.3 2 12 2zm0 5a5 5 0 100 10 5 5 0 000-10zm0 8.2a3.2 3.2 0 110-6.4 3.2 3.2 0 010 6.4zm5.4-8.4a1.2 1.2 0 100-2.4 1.2 1.2 0 000 2.4z"/></svg>' },
  { label: 'X', href: 'https://x.com', svg: '<svg viewBox="0 0 24 24" class="w-4 h-4 fill-current"><path d="M18.9 2H22l-7.2 8.2L23 22h-6.6l-5.2-6.8L5.2 22H2l7.7-8.8L1.5 2h6.8l4.7 6.2L18.9 2zm-1.2 18h1.8L7.4 4H5.5l12.2 16z"/></svg>' },
  { label: 'LinkedIn', href: 'https://linkedin.com', svg: '<svg viewBox="0 0 24 24" class="w-4 h-4 fill-current"><path d="M6.94 5a2 2 0 11-4-.02 2 2 0 014 .02zM7 8.48H3V21h4V8.48zm6.32 0H9.34V21h3.94v-6.57c0-3.66 4.77-3.96 4.77 0V21H22v-7.93c0-6.17-7.06-5.94-8.68-2.91V8.48z"/></svg>' },
  { label: 'YouTube', href: 'https://youtube.com', svg: '<svg viewBox="0 0 24 24" class="w-4 h-4 fill-current"><path d="M23.5 6.2a3 3 0 00-2.1-2.1C19.6 3.6 12 3.6 12 3.6s-7.6 0-9.4.5A3 3 0 00.5 6.2 31.6 31.6 0 000 12a31.6 31.6 0 00.5 5.8 3 3 0 002.1 2.1c1.8.5 9.4.5 9.4.5s7.6 0 9.4-.5a3 3 0 002.1-2.1A31.6 31.6 0 0024 12a31.6 31.6 0 00-.5-5.8zM9.6 15.6V8.4l6.3 3.6-6.3 3.6z"/></svg>' },
]
</script>

<style scoped>
.footer-heading { @apply text-white font-semibold text-sm mb-4; }
.footer-link { @apply block text-sm text-gray-400 hover:text-white transition-colors duration-200 mb-2.5; }
.social-icon { @apply w-9 h-9 rounded-lg bg-white/10 hover:bg-brand-600 flex items-center justify-center text-gray-300 hover:text-white transition-colors duration-200; }
</style>
