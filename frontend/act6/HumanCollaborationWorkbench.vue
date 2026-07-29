<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { HumanCollaboration } from '../src/types'

const props = defineProps<{ collaboration: HumanCollaboration }>()
const emit = defineEmits<{
  record: [value: HumanCollaboration['timeline'][number]]
}>()

type WorkbenchTab = 'approval' | 'adjust' | 'takeover' | 'experience'

const activeTab = ref<WorkbenchTab>('approval')
const selectedId = ref(props.collaboration.pending[0]?.id ?? '')
const reason = ref('')
const operator = ref('王工程师')
const adjustedValues = ref<string[]>([])
const templateId = ref(props.collaboration.templates[0]?.id ?? '')
const experience = ref({
  scene: '',
  diagnosis: '',
  strategy: '',
  regulation: '',
})
const feedback = ref('')

const selected = computed(() =>
  props.collaboration.pending.find((item) => item.id === selectedId.value),
)
const selectedTemplate = computed(() =>
  props.collaboration.templates.find((item) => item.id === templateId.value),
)

function syncParameters() {
  adjustedValues.value = selected.value?.parameters.map((item) => item.suggested) ?? []
}

function applyTemplate() {
  const template = selectedTemplate.value
  if (!template) return
  experience.value = {
    scene: template.scene,
    diagnosis: template.diagnosis,
    strategy: template.strategy,
    regulation: template.regulation,
  }
}

function saveRecord(action: string, status: string, detail: string) {
  const record = {
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    actor: operator.value,
    action,
    target: selected.value?.target ?? '专家经验库',
    detail,
    status,
  }
  emit('record', record)
  const history = JSON.parse(localStorage.getItem('traffic-human-loop-history') ?? '[]')
  localStorage.setItem('traffic-human-loop-history', JSON.stringify([record, ...history].slice(0, 50)))
  feedback.value = `${action}已记录：${status}`
  window.setTimeout(() => {
    feedback.value = ''
  }, 2600)
}

function approve() {
  saveRecord('审批通过', '待执行', reason.value || '确认风险边界、回滚条件与下游承接能力')
  reason.value = ''
}

function reject() {
  saveRecord('驳回方案', '已驳回', reason.value || '证据不足，要求补充多模态核验')
  reason.value = ''
}

function submitAdjustment() {
  const changes = selected.value?.parameters
    .map((item, index) => `${item.name}：${item.before} → ${adjustedValues.value[index]}`)
    .join('；')
  saveRecord('参数微调', '已留痕', `${changes}。原因：${reason.value || '保留安全裕度'}`)
}

function submitTakeover() {
  saveRecord('人工接管', '监控中', reason.value || '现场突发事件，暂停智能体自动下发')
}

function saveExperience(status: '草稿' | '已发布') {
  const payload = {
    ...experience.value,
    templateId: templateId.value,
    operator: operator.value,
    status,
    createdAt: new Date().toISOString(),
  }
  const records = JSON.parse(localStorage.getItem('traffic-experience-drafts') ?? '[]')
  localStorage.setItem('traffic-experience-drafts', JSON.stringify([payload, ...records].slice(0, 30)))
  saveRecord(status === '草稿' ? '保存经验草稿' : '发布专家经验', status, experience.value.strategy || '已完成四维经验录入')
}

watch(selectedId, syncParameters, { immediate: true })
watch(templateId, applyTemplate, { immediate: true })
</script>

