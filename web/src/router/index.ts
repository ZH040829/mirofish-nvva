import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Simulation from '../views/Simulation.vue'
import Agents from '../views/Agents.vue'
import DataPipeline from '../views/DataPipeline.vue'
import Report from '../views/Report.vue'
import System from '../views/System.vue'

const base = import.meta.env.BASE_URL || '/'

const router = createRouter({
  history: createWebHistory(base),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/simulation', name: 'simulation', component: Simulation },
    { path: '/agents', name: 'agents', component: Agents },
    { path: '/data', name: 'data', component: DataPipeline },
    { path: '/report', name: 'report', component: Report },
    { path: '/system', name: 'system', component: System },
  ],
})

export default router
