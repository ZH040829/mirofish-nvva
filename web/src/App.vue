<template>
  <div id="mirofish-app" :class="{ 'dark-mode': isDark }">
    <el-container style="height: 100vh;">
      <!-- 侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>🐟 MiroFish</h2>
          <p class="subtitle">女娲数字孪生 v1.4.0</p>
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
            <span class="dot" :class="goOnline ? 'running' : 'error'"></span>
            <span>Go 引擎: {{ goOnline ? '在线' : '离线' }}</span>
          </div>
          <div class="status-row">
            <span class="dot" :class="aiOnline ? 'running' : 'error'"></span>
            <span>AI 服务: {{ aiOnline ? '在线' : '离线' }}</span>
          </div>
          <div class="status-row">
            <span class="dot" :class="redisOnline ? 'running' : 'standby'"></span>
            <span>Redis: {{ redisOnline ? '在线' : '离线' }}</span>
          </div>
          <el-button size="small" type="primary" text style="margin-top:8px;width:100%;" @click="showConnectDialog = true">
            ⚙ 连接设置
          </el-button>
        </div>
      </el-aside>

      <!-- 主内容 -->
      <el-container>
        <el-header class="top-bar">
          <div class="header-left">
            <span class="system-title">MiroFish 企业经营数字孪生系统</span>
            <el-tag :type="goOnline && aiOnline ? 'success' : 'warning'" size="small">
              {{ goOnline && aiOnline ? '● 全部在线' : '○ 部分离线' }}
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
          <!-- 离线提示横幅 -->
          <el-alert
            v-if="!goOnline || !aiOnline"
            :title="`服务连接异常: ${!goOnline ? 'Go引擎离线' : ''}${!goOnline && !aiOnline ? '，' : ''}${!aiOnline ? 'AI服务离线' : ''}`"
            type="warning"
            description="请点击左侧「连接设置」配置后端 API 地址，或确认本地服务已启动"
            show-icon
            :closable="false"
            style="margin-bottom: 16px;"
          />
          <router-view />
        </el-main>
      </el-container>
    </el-container>

    <!-- 连接设置对话框 -->
    <el-dialog v-model="showConnectDialog" title="连接设置" width="500px">
      <el-form label-width="120px">
        <el-form-item label="Go 引擎地址">
          <el-input v-model="gatewayUrlInput" placeholder="http://localhost:9090/api">
            <template #append>
              <el-button @click="testGoConnect" :loading="testingGo" :type="goOnline ? 'success' : 'default'">
                {{ goOnline ? '已连接' : '测试' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="AI 服务地址">
          <el-input v-model="aiUrlInput" placeholder="http://localhost:8000/api">
            <template #append>
              <el-button @click="testAiConnect" :loading="testingAi" :type="aiOnline ? 'success' : 'default'">
                {{ aiOnline ? '已连接' : '测试' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveConnectConfig">保存并连接</el-button>
          <el-button @click="resetConnectConfig">恢复默认</el-button>
        </el-form-item>
      </el-form>
      <el-divider />
      <div style="font-size: 12px; color: #909399; line-height: 1.8;">
        <p><b>使用说明：</b></p>
        <p>1. 本地开发：使用默认 localhost 地址即可</p>
        <p>2. 远程访问：输入后端服务器 IP:端口/api</p>
        <p>3. 启动本地服务：cd mirofish && ./scripts/start.sh</p>
        <p>4. Go 引擎端口: 9090，AI 服务端口: 8000</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, VideoPlay, User, DataAnalysis, Document, Setting } from '@element-plus/icons-vue'
import { api, updateApiConfig, getApiConfig, probeApiConnectivity } from './api'

const route = useRoute()
const currentRoute = computed(() => route.path)
const isDark = ref(true)
const agentCount = ref(4)
const taskCount = ref(0)

// 连接状态
const goOnline = ref(false)
const aiOnline = ref(false)
const redisOnline = ref(false)
const showConnectDialog = ref(false)
const testingGo = ref(false)
const testingAi = ref(false)

// 连接配置
const config = getApiConfig()
const gatewayUrlInput = ref(config.gatewayUrl || 'http://localhost:9090/api')
const aiUrlInput = ref(config.aiUrl || 'http://localhost:8000/api')

// 检测连接
async function checkConnectivity() {
  const result = await probeApiConnectivity()
  goOnline.value = result.go
  aiOnline.value = result.ai
  redisOnline.value = result.go // Redis 状态跟随 Go
}

async function testGoConnect() {
  testingGo.value = true
  try {
    const saved = gateway.defaults.baseURL
    gateway.defaults.baseURL = gatewayUrlInput.value
    await gateway.get('/health', { timeout: 5000 })
    goOnline.value = true
  } catch {
    goOnline.value = false
  }
  testingGo.value = false
}

async function testAiConnect() {
  testingAi.value = true
  try {
    const saved = aiService.defaults.baseURL
    aiService.defaults.baseURL = aiUrlInput.value
    await aiService.get('/health', { timeout: 5000 })
    aiOnline.value = true
  } catch {
    aiOnline.value = false
  }
  testingAi.value = false
}

function saveConnectConfig() {
  updateApiConfig(gatewayUrlInput.value, aiUrlInput.value)
  checkConnectivity()
  showConnectDialog.value = false
  // 刷新页面数据
  loadAppData()
}

function resetConnectConfig() {
  gatewayUrlInput.value = 'http://localhost:9090/api'
  aiUrlInput.value = 'http://localhost:8000/api'
}

import { gateway, aiService } from './api'

async function loadAppData() {
  if (goOnline.value) {
    try {
      const { data } = await api.get('/health')
      if (data.components) {
        redisOnline.value = data.components.redis === 'running'
      }
    } catch { /* ignore */ }
    try {
      const { data } = await api.get('/simulation/list')
      taskCount.value = data.total || 0
    } catch { /* ignore */ }
  }
}

// 定时检测
let timer: number | null = null

onMounted(async () => {
  await checkConnectivity()
  await loadAppData()
  // 每 15 秒检测一次连接
  timer = window.setInterval(async () => {
    await checkConnectivity()
  }, 15000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
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
.dark-mode .el-dialog { background: #1a1a2e; }
.dark-mode .el-form-item__label { color: #e0e0e0; }
.dark-mode .el-input__wrapper { background: #2a2a4a; box-shadow: none; }
.dark-mode .el-input__inner { color: #e0e0e0; }
.dark-mode .el-divider { border-color: #2a2a4a; }
.dark-mode .el-alert--warning { background: #2a2a1e; border-color: #5a5a2a; }

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
