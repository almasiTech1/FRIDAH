export default {
  darkMode: 'class',
  content: ['./index.html','./src/**/*.{vue,js,ts,jsx,tsx}'],
  safelist: [
    ...['tenant', 'landlord', 'agency', 'provider', 'hotel', 'adminc'].flatMap((c) => [
      `bg-${c}-50`, `bg-${c}-100`, `bg-${c}-200`, `bg-${c}-600`, `bg-${c}-700`,
      `text-${c}-600`, `text-${c}-700`, `border-${c}-200`, `hover:bg-${c}-700`, `hover:border-${c}-200`,
    ]),
  ],
  theme: {
    extend: {
      colors: {
        tenant:   { DEFAULT:'#10b981',50:'#ecfdf5',100:'#d1fae5',200:'#a7f3d0',600:'#059669',700:'#047857',900:'#064e3b' },
        landlord: { DEFAULT:'#6366f1',50:'#eef2ff',100:'#e0e7ff',200:'#c7d2fe',600:'#4f46e5',700:'#4338ca',900:'#312e81' },
        adminc:   { DEFAULT:'#8b5cf6',50:'#f5f3ff',100:'#ede9fe',200:'#ddd6fe',600:'#7c3aed',700:'#6d28d9',900:'#4c1d95' },
        provider: { DEFAULT:'#f97316',50:'#fff7ed',100:'#ffedd5',200:'#fed7aa',600:'#ea580c',700:'#c2410c',900:'#7c2d12' },
        hotel:    { DEFAULT:'#f59e0b',50:'#fffbeb',100:'#fef3c7',200:'#fde68a',600:'#d97706',700:'#b45309',900:'#78350f' },
        agency:   { DEFAULT:'#0ea5e9',50:'#f0f9ff',100:'#e0f2fe',200:'#bae6fd',600:'#0284c7',700:'#0369a1',900:'#0c4a6e' },
        brand:    { DEFAULT:'#0d9488',50:'#f0fdfa',100:'#ccfbf1',200:'#99f6e4',300:'#5eead4',400:'#2dd4bf',500:'#14b8a6',600:'#0d9488',700:'#0f766e',800:'#115e59',900:'#134e4a',950:'#042f2e' },
      },
      fontFamily: { sans: ['Inter','system-ui','sans-serif'] },
      boxShadow: {
        'glow-green': '0 0 30px -5px rgba(16,185,129,0.4)',
        'glow-indigo': '0 0 30px -5px rgba(99,102,241,0.4)',
        'glow-purple': '0 0 30px -5px rgba(139,92,246,0.4)',
        'glow-orange': '0 0 30px -5px rgba(249,115,22,0.4)',
        'glow-amber':  '0 0 30px -5px rgba(245,158,11,0.4)',
        'card-hover': '0 20px 40px -12px rgba(0,0,0,0.12)',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'count': 'fadeIn 0.6s ease both',
        'marquee': 'marquee 30s linear infinite',
      },
      keyframes: {
        float: { '0%,100%': { transform:'translateY(0)' }, '50%': { transform:'translateY(-6px)' } },
        marquee: { '0%': { transform: 'translateX(0)' }, '100%': { transform: 'translateX(-50%)' } },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
