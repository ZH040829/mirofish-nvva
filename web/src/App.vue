<template>
  <div id="mirofish-app">
    <el-container style="height: 100vh;">
      <!-- 侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>🐟 MiroFish</h2>
          <p class="subtitle">女娲数字孪生</p>
        </div>
        <el-menu
          :default-active="currentRoute"
          router
          background-color="#1a1a2e"
          text-color="#e0e0e0"
          active-text-color="#00d4ff"
        >
          <el-menu-item index="/">
            <el-icon><Monitor /></el-icon>
            <span>仿真仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/simulation">
            <el-icon><VideoPlay /></el-icon>
            <span>仿真推演</span>
          </el-menu-item>
          <el-menu-item index="/agents">
            <el-icon><User /></el-icon>
            <span>智能体管理</span>
          </el-menu-item>
          <el-menu-item index="/data">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据管道</span>
          </el-menu-item>
          <el-menu-item index="/data-ingestion">
            <el-icon><Upload /></el-icon>
            <span>数据接入</span>
          </el-menu-item>
          <el-menu-item index="/report">
            <el-icon><Document /></el-icon>
            <span>蒸馏报告</span>
          </el-menu-item>
          <el-menu-item index="/system">
            <el-icon><Setting /></el-icon>
            <span>系统运维</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容 -->
      <el-container>
        <el-header class="top-bar">
          <div class="header-left">
            <span class="system-title">MiroFish 企业经营数字孪生系统</span>
            <el-tag :type="systemStatus === 'running' ? 'success' : 'info'" size="small">
              {{ systemStatus === 'running' ? '● 运行中' : '○ 待启动' }}
            </el-tag>
          </div>
          <div class="header-right">
            <el-badge :value="agentCount" class="badge-item">
              <el-button size="small" text>智能体</el-button>
            </el-badge>
            <el-badge :value="taskCount" class="badge-item">
              <el-button size="small" text>任务</el-button>
            </el-badge>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, VideoPlay, User, DataAnalysis, Upload, Document, Setting } from '@element-plus/icons-vue'
import * as api from './api'

const route = useRoute()
const currentRoute = computed(() => route.path)
const systemStatus = ref('running')
const agentCount = ref(4)
const taskCount = ref(0)

onMounted(async () => {
  try {
    const { data } = await api.getSystemHealth()
    systemStatus.value = data.components?.ai_agent === 'running' ? 'running' : 'standby'
  } catch { /* ignore */ }
  try {
    const { data } = await api.getSimulationList()
    taskCount.value = data.total || 0
  } catch { /* ignore */ }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f0f23; color: #e0e0e0; }

.sidebar {
  background: #1a1a2e;
  border-right: 1px solid #2a2a4a;
}
.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #2a2a4a;
}
.logo h2 { color: #00d4ff; font-size: 20px; }
.logo .subtitle { color: #888; font-size: 12px; margin-top: 4px; }

.top-bar {
  background: #16213e;
  border-bottom: 1px solid #2a2a4a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.system-title { font-size: 16px; font-weight: 600; color: #00d4ff; }
.header-right { display: flex; align-items: center; gap: 16px; }
.badge-item { margin-right: 10px; }

.main-content {
  background: #0f0f23;
  padding: 20px;
}

.el-menu { border-right: none !important; }
.el-menu-item { font-size: 14px; }
.el-menu-item:hover { background-color: #2a2a4a !important; }
</style>
