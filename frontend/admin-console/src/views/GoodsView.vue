<template>
  <div>
    <!-- ── Tab 切换 ── -->
    <div class="tab-bar">
      <button :class="['tab-btn', tab === 'goods' && 'active']" @click="tab = 'goods'">商品管理</button>
      <button :class="['tab-btn', tab === 'orders' && 'active']" @click="tab = 'orders'; loadOrders()">闲管家订单</button>
    </div>

    <!-- ══════════ 商品管理 Tab ══════════ -->
    <template v-if="tab === 'goods'">
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="total-hint">共 {{ total }} 件商品</span>
          <select v-model="filterType" class="filter-select" @change="offset = 0; load()">
            <option :value="undefined">全部类型</option>
            <option :value="1">直充</option>
            <option :value="2">卡密</option>
            <option :value="3">券码</option>
          </select>
          <select v-model="filterStatus" class="filter-select" @change="offset = 0; load()">
            <option :value="undefined">全部状态</option>
            <option :value="1">在架</option>
            <option :value="2">下架</option>
          </select>
        </div>
        <button class="btn btn-primary" @click="openCreate">＋ 新建商品</button>
      </div>

      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>Logo</th><th>商品编号</th><th>商品名称</th><th>类型</th><th>规格</th>
              <th>价格(分)</th><th>库存</th><th>闲管家ID</th><th>状态</th><th>更新时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="items.length === 0">
              <td colspan="11" class="empty-row">暂无数据</td>
            </tr>
            <tr v-for="g in items" :key="g.id">
              <td>
                <img v-if="g.logo_url" :src="g.logo_url" class="goods-logo" alt="logo" />
                <span v-else class="no-logo">无</span>
              </td>
              <td><code class="tiny">{{ g.goods_no }}</code></td>
              <td><b>{{ g.goods_name }}</b></td>
              <td><span class="badge" :class="typeBadge(g.goods_type)">{{ typeLabel(g.goods_type) }}</span></td>
              <td>
                <span class="badge" :class="g.multi_spec ? 'badge-info' : 'badge-success'">
                  {{ g.multi_spec ? `多规格(${g.specs?.length ?? 0})` : '单规格' }}
                </span>
              </td>
              <td>{{ g.price_cents }}</td>
              <td>{{ g.stock }}</td>
              <td>
                <code v-if="g.xgj_goods_id" class="tiny">{{ g.xgj_goods_id }}</code>
                <span v-else class="text-muted">未绑定</span>
              </td>
              <td>
                <span :class="g.status === 1 ? 'badge badge-active' : 'badge badge-revoked'">
                  {{ g.status === 1 ? '在架' : '下架' }}
                </span>
              </td>
              <td>{{ fmt(g.updated_at) }}</td>
              <td class="action-cell">
                <button class="btn btn-secondary btn-sm" @click="openEdit(g)">编辑</button>
                <button v-if="g.multi_spec" class="btn btn-ghost btn-sm" @click="openSpecs(g)">规格</button>
                <button class="btn btn-danger btn-sm" @click="handleDelete(g)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <button class="btn btn-secondary btn-sm" :disabled="offset === 0" @click="offset -= PAGE_SIZE; load()">上一页</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button class="btn btn-secondary btn-sm" :disabled="offset + PAGE_SIZE >= total" @click="offset += PAGE_SIZE; load()">下一页</button>
        </div>
      </div>
    </template>

    <!-- ══════════ 闲管家订单 Tab ══════════ -->
    <template v-if="tab === 'orders'">
      <div class="toolbar">
        <span class="total-hint">共 {{ ordersTotal }} 条订单</span>
      </div>
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>闲管家订单号</th><th>我方订单号</th><th>商品编号</th>
              <th>类型</th><th>数量</th><th>总价(分)</th><th>状态</th><th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="orderItems.length === 0">
              <td colspan="8" class="empty-row">暂无数据</td>
            </tr>
            <tr v-for="o in orderItems" :key="o.id">
              <td><code class="tiny">{{ o.order_no }}</code></td>
              <td><code class="tiny">{{ o.out_order_no }}</code></td>
              <td>{{ o.goods_no }}</td>
              <td>{{ typeLabel(o.goods_type) }}</td>
              <td>{{ o.quantity }}</td>
              <td>{{ o.total_price_cents }}</td>
              <td><span class="badge" :class="orderStatusBadge(o.status)">{{ orderStatusLabel(o.status) }}</span></td>
              <td>{{ fmt(o.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <button class="btn btn-secondary btn-sm" :disabled="ordersOffset === 0" @click="ordersOffset -= PAGE_SIZE; loadOrders()">上一页</button>
          <span>{{ ordersPage }} / {{ ordersTotalPages }}</span>
          <button class="btn btn-secondary btn-sm" :disabled="ordersOffset + PAGE_SIZE >= ordersTotal" @click="ordersOffset += PAGE_SIZE; loadOrders()">下一页</button>
        </div>
      </div>
    </template>

    <!-- ══════════ 新建/编辑商品 Modal ══════════ -->
    <Modal v-model="showGoodsModal" :title="editingGoods ? '编辑商品' : '新建商品'">
      <div class="form-grid">
        <!-- Logo 上传 -->
        <div class="form-group" style="grid-column:1/-1">
          <label>商品图片 / Logo</label>
          <div class="logo-upload-area">
            <img v-if="logoPreview || goodsForm.logo_url" :src="logoPreview || goodsForm.logo_url!" class="logo-preview" alt="logo" />
            <div v-else class="logo-placeholder">点击上传图片</div>
            <input type="file" accept="image/*" class="logo-file-input" @change="onLogoSelected" />
          </div>
        </div>
        <div class="form-group" v-if="editingGoods">
          <label>商品编号</label>
          <input :value="editingGoods.goods_no" disabled class="input-disabled" />
        </div>
        <div class="form-group">
          <label>商品类型 *</label>
          <select v-model.number="goodsForm.goods_type">
            <option :value="1">直充</option>
            <option :value="2">卡密</option>
            <option :value="3">券码</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>商品名称 *</label>
          <input v-model="goodsForm.goods_name" placeholder="月卡充值" />
        </div>
        <div class="form-group">
          <label>价格（分）</label>
          <input v-model.number="goodsForm.price_cents" type="number" min="0" />
        </div>
        <div class="form-group">
          <label>库存</label>
          <input v-model.number="goodsForm.stock" type="number" min="0" />
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model.number="goodsForm.status">
            <option :value="1">在架</option>
            <option :value="2">下架</option>
          </select>
        </div>
        <div class="form-group">
          <label>规格模式</label>
          <select v-model="goodsForm.multi_spec" :disabled="!!editingGoods && (editingGoods.specs?.length ?? 0) > 1">
            <option :value="false">单规格</option>
            <option :value="true">多规格</option>
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1" v-if="editingGoods">
          <label>闲管家商品ID</label>
          <input v-model="goodsForm.xgj_goods_id" placeholder="绑定闲管家后填写（可选）" />
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label>描述</label>
          <textarea v-model="goodsForm.description" rows="2" placeholder="商品描述（可选）"></textarea>
        </div>

        <div class="form-group" style="grid-column:1/-1">
          <label class="section-label">闲管家商品配置</label>
        </div>
        <div class="xgj-grid" style="grid-column:1/-1">
          <label class="form-group"><span>item_biz_type *</span><input v-model.number="goodsForm.xgj_profile.item_biz_type" type="number" min="0" /></label>
          <label class="form-group"><span>sp_biz_type *</span><input v-model.number="goodsForm.xgj_profile.sp_biz_type" type="number" min="0" /></label>
          <label class="form-group"><span>category_id</span><input v-model.number="goodsForm.xgj_profile.category_id" type="number" min="0" /></label>
          <label class="form-group"><span>channel_cat_id *</span><input v-model="goodsForm.xgj_profile.channel_cat_id" placeholder="闲管家类目ID" /></label>
          <label class="form-group"><span>原价(分)</span><input v-model.number="goodsForm.xgj_profile.original_price_cents" type="number" min="0" /></label>
          <label class="form-group"><span>运费(分)</span><input v-model.number="goodsForm.xgj_profile.express_fee_cents" type="number" min="0" /></label>
          <label class="form-group"><span>成色</span><input v-model.number="goodsForm.xgj_profile.stuff_status" type="number" /></label>
          <label class="form-group"><span>flash_sale_type</span><input v-model.number="goodsForm.xgj_profile.flash_sale_type" type="number" min="0" /></label>
          <label class="form-group" style="grid-column:1/-1"><span>notify_url</span><input v-model="goodsForm.xgj_profile.notify_url" placeholder="商品变更回调地址（可选）" /></label>
          <label class="checkbox-inline"><input v-model="goodsForm.xgj_profile.is_tax_included" type="checkbox" /> 含税</label>
        </div>

        <div class="form-group" style="grid-column:1/-1">
          <label class="section-label">闲管家商品属性</label>
          <div class="nested-list">
            <div v-for="(prop, pi) in goodsForm.xgj_properties" :key="pi" class="nested-card nested-grid">
              <input v-model="prop.property_id" placeholder="属性ID" />
              <input v-model="prop.property_name" placeholder="属性名" />
              <input v-model="prop.value_id" placeholder="属性值ID" />
              <input v-model="prop.value_name" placeholder="属性值名" />
              <button class="btn btn-danger btn-sm nested-remove" @click="removeXgjProperty(pi)">删除属性</button>
            </div>
            <button class="btn btn-secondary btn-sm" @click="addXgjProperty">＋ 添加属性</button>
          </div>
        </div>

        <div class="form-group" style="grid-column:1/-1">
          <label class="section-label">闲管家发布店铺</label>
          <div class="nested-list">
            <div class="shop-picker card-lite">
              <div class="shop-picker-head">
                <span>从本地店铺中选择</span>
                <span class="shop-picker-hint">已选 {{ goodsForm.xgj_publish_shops.length }} 家</span>
              </div>
              <div v-if="availableXgjShops.length" class="shop-picker-grid">
                <label v-for="shop in availableXgjShops" :key="shop.id" class="shop-choice" :class="{ selected: isSelectedXgjShop(shop.id) }">
                  <input
                    type="checkbox"
                    :checked="isSelectedXgjShop(shop.id)"
                    @change="onPublishShopCheckboxChange(shop, $event)"
                  />
                  <div class="shop-choice-body">
                    <b>{{ shop.shop_name }}</b>
                    <span>{{ shop.user_name }}</span>
                    <small>{{ shop.service_support || '无服务项' }}</small>
                  </div>
                </label>
              </div>
              <div v-else class="empty-inline">暂无可用本地店铺，请先去店铺管理同步。</div>
            </div>
            <div v-for="(shop, si) in goodsForm.xgj_publish_shops" :key="si" class="nested-card">
              <div class="nested-card-head">
                <div class="shop-card-title">
                  <b>{{ shop.xgj_shop?.shop_name || shop.user_name || `店铺 ${si + 1}` }}</b>
                  <span class="shop-card-subtitle">{{ shop.xgj_shop?.user_name || shop.user_name }}</span>
                </div>
                <button class="btn btn-danger btn-sm" @click="removeXgjShop(si)">删除店铺</button>
              </div>
              <div class="nested-grid">
                <input v-model="shop.user_name" placeholder="闲鱼会员名 *" :disabled="!!shop.xgj_shop_id" />
                <input v-model.number="shop.province" type="number" min="0" placeholder="省份ID *" />
                <input v-model.number="shop.city" type="number" min="0" placeholder="城市ID *" />
                <input v-model.number="shop.district" type="number" min="0" placeholder="地区ID *" />
                <input v-model="shop.title" placeholder="商品标题 *" />
                <input v-model="shop.service_support" placeholder="服务项，如 SDR,VNR" />
                <input v-model="shop.white_image_url" placeholder="白底图URL（可选）" style="grid-column:1/-1" />
                <textarea v-model="shop.content" rows="3" placeholder="商品描述 *" style="grid-column:1/-1"></textarea>
              </div>
              <div class="shop-images">
                <div class="shop-images-head">
                  <div>
                    <div class="section-subtitle">店铺图片</div>
                    <div class="section-hint">第一张会作为主图上传到闲管家</div>
                  </div>
                  <label class="btn btn-secondary btn-sm upload-btn-inline" :class="{ disabled: uploadingTarget === `shop-${si}` }">
                    {{ uploadingTarget === `shop-${si}` ? '上传中…' : '上传图片' }}
                    <input type="file" accept="image/*" multiple hidden @change="onShopImagesSelected(si, $event)" />
                  </label>
                </div>
                <div v-for="(image, ii) in shop.images" :key="ii" class="image-row">
                  <div class="image-main">
                    <img v-if="image.image_url" :src="image.image_url" class="shop-image-preview" alt="店铺图片" />
                    <div v-else class="shop-image-empty">未上传</div>
                    <input v-model="image.image_url" placeholder="图片URL *" />
                  </div>
                  <div class="image-actions">
                    <button class="btn btn-secondary btn-sm" :disabled="ii === 0" @click="moveXgjShopImage(si, ii, -1)">上移</button>
                    <button class="btn btn-secondary btn-sm" :disabled="ii === shop.images.length - 1" @click="moveXgjShopImage(si, ii, 1)">下移</button>
                    <button class="btn btn-danger btn-sm" @click="removeXgjShopImage(si, ii)">删除</button>
                  </div>
                </div>
                <button class="btn btn-secondary btn-sm" @click="addXgjShopImage(si)">＋ 手动添加图片 URL</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 单规格模式：直接设置发货时机绑定 -->
        <template v-if="!goodsForm.multi_spec">
          <div class="form-group" style="grid-column:1/-1">
            <label class="section-label">发货时机 SKU 绑定（单规格）</label>
          </div>
          <div class="binding-grid-inline" style="grid-column:1/-1">
            <div v-for="t in timings" :key="t.value" class="binding-item">
              <span class="binding-label">{{ t.label }}</span>
              <select v-model="singleSpecBindings[t.value]" class="binding-select">
                <option :value="null">— 不绑定 —</option>
                <option v-for="sku in skuOptions" :key="sku.id" :value="sku.id">{{ sku.name }}</option>
              </select>
            </div>
          </div>
        </template>
      </div>
      <p v-if="goodsErr" class="error-text">{{ goodsErr }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showGoodsModal = false">取消</button>
        <button class="btn btn-primary" :disabled="goodsSaving" @click="handleSaveGoods">{{ goodsSaving ? '保存中…' : '保存' }}</button>
      </template>
    </Modal>

    <!-- ══════════ 多规格管理 Modal ══════════ -->
    <Modal v-model="showSpecModal" :title="`规格管理 — ${specGoods?.goods_name ?? ''}`">
      <!-- 规格维度定义 -->
      <div class="spec-groups-section">
        <div class="section-title">规格维度 <small>（最多2组）</small></div>
        <div v-for="(group, gi) in specGroups" :key="gi" class="spec-group-card">
          <div class="spec-group-header">
            <input v-model="group.name" placeholder="规格名称，如：颜色、尺码" class="spec-group-name-input" @input="regenerateVariants" />
            <button class="btn btn-danger btn-sm" @click="removeGroup(gi)">删除维度</button>
          </div>
          <div class="values-area">
            <div class="value-chips">
              <span v-for="(val, vi) in group.values" :key="vi" class="value-chip">
                {{ val }}
                <button class="chip-remove" @click="removeValue(gi, vi)">×</button>
              </span>
            </div>
            <div class="add-value-row">
              <input v-model="group._newValue" placeholder="输入属性值，按回车添加" @keydown.enter.prevent="addValue(gi)" class="add-value-input" />
              <button class="btn btn-secondary btn-sm" @click="addValue(gi)">添加</button>
            </div>
            <div class="value-count-hint">已添加 {{ group.values.length }} / 150 个属性值</div>
          </div>
        </div>
        <button v-if="specGroups.length < 2" class="btn btn-secondary" @click="addGroup" style="margin-top:8px">＋ 添加规格维度</button>

        <div v-if="specGroups.length > 0" class="combo-hint" :class="{ 'combo-warn': comboCount > 400 }">
          组合数：{{ comboCount }} / 400
          <template v-if="specGroups.length === 2">
            （{{ specGroups[0].values.length }} × {{ specGroups[1].values.length }}）
          </template>
        </div>
      </div>

      <!-- 变体组合表格 -->
      <div v-if="specVariants.length > 0" class="variants-section">
        <div class="section-title">规格组合明细 <small>（{{ specVariants.length }}项）</small></div>
        <div class="batch-set">
          <span class="batch-label">批量设置：</span>
          <label class="spec-field"><span>价格(分)</span><input v-model.number="batchPrice" type="number" min="0" /></label>
          <label class="spec-field"><span>库存</span><input v-model.number="batchStock" type="number" min="0" /></label>
          <button class="btn btn-secondary btn-sm" @click="applyBatch">应用到全部</button>
        </div>
        <div class="variants-table-wrapper">
          <table class="data-table variants-table">
            <thead>
              <tr>
                <th>组合名称</th>
                <th>价格(分)</th>
                <th>库存</th>
                <th v-for="t in timings" :key="t.value">{{ t.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(v, vi) in specVariants" :key="vi">
                <td><b>{{ v.spec_name }}</b></td>
                <td><input v-model.number="v.price_cents" type="number" min="0" class="variant-input" /></td>
                <td><input v-model.number="v.stock" type="number" min="0" class="variant-input" /></td>
                <td v-for="t in timings" :key="t.value">
                  <select v-model="v.bindings[t.value]" class="binding-select-sm">
                    <option :value="null">—</option>
                    <option v-for="sku in skuOptions" :key="sku.id" :value="sku.id">{{ sku.name }}</option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p v-if="specErr" class="error-text">{{ specErr }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showSpecModal = false">取消</button>
        <button class="btn btn-primary" :disabled="specSaving || comboCount > 400" @click="handleSaveSpecs">
          {{ specSaving ? '保存中…' : '保存全部' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  listGoods, createGoods, updateGoods, deleteGoods, getGoods, uploadGoodsLogo,
  createGoodsSpec, updateGoodsSpec, setSpecBindings, setSpecConfig,
  listXgjOrders, listSKUs, listXgjShops, uploadAdminImage,
  type Goods, type GoodsSpec, type SKU, type XgjOrder, type SpecGroup,
  type GoodsXgjProfile, type GoodsXgjProperty, type GoodsXgjPublishShop, type XgjShop,
} from '@/api/client'
import Modal from '@/components/Modal.vue'

const PAGE_SIZE = 20
const tab = ref<'goods' | 'orders'>('goods')

// ── 商品列表 ──
const items = ref<Goods[]>([])
const total = ref(0)
const offset = ref(0)
const filterType = ref<number | undefined>(undefined)
const filterStatus = ref<number | undefined>(undefined)
const page = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

async function load() {
  const r = await listGoods(PAGE_SIZE, offset.value, filterStatus.value, filterType.value)
  items.value = r.items; total.value = r.total
}

// ── SKU 选项（全局加载一次）──
const skuOptions = ref<SKU[]>([])
async function ensureSkuOptions() {
  if (skuOptions.value.length === 0) {
    const r = await listSKUs(undefined, 200)
    skuOptions.value = r.items
  }
}

const availableXgjShops = ref<XgjShop[]>([])
async function ensureXgjShops() {
  if (availableXgjShops.value.length === 0) {
    const r = await listXgjShops(200, 0)
    availableXgjShops.value = r.items
  }
}

// ── 商品 Modal ──
const showGoodsModal = ref(false)
const editingGoods = ref<Goods | null>(null)
const goodsSaving = ref(false)
const goodsErr = ref('')
const logoFile = ref<File | null>(null)
const logoPreview = ref<string | null>(null)
const uploadingTarget = ref<string | null>(null)

const timings = [
  { value: 'after_payment', label: '付款后发货' },
  { value: 'after_receipt', label: '收货后赠送' },
  { value: 'after_review',  label: '好评后赠送' },
]

const singleSpecBindings = ref<Record<string, string | null>>({
  after_payment: null, after_receipt: null, after_review: null,
})

function createDefaultXgjProfile(): GoodsXgjProfile {
  return {
    item_biz_type: 2,
    sp_biz_type: 22,
    category_id: null,
    channel_cat_id: '',
    original_price_cents: 0,
    express_fee_cents: 0,
    stuff_status: 0,
    notify_url: null,
    flash_sale_type: null,
    is_tax_included: false,
  }
}

function createEmptyXgjProperty(): GoodsXgjProperty {
  return {
    property_id: '',
    property_name: '',
    value_id: '',
    value_name: '',
    sort_order: 0,
  }
}

function createEmptyXgjShop(shop?: XgjShop): GoodsXgjPublishShop {
  return {
    xgj_shop_id: shop?.id ?? null,
    xgj_shop: shop
      ? {
        id: shop.id,
        user_name: shop.user_name,
        user_nick: shop.user_nick,
        shop_name: shop.shop_name,
        service_support: shop.service_support,
        is_valid: shop.is_valid,
      }
      : null,
    user_name: shop?.user_name ?? '',
    province: 0,
    city: 0,
    district: 0,
    title: '',
    content: '',
    white_image_url: null,
    service_support: shop?.service_support ?? null,
    sort_order: 0,
    images: [],
  }
}

const defaultGoodsForm = () => ({
  goods_type: 1, goods_name: '',
  logo_url: null as string | null,
  price_cents: 0, stock: 0, status: 1,
  multi_spec: false,
  xgj_goods_id: null as string | null,
  description: null as string | null,
  xgj_profile: createDefaultXgjProfile(),
  xgj_properties: [] as GoodsXgjProperty[],
  xgj_publish_shops: [] as GoodsXgjPublishShop[],
})
const goodsForm = ref(defaultGoodsForm())

function addXgjProperty() {
  goodsForm.value.xgj_properties.push(createEmptyXgjProperty())
}

function removeXgjProperty(index: number) {
  goodsForm.value.xgj_properties.splice(index, 1)
}

function isSelectedXgjShop(shopId: string) {
  return goodsForm.value.xgj_publish_shops.some(shop => shop.xgj_shop_id === shopId)
}

function togglePublishShopSelection(selectedShop: XgjShop, checked: boolean) {
  const current = goodsForm.value.xgj_publish_shops
  const existing = current.find(shop => shop.xgj_shop_id === selectedShop.id)
  if (checked) {
    if (existing) return
    current.push(createEmptyXgjShop(selectedShop))
    return
  }
  goodsForm.value.xgj_publish_shops = current.filter(shop => shop.xgj_shop_id !== selectedShop.id)
}

function onPublishShopCheckboxChange(selectedShop: XgjShop, event: Event) {
  const checked = (event.target as HTMLInputElement | null)?.checked ?? false
  togglePublishShopSelection(selectedShop, checked)
}

function removeXgjShop(index: number) {
  goodsForm.value.xgj_publish_shops.splice(index, 1)
}

function addXgjShopImage(shopIndex: number) {
  goodsForm.value.xgj_publish_shops[shopIndex].images.push({ image_url: '', sort_order: 0 })
}

function removeXgjShopImage(shopIndex: number, imageIndex: number) {
  const images = goodsForm.value.xgj_publish_shops[shopIndex].images
  images.splice(imageIndex, 1)
}

function moveXgjShopImage(shopIndex: number, imageIndex: number, offset: -1 | 1) {
  const images = goodsForm.value.xgj_publish_shops[shopIndex].images
  const targetIndex = imageIndex + offset
  if (targetIndex < 0 || targetIndex >= images.length) return
  const [image] = images.splice(imageIndex, 1)
  images.splice(targetIndex, 0, image)
}

async function onShopImagesSelected(shopIndex: number, event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (!files.length) return
  uploadingTarget.value = `shop-${shopIndex}`
  goodsErr.value = ''
  try {
    const urls = await Promise.all(files.map(file => uploadAdminImage(file)))
    goodsForm.value.xgj_publish_shops[shopIndex].images.push(
      ...urls.map((url, index) => ({ image_url: url, sort_order: goodsForm.value.xgj_publish_shops[shopIndex].images.length + index }))
    )
  } catch (error: unknown) {
    goodsErr.value = error instanceof Error ? error.message : '图片上传失败'
  } finally {
    input.value = ''
    uploadingTarget.value = null
  }
}

function reconcilePublishShops() {
  if (!availableXgjShops.value.length) return
  const catalog = new Map(availableXgjShops.value.map(shop => [shop.id, shop]))
  const byUserName = new Map(availableXgjShops.value.map(shop => [shop.user_name, shop]))
  goodsForm.value.xgj_publish_shops = goodsForm.value.xgj_publish_shops.map((shop, index) => {
    const matched = (shop.xgj_shop_id ? catalog.get(shop.xgj_shop_id) : undefined) || byUserName.get(shop.user_name)
    const next = matched ? createEmptyXgjShop(matched) : createEmptyXgjShop()
    return {
      ...next,
      ...shop,
      xgj_shop_id: matched?.id ?? shop.xgj_shop_id ?? null,
      xgj_shop: matched
        ? {
          id: matched.id,
          user_name: matched.user_name,
          user_nick: matched.user_nick,
          shop_name: matched.shop_name,
          service_support: matched.service_support,
          is_valid: matched.is_valid,
        }
        : shop.xgj_shop ?? null,
      user_name: matched?.user_name ?? shop.user_name,
      service_support: shop.service_support ?? matched?.service_support ?? null,
      sort_order: shop.sort_order ?? index,
      images: (shop.images ?? []).map((image, imageIndex) => ({ ...image, sort_order: image.sort_order ?? imageIndex })),
    }
  })
}

function onLogoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  logoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
}

async function openCreate() {
  editingGoods.value = null
  goodsForm.value = defaultGoodsForm()
  logoFile.value = null; logoPreview.value = null
  singleSpecBindings.value = { after_payment: null, after_receipt: null, after_review: null }
  goodsErr.value = ''
  await Promise.all([ensureSkuOptions(), ensureXgjShops()])
  showGoodsModal.value = true
}

async function openEdit(g: Goods) {
  editingGoods.value = g
  goodsForm.value = {
    goods_type: g.goods_type, goods_name: g.goods_name,
    logo_url: g.logo_url,
    price_cents: g.price_cents, stock: g.stock, status: g.status,
    multi_spec: g.multi_spec,
    xgj_goods_id: g.xgj_goods_id,
    description: g.description,
    xgj_profile: g.xgj_profile ?? createDefaultXgjProfile(),
    xgj_properties: (g.xgj_properties ?? []).map((item, index) => ({ ...item, sort_order: item.sort_order ?? index })),
    xgj_publish_shops: (g.xgj_publish_shops?.length
      ? g.xgj_publish_shops
      : [createEmptyXgjShop()]).map((shop, shopIndex) => ({
        ...shop,
        sort_order: shop.sort_order ?? shopIndex,
        white_image_url: shop.white_image_url ?? null,
        service_support: shop.service_support ?? null,
        images: (shop.images ?? []).map((image, imageIndex) => ({
          ...image,
          sort_order: image.sort_order ?? imageIndex,
        })),
      })),
  }
  logoFile.value = null; logoPreview.value = null
  // 单规格：加载默认规格的绑定
  if (!g.multi_spec && g.specs?.length) {
    const spec = g.specs[0]
    singleSpecBindings.value = Object.fromEntries(
      timings.map(t => {
        const b = spec.sku_bindings?.find(x => x.timing === t.value)
        return [t.value, b?.sku_id ?? null]
      })
    )
  } else {
    singleSpecBindings.value = { after_payment: null, after_receipt: null, after_review: null }
  }
  goodsErr.value = ''
  await Promise.all([ensureSkuOptions(), ensureXgjShops()])
  reconcilePublishShops()
  showGoodsModal.value = true
}

async function handleSaveGoods() {
  const f = goodsForm.value
  if (!f.goods_name.trim()) { goodsErr.value = '商品名称不能为空'; return }
  if (!f.xgj_profile.channel_cat_id.trim()) { goodsErr.value = '请填写 channel_cat_id'; return }
  if (!f.xgj_publish_shops.length) { goodsErr.value = '请至少配置一个闲管家发布店铺'; return }
  if (f.xgj_publish_shops.some(shop => !shop.xgj_shop_id)) { goodsErr.value = '请选择本地店铺后再保存'; return }
  if (f.xgj_publish_shops.some(shop => !shop.user_name.trim() || !shop.title.trim() || !shop.content.trim())) {
    goodsErr.value = '请完整填写发布店铺的会员名、标题和描述'
    return
  }
  if (f.xgj_publish_shops.some(shop => !shop.images.length)) {
    goodsErr.value = '每个发布店铺至少需要上传一张图片'
    return
  }
  if (f.xgj_publish_shops.some(shop => shop.images.some(image => !image.image_url.trim()))) {
    goodsErr.value = '请完整填写发布店铺图片 URL'
    return
  }
  goodsSaving.value = true; goodsErr.value = ''
  try {
    let savedGoods: Goods
    if (editingGoods.value) {
      savedGoods = await updateGoods(editingGoods.value.id, {
        goods_name: f.goods_name, goods_type: f.goods_type,
        logo_url: f.logo_url,
        price_cents: f.price_cents, stock: f.stock, status: f.status,
        multi_spec: f.multi_spec,
        xgj_goods_id: f.xgj_goods_id || undefined,
        description: f.description,
        xgj_profile: {
          ...f.xgj_profile,
          notify_url: f.xgj_profile.notify_url || null,
          flash_sale_type: f.xgj_profile.flash_sale_type || null,
        },
        xgj_properties: f.xgj_properties.map((item, index) => ({ ...item, sort_order: index })),
        xgj_publish_shops: f.xgj_publish_shops.map((shop, shopIndex) => {
          const { xgj_shop, ...rest } = shop
          return {
          ...rest,
          white_image_url: shop.white_image_url || null,
          service_support: shop.service_support || null,
          sort_order: shopIndex,
          images: shop.images.map((image, imageIndex) => ({ ...image, sort_order: imageIndex })),
        }}),
      })
    } else {
      savedGoods = await createGoods({
        goods_type: f.goods_type, goods_name: f.goods_name,
        logo_url: f.logo_url,
        price_cents: f.price_cents, stock: f.stock, status: f.status,
        multi_spec: f.multi_spec,
        description: f.description,
        xgj_profile: {
          ...f.xgj_profile,
          notify_url: f.xgj_profile.notify_url || null,
          flash_sale_type: f.xgj_profile.flash_sale_type || null,
        },
        xgj_properties: f.xgj_properties.map((item, index) => ({ ...item, sort_order: index })),
        xgj_publish_shops: f.xgj_publish_shops.map((shop, shopIndex) => {
          const { xgj_shop, ...rest } = shop
          return {
          ...rest,
          white_image_url: shop.white_image_url || null,
          service_support: shop.service_support || null,
          sort_order: shopIndex,
          images: shop.images.map((image, imageIndex) => ({ ...image, sort_order: imageIndex })),
        }}),
      })
    }

    // 上传 Logo 图片
    if (logoFile.value) {
      savedGoods = await uploadGoodsLogo(savedGoods.id, logoFile.value)
    }

    // 单规格模式：自动创建/更新默认规格 + 绑定
    if (!f.multi_spec) {
      const fresh = await getGoods(savedGoods.id)
      const hasBindings = timings.some(t => singleSpecBindings.value[t.value])
      if (hasBindings || fresh.specs?.length) {
        let specId: string
        if (fresh.specs?.length) {
          specId = fresh.specs[0].id
          await updateGoodsSpec(savedGoods.id, specId, {
            spec_name: '默认', price_cents: f.price_cents, stock: f.stock, enabled: true,
          })
        } else {
          const created = await createGoodsSpec(savedGoods.id, {
            spec_name: '默认', price_cents: f.price_cents, stock: f.stock, enabled: true,
            sku_bindings: [],
          })
          specId = created.id
        }
        await setSpecBindings(savedGoods.id, specId,
          timings.map(t => ({ timing: t.value, sku_id: singleSpecBindings.value[t.value] || null }))
        )
      }
    }

    showGoodsModal.value = false; await load()
  } catch (e: unknown) { goodsErr.value = e instanceof Error ? e.message : '操作失败' }
  finally { goodsSaving.value = false }
}

async function handleDelete(g: Goods) {
  if (!confirm(`确认删除商品「${g.goods_name}」？此操作不可恢复。`)) return
  await deleteGoods(g.id); await load()
}

// ── 多规格管理 Modal ──
const showSpecModal = ref(false)
const specGoods = ref<Goods | null>(null)
const specSaving = ref(false)
const specErr = ref('')
const batchPrice = ref(0)
const batchStock = ref(0)

interface SpecGroupEditing {
  name: string
  values: string[]
  _newValue: string
}

interface SpecVariantEditing {
  spec_name: string
  price_cents: number
  stock: number
  enabled: boolean
  bindings: Record<string, string | null>
}

const specGroups = ref<SpecGroupEditing[]>([])
const specVariants = ref<SpecVariantEditing[]>([])

const comboCount = computed(() => {
  const groups = specGroups.value.filter(g => g.values.length > 0)
  if (groups.length === 0) return 0
  if (groups.length === 1) return groups[0].values.length
  return groups[0].values.length * groups[1].values.length
})

function addGroup() {
  if (specGroups.value.length >= 2) return
  specGroups.value.push({ name: '', values: [], _newValue: '' })
}

function removeGroup(gi: number) {
  specGroups.value.splice(gi, 1)
  regenerateVariants()
}

function addValue(gi: number) {
  const group = specGroups.value[gi]
  const val = group._newValue.trim()
  if (!val) return
  if (group.values.length >= 150) { specErr.value = '单个规格最多150个属性值'; return }
  if (group.values.includes(val)) { specErr.value = '属性值已存在'; return }
  // 校验组合数
  const otherLen = specGroups.value.length === 2 ? specGroups.value[1 - gi].values.length : 0
  const thisNewLen = group.values.length + 1
  if (specGroups.value.length === 2 && otherLen > 0 && thisNewLen * otherLen > 400) {
    specErr.value = `组合数将超过400（${thisNewLen} × ${otherLen} = ${thisNewLen * otherLen}）`
    return
  }
  specErr.value = ''
  group.values.push(val)
  group._newValue = ''
  regenerateVariants()
}

function removeValue(gi: number, vi: number) {
  specGroups.value[gi].values.splice(vi, 1)
  specErr.value = ''
  regenerateVariants()
}

function regenerateVariants() {
  const groups = specGroups.value.filter(g => g.name.trim() && g.values.length > 0)
  if (groups.length === 0) { specVariants.value = []; return }

  // 保存旧变体数据用于恢复
  const oldMap = new Map(specVariants.value.map(v => [v.spec_name, v]))

  const combos: string[] = []
  if (groups.length === 1) {
    for (const v of groups[0].values) combos.push(v)
  } else {
    for (const v1 of groups[0].values) {
      for (const v2 of groups[1].values) combos.push(`${v1}/${v2}`)
    }
  }

  specVariants.value = combos.map(name => {
    const old = oldMap.get(name)
    return old ? { ...old } : {
      spec_name: name,
      price_cents: 0,
      stock: 0,
      enabled: true,
      bindings: { after_payment: null, after_receipt: null, after_review: null },
    }
  })
}

function applyBatch() {
  for (const v of specVariants.value) {
    if (batchPrice.value > 0) v.price_cents = batchPrice.value
    if (batchStock.value > 0) v.stock = batchStock.value
  }
}

async function openSpecs(g: Goods) {
  specGoods.value = g; specErr.value = ''
  batchPrice.value = 0; batchStock.value = 0
  const [fresh, skuResult] = await Promise.all([getGoods(g.id), listSKUs(undefined, 200)])
  skuOptions.value = skuResult.items

  // 恢复已有的 spec_groups
  const existingGroups: SpecGroup[] = fresh.spec_groups ?? []
  specGroups.value = existingGroups.map(sg => ({
    name: sg.name,
    values: [...sg.values],
    _newValue: '',
  }))

  // 恢复已有的 variant 数据
  specVariants.value = (fresh.specs || []).map(s => ({
    spec_name: s.spec_name,
    price_cents: s.price_cents,
    stock: s.stock,
    enabled: s.enabled,
    bindings: Object.fromEntries(
      timings.map(t => {
        const b = s.sku_bindings?.find(x => x.timing === t.value)
        return [t.value, b?.sku_id ?? null]
      })
    ),
  }))

  showSpecModal.value = true
}

async function handleSaveSpecs() {
  if (!specGoods.value) return
  const gid = specGoods.value.id
  const groups = specGroups.value.filter(g => g.name.trim() && g.values.length > 0)
  if (groups.length === 0) { specErr.value = '请至少添加一个规格维度和属性值'; return }
  if (specVariants.value.length === 0) { specErr.value = '没有可保存的组合'; return }

  specSaving.value = true; specErr.value = ''
  try {
    await setSpecConfig(gid, {
      spec_groups: groups.map(g => ({ name: g.name, values: g.values })),
      variants: specVariants.value.map(v => ({
        spec_name: v.spec_name,
        price_cents: v.price_cents,
        stock: v.stock,
        enabled: v.enabled,
        sku_bindings: timings
          .filter(t => v.bindings[t.value])
          .map(t => ({ timing: t.value, sku_id: v.bindings[t.value] })),
      })),
    })
    showSpecModal.value = false; await load()
  } catch (e: unknown) { specErr.value = e instanceof Error ? e.message : '操作失败' }
  finally { specSaving.value = false }
}

// ── 闲管家订单 ──
const orderItems = ref<XgjOrder[]>([])
const ordersTotal = ref(0)
const ordersOffset = ref(0)
const ordersPage = computed(() => Math.floor(ordersOffset.value / PAGE_SIZE) + 1)
const ordersTotalPages = computed(() => Math.max(1, Math.ceil(ordersTotal.value / PAGE_SIZE)))

async function loadOrders() {
  const r = await listXgjOrders(PAGE_SIZE, ordersOffset.value)
  orderItems.value = r.items; ordersTotal.value = r.total
}

// ── 工具函数 ──
function typeLabel(t: number) { return { 1: '直充', 2: '卡密', 3: '券码' }[t] ?? '未知' }
function typeBadge(t: number) { return { 1: 'badge-info', 2: 'badge-warning', 3: 'badge-success' }[t] ?? '' }
function orderStatusLabel(s: number) { return { 0: '待处理', 1: '处理中', 2: '成功', 3: '失败', 4: '退款中', 5: '已退款' }[s] ?? '未知' }
function orderStatusBadge(s: number) { return { 0: 'badge-expired', 1: 'badge-info', 2: 'badge-active', 3: 'badge-revoked', 4: 'badge-expired', 5: 'badge-revoked' }[s] ?? '' }
function fmt(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.tab-bar { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 2px solid var(--border); }
.tab-btn {
  padding: 10px 24px; font-size: .9rem; font-weight: 600;
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all .15s;
  font-family: 'Open Sans', sans-serif;
}
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }
.tab-btn:hover:not(.active) { color: var(--text); }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.toolbar-left { display: flex; align-items: center; gap: 12px; }
.total-hint { font-size: .85rem; color: var(--text-muted); font-weight: 500; }
.filter-select {
  padding: 5px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: .82rem; background: #fff; color: var(--text);
  font-family: 'Open Sans', sans-serif;
}
.tiny { font-size: .75rem; font-family: monospace; background: var(--bg); padding: 2px 6px; border-radius: 4px; color: var(--text-muted); }
.text-muted { font-size: .8rem; color: var(--text-muted); }
.action-cell { display: flex; gap: 6px; }

/* Logo */
.goods-logo { width: 36px; height: 36px; object-fit: cover; border-radius: 6px; border: 1px solid var(--border); }
.no-logo { font-size: .75rem; color: var(--text-muted); }

/* Logo upload */
.logo-upload-area {
  position: relative; width: 100px; height: 100px;
  border: 2px dashed var(--border); border-radius: 8px;
  overflow: hidden; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.logo-upload-area:hover { border-color: var(--primary); }
.logo-preview { width: 100%; height: 100%; object-fit: cover; }
.logo-placeholder { font-size: .75rem; color: var(--text-muted); text-align: center; padding: 8px; }
.logo-file-input {
  position: absolute; inset: 0; opacity: 0; cursor: pointer;
}
.input-disabled { background: var(--bg); color: var(--text-muted); cursor: not-allowed; }

/* badges */
.badge-info { background: #DBEAFE; color: #1E40AF; }
.badge-warning { background: #FEF3C7; color: #92400E; }
.badge-success { background: #D1FAE5; color: #065F46; }

/* section label */
.section-label { font-weight: 600; color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: 4px; }

/* binding grid inline (for single-spec in goods modal) */
.binding-grid-inline { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }

/* 规格 Modal */
.spec-groups-section { margin-bottom: 20px; }
.section-title { font-weight: 600; font-size: .95rem; margin-bottom: 10px; color: var(--text); }
.section-title small { font-weight: 400; color: var(--text-muted); font-size: .8rem; }

.spec-group-card {
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 14px; background: var(--bg); margin-bottom: 12px;
}
.spec-group-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.spec-group-name-input {
  flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: .875rem; font-family: 'Open Sans', sans-serif;
}

.values-area { display: flex; flex-direction: column; gap: 8px; }
.value-chips { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; }
.value-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; background: #DBEAFE; color: #1E40AF;
  border-radius: 20px; font-size: .8rem; font-weight: 500;
}
.chip-remove {
  background: none; border: none; cursor: pointer;
  color: #1E40AF; font-size: .9rem; padding: 0 2px; line-height: 1;
  opacity: .6; transition: opacity .15s;
}
.chip-remove:hover { opacity: 1; }

.add-value-row { display: flex; gap: 8px; align-items: center; }
.add-value-input {
  flex: 1; padding: 5px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: .82rem; font-family: 'Open Sans', sans-serif;
}
.value-count-hint { font-size: .75rem; color: var(--text-muted); }

.combo-hint {
  margin-top: 10px; font-size: .82rem; color: var(--text-muted);
  padding: 6px 12px; background: #F0FDF4; border-radius: 6px; border: 1px solid #BBF7D0;
}
.combo-warn { background: #FEF2F2; border-color: #FECACA; color: #DC2626; font-weight: 600; }

/* 变体表格 */
.variants-section { margin-top: 16px; }
.variants-table-wrapper { max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: var(--radius); }
.variants-table th, .variants-table td { padding: 6px 8px; font-size: .82rem; white-space: nowrap; }
.variant-input {
  width: 80px; padding: 4px 6px; border: 1px solid var(--border); border-radius: 4px;
  font-size: .82rem; text-align: right;
}
.binding-select-sm {
  width: 120px; padding: 3px 6px; border: 1px solid var(--border); border-radius: 4px;
  font-size: .78rem; background: #fff; font-family: 'Open Sans', sans-serif;
}

.batch-set {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
  padding: 8px 12px; background: var(--bg); border-radius: 6px; border: 1px solid var(--border);
}
.batch-label { font-size: .8rem; color: var(--text-muted); font-weight: 600; }
.spec-field { display: flex; align-items: center; gap: 4px; font-size: .8rem; color: var(--text-muted); }
.spec-field input { width: 80px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: .82rem; }

.xgj-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.checkbox-inline { display: flex; align-items: center; gap: 8px; font-size: .86rem; color: var(--text); }
.nested-list { display: flex; flex-direction: column; gap: 12px; }
.card-lite { border: 1px solid var(--border); border-radius: 10px; padding: 12px; background: var(--bg); }
.shop-picker-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 10px; }
.shop-picker-hint, .section-hint { font-size: .75rem; color: var(--text-muted); }
.shop-picker-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.shop-choice {
  display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px;
  border: 1px solid var(--border); border-radius: 8px; background: #fff; cursor: pointer;
}
.shop-choice.selected { border-color: var(--primary); background: rgba(59, 130, 246, 0.06); }
.shop-choice-body { display: flex; flex-direction: column; gap: 3px; }
.shop-choice-body span { font-size: .82rem; color: var(--text); }
.shop-choice-body small { color: var(--text-muted); }
.nested-card { border: 1px solid var(--border); border-radius: 10px; padding: 12px; background: var(--bg); }
.nested-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.shop-card-title { display: flex; flex-direction: column; gap: 4px; }
.shop-card-subtitle { font-size: .78rem; color: var(--text-muted); }
.nested-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.nested-remove { grid-column: 1 / -1; justify-self: end; }
.shop-images { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.shop-images-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.section-subtitle { font-size: .8rem; color: var(--text-muted); font-weight: 600; }
.image-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
.image-main { display: grid; grid-template-columns: 56px 1fr; gap: 10px; align-items: center; }
.shop-image-preview, .shop-image-empty {
  width: 56px; height: 56px; border-radius: 8px; border: 1px solid var(--border);
  object-fit: cover; background: #fff;
}
.shop-image-empty {
  display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: .72rem;
}
.image-actions { display: flex; gap: 6px; }
.upload-btn-inline { position: relative; overflow: hidden; }
.upload-btn-inline.disabled { pointer-events: none; opacity: .6; }
.empty-inline { font-size: .82rem; color: var(--text-muted); padding: 8px 0; }

@media (max-width: 900px) {
  .xgj-grid, .nested-grid, .shop-picker-grid { grid-template-columns: 1fr; }
  .image-row, .image-main { grid-template-columns: 1fr; }
  .image-actions, .shop-images-head, .shop-picker-head { flex-wrap: wrap; }
}
.binding-item { display: flex; flex-direction: column; gap: 4px; }
.binding-label { font-size: .75rem; color: var(--text-muted); font-weight: 600; }
.binding-select {
  padding: 5px 8px; border: 1px solid var(--border); border-radius: 6px;
  font-size: .8rem; background: #fff; font-family: 'Open Sans', sans-serif;
}
</style>
