import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/market', name: 'market', component: () => import('@/views/MarketView.vue') },
    { path: '/news', name: 'news', component: () => import('@/views/NewsView.vue') },
    { path: '/graph', name: 'graph', component: () => import('@/views/GraphView.vue') },
    { path: '/narrative', name: 'narrative', component: () => import('@/views/NarrativeView.vue') },
    { path: '/reports', name: 'reports', component: () => import('@/views/ReportView.vue') },
    { path: '/pipeline', name: 'pipeline', component: () => import('@/views/PipelineView.vue') },
    { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
  ],
})

export default router
