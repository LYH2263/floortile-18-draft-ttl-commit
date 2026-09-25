<script setup>
import { onMounted, ref, watch } from 'vue'
import { getJSON, postJSON } from '../api'
import OrderSummary from '../components/OrderSummary.vue'
import TileGridPreview from '../components/TileGridPreview.vue'

const rooms = ref([])
const tiles = ref([])
const roomId = ref(1)
const tileId = ref(1)
const result = ref(null)
const draftId = ref(null)
const expiresAt = ref('')
const confirmedRunId = ref(null)
const err = ref('')

onMounted(async () => {
  rooms.value = (await getJSON('/api/rooms')).items.filter(r => r.data_quality === 'clean')
  tiles.value = (await getJSON('/api/tiles')).items.filter(t => t.data_quality === 'clean')
  if (rooms.value.length) roomId.value = rooms.value[0].id
  if (tiles.value.length) tileId.value = tiles.value[0].id
})

// 草稿绑定当时的房间/砖型，切换选择后旧草稿不再适用
watch([roomId, tileId], () => {
  result.value = null
  draftId.value = null
  expiresAt.value = ''
  confirmedRunId.value = null
  err.value = ''
})

async function preview() {
  err.value = ''
  confirmedRunId.value = null
  try {
    const d = await postJSON('/api/estimate/draft', {
      room_id: roomId.value,
      tile_id: tileId.value,
    })
    result.value = d
    draftId.value = d.draft_id
    expiresAt.value = d.expires_at
  } catch (e) {
    err.value = e.message
    result.value = null
    draftId.value = null
  }
}

async function confirmDraft() {
  err.value = ''
  try {
    const r = await postJSON('/api/estimate/confirm', {
      draft_id: draftId.value,
      note: '下单台确认',
    })
    confirmedRunId.value = r.run_id
    draftId.value = null
    expiresAt.value = ''
  } catch (e) {
    err.value = e.message
  }
}
</script>
<template>
  <div class="page">
    <h1>下单测算</h1>
    <label>房间 <select v-model.number="roomId"><option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option></select></label>
    <label>砖型 <select v-model.number="tileId"><option v-for="t in tiles" :key="t.id" :value="t.id">{{ t.name }}</option></select></label>
    <button @click="preview">试算</button>
    <button :disabled="!draftId" @click="confirmDraft">确认下单</button>
    <p v-if="err" class="alert">{{ err }}</p>
    <p v-if="draftId" class="muted">草稿 #{{ draftId }} 已生成，{{ new Date(expiresAt).toLocaleString() }} 前确认有效，确认后才会写入历史。</p>
    <p v-if="confirmedRunId" class="ok">已确认，历史记录 #{{ confirmedRunId }} 已生成。</p>
    <OrderSummary :result="result" />
    <TileGridPreview v-if="result?.layout" :cols="result.layout.cols" :rows="result.layout.rows" :grid-count="result.layout.grid_count" />
  </div>
</template>
