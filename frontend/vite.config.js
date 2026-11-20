import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    clearMocks: true,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, "/");
          if (
            normalizedId.includes("/node_modules/katex/") ||
            normalizedId.includes("/node_modules/rehype-katex/") ||
            normalizedId.includes("/node_modules/remark-math/") ||
            normalizedId.includes("/node_modules/micromark-extension-math/")
          ) {
            return "math-rendering";
          }
        },
      },
    },
  },
});
