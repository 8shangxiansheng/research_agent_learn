<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1>Academic Q&A Agent</h1>
        <span class="subtitle">AI-powered academic paper research assistant</span>
      </div>
    </el-header>
    <el-main class="app-main">
      <Home />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import Home from './views/Home.vue'
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

.app-main {
  padding: 0;
  height: calc(100% - 60px);
  overflow: hidden;
}
</style>
