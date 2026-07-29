import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    // Act 6 的 ECharts 已独立懒加载；该阈值只覆盖其可视化分包。
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
  },
})
