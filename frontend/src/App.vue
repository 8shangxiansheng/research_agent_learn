<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <div>
          <h1>{{ localeStore.t('app.title') }}</h1>
          <span class="subtitle">{{ localeStore.t('app.subtitle') }}</span>
        </div>
        <button
          type="button"
          class="locale-toggle"
          @click="localeStore.toggleLocale()"
        >
          {{ localeStore.t('app.language') }} · {{ localeStore.nextLocaleLabel }}
        </button>
      </div>
    </el-header>
    <el-main class="app-main">
      <Home />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import Home from './views/Home.vue'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.app-container {
  height: 100%;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px !important;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.header-content .subtitle {
  font-size: 12px;
  opacity: 0.8;
  margin-left: 15px;
}

.locale-toggle {
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  color: white;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.locale-toggle:hover {
  background: rgba(255, 255, 255, 0.24);
}

.app-main {
  padding: 0;
  height: calc(100% - 60px);
  overflow: hidden;
}
</style>
