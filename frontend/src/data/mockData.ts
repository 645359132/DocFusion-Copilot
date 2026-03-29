export type TaskStatus = 'queued' | 'processing' | 'completed' | 'warning';

export type TaskItem = {
  id: string;
  name: string;
  type: '文档解析' | '模板回填';
  status: TaskStatus;
  progress: number;
  updatedAt: string;
  detail: string;
};

export type ResultRow = {
  city: string;
  gdp: string;
  population: string;
  perCapitaGdp: string;
  revenue: string;
  traceId: string;
};

export type TraceRecord = {
  id: string;
  cell: string;
  field: string;
  sourceDoc: string;
  sourcePath: string;
  evidence: string;
  confidence: string;
  notes: string;
};

export const summaryCards = [
  { label: '已上传文档', value: '12 份', tone: 'text-ember' },
  { label: '解析完成', value: '9 份', tone: 'text-teal' },
  { label: '待回填模板', value: '2 份', tone: 'text-ink' },
];

export const taskItems: TaskItem[] = [
  {
    id: 'task-parse-001',
    name: '2025 城市经济报告.docx',
    type: '文档解析',
    status: 'completed',
    progress: 100,
    updatedAt: '今天 10:24',
    detail: '结构切块、字段抽取和事实入库已完成。',
  },
  {
    id: 'task-parse-002',
    name: '城市财政补充说明.md',
    type: '文档解析',
    status: 'processing',
    progress: 68,
    updatedAt: '今天 10:31',
    detail: '正在进行单位归一化与冲突值合并。',
  },
  {
    id: 'task-fill-001',
    name: '城市指标汇总模板.xlsx',
    type: '模板回填',
    status: 'warning',
    progress: 88,
    updatedAt: '今天 10:35',
    detail: '已完成主要字段填充，1 个低置信度字段待确认。',
  },
];

export const resultRows: ResultRow[] = [
  {
    city: '上海',
    gdp: '56708.71',
    population: '2487.45',
    perCapitaGdp: '228020',
    revenue: '8500.91',
    traceId: 'trace-b2',
  },
  {
    city: '北京',
    gdp: '52073.40',
    population: '2185.30',
    perCapitaGdp: '238320',
    revenue: '6680.60',
    traceId: 'trace-b3',
  },
  {
    city: '深圳',
    gdp: '38731.80',
    population: '1779.05',
    perCapitaGdp: '217710',
    revenue: '4163.80',
    traceId: 'trace-b4',
  },
];

export const traceRecords: Record<string, TraceRecord> = {
  'trace-b2': {
    id: 'trace-b2',
    cell: 'B2',
    field: 'GDP总量（亿元）',
    sourceDoc: '2025 城市经济报告.docx',
    sourcePath: '一、双核领航 / 新高度',
    evidence: '上海以56,708.71亿元的GDP总量稳居全年第一。',
    confidence: '0.95',
    notes: '数值来自正文主段落，与统计表记录一致。',
  },
  'trace-b3': {
    id: 'trace-b3',
    cell: 'B3',
    field: 'GDP总量（亿元）',
    sourceDoc: '城市经济概览.xlsx',
    sourcePath: 'Sheet1 / 城市指标总表',
    evidence: '北京 GDP 总量为 52073.40 亿元。',
    confidence: '0.93',
    notes: '来源于表格主数据区域，单位已校验。',
  },
  'trace-b4': {
    id: 'trace-b4',
    cell: 'B4',
    field: 'GDP总量（亿元）',
    sourceDoc: '深圳年度公报.md',
    sourcePath: '## 综合实力',
    evidence: '深圳全年地区生产总值 38731.80 亿元。',
    confidence: '0.91',
    notes: '字段别名经“地区生产总值 -> GDP总量”标准化。',
  },
};