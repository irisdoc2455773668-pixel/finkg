<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { NLayout, NLayoutHeader, NLayoutContent, NMenu, NButton, NDatePicker, NSpace, NTag, NSpin, NMessageProvider } from 'naive-ui'
import { useRouter, useRoute } from 'vue-router'

const store = useAppStore()
const router = useRouter()
const route = useRoute()

onMounted(() => store.fetchStatus())

const menuOptions = [
  { label: '管道', key: 'pipeline' },
  { label: '总览', key: 'dashboard' },
  { label: '市场', key: 'market' },
  { label: '资讯', key: 'news' },
  { label: '图谱', key: 'graph' },
  { label: '叙事', key: 'narrative' },
  { label: '报告', key: 'reports' },
  { label: '设置', key: 'settings' },
]

function onMenuChange(key: string) {
  router.push({ name: key })
}
</script>

<template>
  <n-message-provider>
    <n-layout style="min-height:100vh">
    <n-layout-header bordered style="padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:32px">
        <span style="font-size:20px;font-weight:700;font-family:Georgia,serif">
          Fin<span style="color:#d97706">KG</span>
          <span style="font-size:11px;color:#999;margin-left:6px;font-weight:400">v5</span>
        </span>
        <n-menu mode="horizontal" :value="String(route.name)" :options="menuOptions" @update:value="onMenuChange" />
      </div>
      <n-space align="center">
        <span style="font-size:12px;color:#999">时间范围:</span>
        <n-date-picker v-model:formatted-value="store.dateFrom" type="date" value-format="yyyy-MM-dd" size="small" style="width:130px" />
        <span style="color:#999">—</span>
        <n-date-picker v-model:formatted-value="store.dateTo" type="date" value-format="yyyy-MM-dd" size="small" style="width:130px" />
        <n-button size="small" @click="store.fetchStatus" :loading="store.loading">刷新</n-button>
      </n-space>
    </n-layout-header>
    <n-layout-content style="padding:24px;max-width:1400px;margin:0 auto;width:100%">
      <n-spin :show="store.loading">
        <router-view />
      </n-spin>
    </n-layout-content>
  </n-layout>
  </n-message-provider>
</template>
