<template>
  <el-container class="home-container">
    <el-aside width="280px" class="sidebar">
      <SessionList />
    </el-aside>
    <el-main class="main-content">
      <div class="workspace">
        <div class="chat-shell">
          <ChatInterface />
        </div>
        <ResearchPanel />
      </div>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import SessionList from '@/components/SessionList.vue'
import ChatInterface from '@/components/ChatInterface.vue'
import ResearchPanel from '@/components/ResearchPanel.vue'
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

.workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-shell {
  min-height: 0;
  flex: 1;
}
</style>
