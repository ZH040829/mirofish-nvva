<template>
  <div id="mirofish-app" :class="{ 'dark-mode': isDark }">
    <el-container style="height: 100vh;">
      <!-- 侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>🐟 MiroFish</h2>
          <p class="subtitle">女娲数字孪生 v1.2.0</p>
        </div>
        <el-menu
          :default-active="currentRoute"
          router
          :background-color="isDark ? '#1a1a2e' : '#ffffff'"
          :text-color="isDark ? '#e0e0e0' : '#333333'"
          :active-text-color="isDark ? '#00d4ff' : '#409eff'"
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
          <el-menu-item index="/report">
            <el-icon><Document /></el-icon>
            <span>蒸馏报告</span>
          </el-menu-item>
          <el-menu-item index="/system">
            <el-icon><Setting /></el-icon>
            <span>系统运维</span>
          </el-menu-item>
        </el-menu>

        <!-- 系统状态 -->
        <div class="sidebar-footer">
          <div class="status-row">
            <span class="dot" :class="systemStatus"></span>
            <span>{{ systemStatus === 'running' ? '系统运行中' : '系统待启动' }}</span>
          </div>
          <div class="status-row">
            <span class="dot" :class="aiStatus"></span>
            <span>AI: {{ aiStatus === 'running' ? '在线' : '离线' }}</span>
          </div>
          <div class="status-row">
            <span class="dot running"></span>
            <span>Redis: 在线</span>
          </div>
        </div>
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
            <el-switch
              v-model="isDark"
              active-text="🌙"
              inactive-text="☀️"
              inline-prompt
              style="margin-left: 16px;"
            />
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
import { Monitor, VideoPlay, User, DataAnalysis, Document, Setting } from '@element-plus/icons-vue'
import { api } from './api'

const route = useRoute()
const currentRoute = computed(() => route.path)
const systemStatus = ref('running')
const aiStatus = ref('standby')
const agentCount = ref(4)
const taskCount = ref(0)
const isDark = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/health')
    systemStatus.value = data.status || 'running'
    aiStatus.value = data.components?.ai_agent || 'standby'
  } catch { /* ignore */ }
  try {
    const { data } = await api.get('/simulation/list')
    taskCount.value = data.total || 0
  } catch { /* ignore */ }
  try {
    const { data } = await api.ai.get('/health')
    aiStatus.value = data.components?.llm_agent || 'standby'
  } catch { /* ignore */ }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

/* 暗色主题 */
.dark-mode body, .dark-mode .main-content { background: #0f0f23; color: #e0e0e0; }
.dark-mode .sidebar { background: #1a1a2e; border-right: 1px solid #2a2a4a; }
.dark-mode .top-bar { background: #16213e; border-bottom: 1px solid #2a2a4a; }
.dark-mode .system-title { color: #00d4ff; }
.dark-mode .el-card { background: #1a1a2e; border-color: #2a2a4a; color: #e0e0e0; }
.dark-mode .el-card__header { border-bottom-color: #2a2a4a; color: #e0e0e0; }

/* 亮色主题 */
body { background: #f5f7fa; color: #333; }
.sidebar { background: #fff; border-right: 1px solid #e4e7ed; }
.top-bar { background: #fff; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.system-title { font-size: 16px; font-weight: 600; }

.logo { padding: 20px; text-align: center; border-bottom: 1px solid #2a2a4a; }
.logo h2 { color: #00d4ff; font-size: 20px; }
.logo .subtitle { color: #888; font-size: 12px; margin-top: 4px; }

.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; gap: 16px; }
.badge-item { margin-right: 10px; }

.main-content { padding: 20px; overflow-y: auto; }

.el-menu { border-right: none !important; }
.el-menu-item { font-size: 14px; }

.sidebar-footer {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 16px; border-top: 1px solid #2a2a4a;
  font-size: 12px;
}
.status-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.running { background: #67c23a; box-shadow: 0 0 6px #67c23a; }
.dot.standby { background: #909399; }
.dot.error { background: #f56c6c; box-shadow: 0 0 6px #f56c6c; }
</style>
