<template>
  <el-container class="home-container">
    <el-aside width="280px" class="sidebar">
      <SessionList />
    </el-aside>
    <el-main class="main-content">
      <ChatInterface />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import SessionList from '@/components/SessionList.vue'
import ChatInterface from '@/components/ChatInterface.vue'
</script>

<style scoped>
.home-container {
  height: 100%;
}

.sidebar {
  padding: 0;
  height: 100%;
}

.main-content {
  padding: 0;
  height: 100%;
}
</style>
