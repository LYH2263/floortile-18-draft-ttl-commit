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
const draft = ref(null)
const confirmedRunId = ref(null)
const err = ref('')
const busy = ref(false)

onMounted(async () => {
  rooms.value = (await getJSON('/api/rooms')).items.filter(r => r.data_quality === 'clean')
  tiles.value = (await getJSON('/api/tiles')).items.filter(t => t.data_quality === 'clean')
  if (rooms.value.length) roomId.value = rooms.value[0].id
  if (tiles.value.length) tileId.value = tiles.value[0].id
})

// 选择变化后旧草稿即作废，需要重新生成
watch([roomId, tileId], () => {
  draft.value = null
  confirmedRunId.value = null
})

async function preview() {
  err.value = ''
  confirmedRunId.value = null
  try {
    result.value = await getJSON(`/api/estimate?room_id=${roomId.value}&tile_id=${tileId.value}`)
  } catch (e) {
    err.value = e.message
    result.value = null
  }
}

async function makeDraft() {
  err.value = ''
  confirmedRunId.value = null
  busy.value = true
  try {
    draft.value = await postJSON('/api/estimate/draft', {
      room_id: roomId.value,
      tile_id: tileId.value,
      note: '下单台草稿',
    })
    result.value = draft.value
  } catch (e) {
    err.value = e.message
    draft.value = null
  } finally {
    busy.value = false
  }
}

async function confirmDraft() {
  if (!draft.value) return
  err.value = ''
  busy.value = true
  try {
    const r = await postJSON('/api/estimate/confirm', { draft_id: draft.value.draft_id })
    confirmedRunId.value = r.run_id
    draft.value = null
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}

function fmtTs(iso) {
  return iso ? new Date(iso).toLocaleString() : ''
}
</script>
<template>
  <div class="page">
    <h1>下单测算</h1>
    <label>房间 <select v-model.number="roomId"><option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option></select></label>
    <label>砖型 <select v-model.number="tileId"><option v-for="t in tiles" :key="t.id" :value="t.id">{{ t.name }}</option></select></label>
    <button :disabled="busy" @click="preview">试算</button>
    <button :disabled="busy" @click="makeDraft">生成草稿</button>
    <button :disabled="busy || !draft" @click="confirmDraft">确认下单</button>
    <p v-if="err" class="alert">{{ err }}</p>
    <p v-if="draft" class="draft-banner">
      草稿 #{{ draft.draft_id }}（{{ fmtTs(draft.expires_at) }} 前有效），确认后才会写入测算记录
    </p>
    <p v-if="confirmedRunId" class="ok-banner">
      已确认，记录 #{{ confirmedRunId }} 已写入测算历史
    </p>
    <OrderSummary :result="result" />
    <TileGridPreview v-if="result?.layout" :cols="result.layout.cols" :rows="result.layout.rows" :grid-count="result.layout.grid_count" />
  </div>
</template>
