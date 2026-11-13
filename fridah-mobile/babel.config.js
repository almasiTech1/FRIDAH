module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [
    // Inlines process.env.FRIDAH_API_URL at build time (see src/api/client.ts) so
    // `FRIDAH_API_URL=http://10.0.2.2:8000/api/v1 npx react-native start --reset-cache`
    // can point the app at a local backend during development.
    'transform-inline-environment-variables',
    [
      'module-resolver',
      {
        root: ['./src'],
        extensions: ['.ios.js', '.android.js', '.js', '.ts', '.tsx', '.json'],
        alias: { '@': './src' },
      },
    ],
  ],
}
