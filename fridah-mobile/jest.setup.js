// AsyncStorage has no native module under Jest; a tiny in-memory stand-in is enough for the stores.
jest.mock('@react-native-async-storage/async-storage', () => {
  const store = {}
  const api = {
    getItem: jest.fn(async (k) => (k in store ? store[k] : null)),
    setItem: jest.fn(async (k, v) => { store[k] = v }),
    removeItem: jest.fn(async (k) => { delete store[k] }),
    clear: jest.fn(async () => { Object.keys(store).forEach((k) => delete store[k]) }),
  }
  return { __esModule: true, default: api, ...api }
})