<template>
  <section class="collab-workbench">
    <header class="workbench-header">
      <div>
        <small>HUMAN–AI CONTROL DESK</small>
        <h3>人机协同工作台</h3>
        <p>审批、调整、接管与经验沉淀均形成可追溯记录</p>
      </div>
      <div class="operator-chip"><i></i><span>当前值守</span><strong>{{ operator }}</strong></div>
    </header>

    <nav class="workbench-tabs">
      <button :class="{ active: activeTab === 'approval' }" @click="activeTab = 'approval'">
        <span>01</span>待审批<b>{{ collaboration.pending.length }}</b>
      </button>
      <button :class="{ active: activeTab === 'adjust' }" @click="activeTab = 'adjust'">
        <span>02</span>参数微调
      </button>
      <button :class="{ active: activeTab === 'takeover' }" @click="activeTab = 'takeover'">
        <span>03</span>人工接管
      </button>
      <button :class="{ active: activeTab === 'experience' }" @click="activeTab = 'experience'">
        <span>04</span>经验录入
      </button>
    </nav>

    <div v-if="activeTab !== 'experience'" class="workbench-body">
      <aside class="approval-queue">
        <button
          v-for="item in collaboration.pending"
          :key="item.id"
          :class="{ active: item.id === selectedId }"
          @click="selectedId = item.id"
        >
          <span>{{ item.level === 'intersection' ? '路口' : item.level === 'corridor' ? '走廊' : '应急' }}</span>
          <strong>{{ item.target }}</strong>
          <small>{{ item.id }} · {{ item.expiresAt }} 前处理</small>
        </button>
      </aside>

      <div v-if="selected" class="decision-form">
        <div class="strategy-brief">
          <span>AI 建议策略</span>
          <strong>{{ selected.strategy }}</strong>
          <p><b>风险边界</b>{{ selected.risk }}</p>
        </div>

        <div v-if="activeTab === 'approval'" class="approval-form">
          <div class="parameter-table">
            <div class="table-head"><span>参数</span><span>当前值</span><span>建议值</span></div>
            <div v-for="item in selected.parameters" :key="item.name">
              <strong>{{ item.name }}</strong><span>{{ item.before }}</span><b>{{ item.suggested }}</b>
            </div>
          </div>
          <label class="reason-field">
            <span>审批意见 / 约束条件</span>
            <textarea v-model="reason" placeholder="输入审批依据、执行约束或驳回原因"></textarea>
          </label>
          <div class="decision-actions">
            <button class="reject" @click="reject">驳回并退回补证</button>
            <button class="approve" @click="approve">确认风险边界并批准</button>
          </div>
        </div>

        <div v-else-if="activeTab === 'adjust'" class="adjustment-form">
          <div v-for="(item, index) in selected.parameters" :key="item.name" class="adjustment-row">
            <label>{{ item.name }}</label>
            <span>{{ item.before }}</span><i>→</i>
            <input v-model="adjustedValues[index]" />
          </div>
          <label class="reason-field">
            <span>调整依据</span>
            <textarea v-model="reason" placeholder="说明参数修改依据和预期效果"></textarea>
          </label>
          <button class="full-action" @click="submitAdjustment">保存调整并写入干预记录</button>
        </div>

        <div v-else class="takeover-form">
          <div class="takeover-warning">
            <b>人工接管将暂停该对象的自动策略下发</b>
            <span>系统继续监测并保留恢复自动控制入口，所有人工动作写入安全日志。</span>
          </div>
          <label class="reason-field">
            <span>接管原因与现场指令</span>
            <textarea v-model="reason" placeholder="请输入事件原因、保通目标和恢复条件"></textarea>
          </label>
          <button class="full-action danger" @click="submitTakeover">确认接管并启动持续监控</button>
        </div>
      </div>
    </div>

    <div v-else class="experience-editor">
      <div class="experience-toolbar">
        <label>
          <span>参考模板</span>
          <select v-model="templateId">
            <option v-for="item in collaboration.templates" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </label>
        <label>
          <span>记录人</span>
          <input v-model="operator" />
        </label>
        <div><button @click="saveExperience('草稿')">保存草稿</button><button class="publish" @click="saveExperience('已发布')">发布到经验库</button></div>
      </div>
      <div class="experience-dimensions">
        <label><span><b>01</b>场景认知</span><textarea v-model="experience.scene"></textarea></label>
        <label><span><b>02</b>问题诊断</span><textarea v-model="experience.diagnosis"></textarea></label>
        <label><span><b>03</b>控制策略</span><textarea v-model="experience.strategy"></textarea></label>
        <label><span><b>04</b>管控经验</span><textarea v-model="experience.regulation"></textarea></label>
      </div>
    </div>

    <transition name="workbench-toast">
      <div v-if="feedback" class="workbench-feedback"><i>✓</i>{{ feedback }}</div>
    </transition>
  </section>
</template>
