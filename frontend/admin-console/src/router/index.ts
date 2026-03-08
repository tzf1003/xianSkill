import { createRouter, createWebHistory } from 'vue-router'
import { getStoredToken } from '@/api/client'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
    { path: '/skills', name: 'skills', component: () => import('@/views/SkillsView.vue') },
    { path: '/skus', name: 'skus', component: () => import('@/views/SKUsView.vue') },
    { path: '/goods', name: 'goods', component: () => import('@/views/GoodsView.vue') },
    { path: '/shops', name: 'shops', component: () => import('@/views/ShopsView.vue') },
    { path: '/orders', name: 'orders', component: () => import('@/views/OrdersView.vue') },
    { path: '/tokens', name: 'tokens', component: () => import('@/views/TokensView.vue') },
    { path: '/jobs', name: 'jobs', component: () => import('@/views/JobsView.vue') },
    { path: '/projects', name: 'projects', component: () => import('@/views/ProjectsView.vue') },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!getStoredToken()) return { name: 'login' }
})

export default router
